# admin/capacity/store.py — 운동 정원 Write-Through 인메모리 캐시
#
# 구조:
#   _cache = {"수": <int|None>, "금": <int|None>}
#   - None: 임원진이 아직 정원을 확정하지 않은 상태
#   - int:  확정된 정원
#
# 동작:
#   init_cache()          — 서버 부팅 시 1회, DB → 메모리 적재
#   get_capacities()      — 메모리에서 즉시 반환 (I/O 0)
#   update_capacities()   — 메모리 업데이트 + DB 쓰기 (I/O 1)
import os
import sqlite3
import threading

# ── DB 경로 (smash_db/users.db 와 같은 디렉터리) ───────────────────────────────
_DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', '..', 'smash_db', 'users.db',
)

# ── 인메모리 캐시 ────────────────────────────────────────────────────────────────
_cache: dict[str, int | None] = {"수": None, "금": None}
_lock = threading.Lock()


def _ensure_table(conn: sqlite3.Connection) -> None:
    """capacities 테이블이 없으면 생성한다."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS capacities (
            day   TEXT PRIMARY KEY,
            value INTEGER NOT NULL
        )
    """)
    conn.commit()


def init_cache() -> None:
    """서버 부팅 시 1회 호출. DB에서 마지막 확정 정원을 읽어 메모리에 적재한다."""
    conn = sqlite3.connect(_DB_PATH)
    try:
        _ensure_table(conn)
        rows = conn.execute("SELECT day, value FROM capacities").fetchall()
        with _lock:
            for day, value in rows:
                if day in _cache:
                    _cache[day] = value
    finally:
        conn.close()


def get_capacities() -> dict[str, int | None]:
    """인메모리 캐시에서 정원을 즉시 반환한다. (I/O 0)"""
    with _lock:
        return dict(_cache)


def update_capacities(data: dict) -> None:
    """메모리를 먼저 업데이트한 뒤, DB에도 영구 저장한다. (I/O 1)

    Args:
        data: {"수"?: int, "금"?: int} — 변경할 요일의 정원만 포함.
    """
    # 유효한 키만 필터링
    updates = {k: v for k, v in data.items() if k in ("수", "금") and isinstance(v, int)}
    if not updates:
        return

    # 1) 메모리 업데이트 (즉시 반영)
    with _lock:
        for day, value in updates.items():
            _cache[day] = value

    # 2) DB 영구 저장
    conn = sqlite3.connect(_DB_PATH)
    try:
        _ensure_table(conn)
        for day, value in updates.items():
            conn.execute(
                "INSERT INTO capacities (day, value) VALUES (?, ?) "
                "ON CONFLICT(day) DO UPDATE SET value = excluded.value",
                (day, value),
            )
        conn.commit()
    finally:
        conn.close()
