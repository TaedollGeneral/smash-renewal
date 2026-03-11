# board_store.py — SQLite-backed 게시판 저장소 (Gunicorn 멀티 프로세스 안전)
#
# [Level 3 아키텍처]
# 기존 인메모리 딕셔너리 + threading.Lock 방식을 완전히 제거하고,
# SQLite WAL 모드 기반의 프로세스 간 안전한 저장소로 전환한다.
#
# - 읽기(GET): 각 요청마다 SQLite SELECT (WAL 모드로 쓰기와 비블로킹)
# - 쓰기(Admin Apply): 직접 SQLite INSERT (저빈도, WAL로 worker와 공존)
# - 삭제(Cancel): 직접 SQLite DELETE
# - 대량 쓰기(일반 Apply): Redis 큐 → worker.py가 처리 (이 모듈 밖)
#
# threading.Lock이 없으므로 Gunicorn Workers 간 데이터 정합성이 보장된다.

import json
import os
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .scheduler_logic import Category

# ── 설정 ──────────────────────────────────────────────────────────────────────

_BASE_DIR = Path(__file__).resolve().parent.parent
_DB_PATH = str(_BASE_DIR / "smash_db" / "users.db")
_BACKUP_PATH = _BASE_DIR / "board_backup.json"

_KST = timezone(timedelta(hours=9))

_GUEST_CATEGORIES = {Category.WED_GUEST.value, Category.FRI_GUEST.value}
_VALID_CATEGORIES = {cat.value for cat in Category}

# 한 사람이 같은 주에 1번만 신청 가능한 카테고리 (중복 신청 검사 대상).
# 게스트/잔여석은 여러 건 신청 가능하므로 제외한다.
# role(manager 포함)에 관계없이 이 규칙이 적용된다.
UNIQUE_APPLY_CATEGORIES: frozenset[str] = frozenset({
    "WED_REGULAR",
    "FRI_REGULAR",
    "WED_LESSON",
})


# ── SQLite 연결 ───────────────────────────────────────────────────────────────

def _get_conn() -> sqlite3.Connection:
    """WAL 모드의 SQLite 연결을 반환한다.

    요청마다 새 연결을 생성한다. SQLite 연결 생성은 ~0.1ms로 경량이며,
    커넥션 풀링보다 Gunicorn fork 환경에서 안전하다.
    """
    conn = sqlite3.connect(_DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


# ── 테이블 초기화 ─────────────────────────────────────────────────────────────

def ensure_table() -> None:
    """applications 테이블이 없으면 생성한다. 서버 시작 시 1회 호출."""
    conn = _get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    TEXT    NOT NULL,
                name       TEXT    NOT NULL,
                category   TEXT    NOT NULL,
                type       TEXT    NOT NULL,
                guest_name TEXT,
                timestamp  REAL    NOT NULL,
                created_at TEXT    DEFAULT (datetime('now', '+9 hours')),
                UNIQUE(category, user_id)
            )
        """)
        conn.commit()
    finally:
        conn.close()


# ── 내부 유틸 ─────────────────────────────────────────────────────────────────

def _row_to_dict(row: sqlite3.Row) -> dict:
    """sqlite3.Row를 기존 board_store 호환 dict로 변환한다."""
    entry = {
        "user_id":   row["user_id"],
        "name":      row["name"],
        "type":      row["type"],
        "timestamp": row["timestamp"],
    }
    if row["guest_name"]:
        entry["guest_name"] = row["guest_name"]
    return entry


# ── 공개 API (읽기) ───────────────────────────────────────────────────────────

def get_board(category: str) -> list[dict]:
    """특정 카테고리의 신청 목록을 반환한다.

    게스트 카테고리는 OB/교류전 우선 정렬 후 타임스탬프순,
    나머지 카테고리는 순수 타임스탬프순으로 정렬한다.
    """
    conn = _get_conn()
    try:
        if category in _GUEST_CATEGORIES:
            rows = conn.execute(
                """SELECT user_id, name, type, guest_name, timestamp
                   FROM applications WHERE category = ?
                   ORDER BY
                     CASE WHEN lower(guest_name) LIKE '%(ob)%'
                               OR lower(guest_name) LIKE '%(교류전)%'
                          THEN 0 ELSE 1 END,
                     timestamp""",
                (category,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT user_id, name, type, guest_name, timestamp
                   FROM applications WHERE category = ?
                   ORDER BY timestamp""",
                (category,),
            ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_all_boards() -> dict[str, list[dict]]:
    """전체 카테고리 데이터의 스냅샷을 반환한다.

    단일 연결 + 단일 쿼리로 전체 데이터를 가져온 뒤
    카테고리별로 분류하여 반환한다.
    """
    conn = _get_conn()
    try:
        rows = conn.execute(
            """SELECT user_id, name, category, type, guest_name, timestamp
               FROM applications ORDER BY timestamp"""
        ).fetchall()

        result: dict[str, list[dict]] = {cat.value: [] for cat in Category}
        for row in rows:
            cat = row["category"]
            if cat in result:
                result[cat].append(_row_to_dict(row))

        # 게스트 카테고리만 OB/교류전 우선 정렬 적용
        for cat in _GUEST_CATEGORIES:
            if result[cat]:
                result[cat].sort(
                    key=lambda x: (
                        not (
                            "(ob)" in x.get("guest_name", "").lower()
                            or "(교류전)" in x.get("guest_name", "").lower()
                        ),
                        x["timestamp"],
                    )
                )

        return result
    finally:
        conn.close()


# ── 공개 API (쓰기) ───────────────────────────────────────────────────────────

def apply_entry(category: str, entry: dict) -> tuple[bool, str | None]:
    """신청 항목을 SQLite에 INSERT한다 (중복 시 UNIQUE 제약으로 거부).

    admin apply 경로에서 사용. 일반 apply는 Redis 큐를 거친다.

    Returns:
        (True, None)    — 추가 성공
        (False, reason) — 실패 (중복 또는 유효하지 않은 카테고리)
    """
    if category not in _VALID_CATEGORIES:
        return False, "유효하지 않은 카테고리입니다."

    conn = _get_conn()
    try:
        conn.execute(
            """INSERT INTO applications
                   (user_id, name, category, type, guest_name, timestamp)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                entry["user_id"],
                entry["name"],
                category,
                entry["type"],
                entry.get("guest_name"),
                entry["timestamp"],
            ),
        )
        conn.commit()
        return True, None
    except sqlite3.IntegrityError:
        return False, "이미 신청되어 있습니다."
    finally:
        conn.close()


def remove_entry(category: str, user_id: str) -> bool:
    """카테고리에서 user_id에 해당하는 항목을 삭제한다.

    Returns:
        True — 삭제 성공, False — 항목 없음
    """
    conn = _get_conn()
    try:
        cursor = conn.execute(
            "DELETE FROM applications WHERE category = ? AND user_id = ?",
            (category, user_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def is_already_applied(category: str, user_id: str) -> bool:
    """이번 주에 해당 카테고리에 이미 신청했는지 확인한다.

    이번 주 시작(토요일 00:00 KST) 이후 데이터만 검사하여,
    리셋 미실행 또는 Redis 큐 재삽입으로 남아있는 이전 주 데이터를 오탐지하지 않는다.

    UNIQUE_APPLY_CATEGORIES에 포함된 카테고리에만 호출한다.
    SQLite 장애 시 False를 반환하여 신청을 시도한다.
    → UNIQUE 제약이 최종 안전망으로 중복을 차단하므로 데이터 정합성에 영향 없음.
    """
    try:
        now = datetime.now(_KST)
        days_since_saturday = (now.weekday() - 5) % 7
        week_start_ts = (now - timedelta(days=days_since_saturday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        ).timestamp()

        conn = _get_conn()
        try:
            row = conn.execute(
                "SELECT 1 FROM applications"
                " WHERE category = ? AND user_id = ? AND timestamp >= ?"
                " LIMIT 1",
                (category, user_id, week_start_ts),
            ).fetchone()
            return row is not None
        finally:
            conn.close()
    except Exception:
        return False


def reset_all() -> None:
    """모든 카테고리의 데이터를 초기화한다.

    매주 토요일 00:00 스케줄러에서 호출된다.
    """
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM applications")
        conn.commit()
    finally:
        conn.close()

    # 레거시 백업 파일 삭제
    try:
        _BACKUP_PATH.unlink(missing_ok=True)
    except OSError:
        pass


# ── 레거시 호환 ───────────────────────────────────────────────────────────────

def load_from_backup() -> bool:
    """레거시 JSON 백업 → SQLite 일회성 마이그레이션.

    board_backup.json이 존재하고 applications 테이블이 비어있으면
    JSON 데이터를 SQLite로 이관한다. 이미 데이터가 있으면 스킵.

    Returns:
        True — 마이그레이션 성공 또는 이미 데이터 존재, False — 백업 파일 없음
    """
    if not _BACKUP_PATH.exists():
        return False

    try:
        with open(_BACKUP_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False

    conn = _get_conn()
    try:
        count = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        if count > 0:
            return True

        for category, entries in data.items():
            for entry in entries:
                try:
                    conn.execute(
                        """INSERT OR IGNORE INTO applications
                               (user_id, name, category, type, guest_name, timestamp)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (
                            entry["user_id"],
                            entry["name"],
                            category,
                            entry.get("type", "member"),
                            entry.get("guest_name"),
                            entry["timestamp"],
                        ),
                    )
                except (KeyError, sqlite3.Error):
                    continue
        conn.commit()
        return True
    finally:
        conn.close()


def start_background_saver() -> None:
    """No-op. SQLite 기반으로 전환되어 백그라운드 세이버가 불필요하다."""
    pass
