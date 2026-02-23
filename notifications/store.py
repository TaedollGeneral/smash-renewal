# notifications/store.py — 푸시 알림 저장소
#
# 저장소 분리 원칙:
#   - 브라우저 Push 구독 정보 (endpoint, p256dh, auth) → push_db.sqlite (영속)
#   - 카테고리 알림 On/Off, 요일별 정원 확정 상태, Rate Limit 캐시 → In-Memory (휘발성)
#
# DB I/O는 SQLite 구독 테이블 CRUD에서만 발생한다.
# 나머지 상태는 전부 메모리 딕셔너리로 관리하여 빈번한 폴링/상태 조회에서
# 디스크 I/O가 전혀 없도록 설계한다.

import sqlite3
import threading
from pathlib import Path

# ── 경로 설정 ─────────────────────────────────────────────────────────────────

_BASE_DIR = Path(__file__).resolve().parent        # notifications/
_DB_PATH  = _BASE_DIR / "push_db.sqlite"

# ── SQLite 헬퍼 ───────────────────────────────────────────────────────────────

# WAL 모드 + timeout: 동시 읽기 성능 향상 및 쓰기 충돌 방지
_db_lock = threading.Lock()   # 멀티스레드 환경에서 연결 생성을 직렬화


def _get_conn() -> sqlite3.Connection:
    """WAL 모드 SQLite 연결을 반환한다.

    WAL(Write-Ahead Logging) 모드:
      - 읽기와 쓰기가 서로 블록하지 않음 → 폴링 부하 분산에 유리
      - 서버 1GB 환경에서 파일 lock 대기 없이 안정적으로 동작
    """
    conn = sqlite3.connect(str(_DB_PATH), timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")  # WAL+NORMAL 조합으로 성능/안전 균형
    return conn


# ── DB 초기화 ─────────────────────────────────────────────────────────────────

def init_db() -> None:
    """push_subscriptions 테이블을 생성한다 (없는 경우에만).

    스키마:
        user_id   — 학번 (JWT에서 추출, 절대 프론트엔드 값 신뢰 금지)
        endpoint  — Push 서비스 URL (브라우저마다 고유)
        p256dh    — 브라우저 공개 키 (페이로드 암호화에 사용)
        auth      — 인증 시크릿 (VAPID 인증에 사용)

    복합 PK (user_id, endpoint):
      한 사용자가 여러 기기/브라우저에 구독할 수 있도록 endpoint를 PK에 포함.
    """
    conn = _get_conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS push_subscriptions (
                user_id  TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                p256dh   TEXT NOT NULL,
                auth     TEXT NOT NULL,
                PRIMARY KEY (user_id, endpoint)
            )
        """)
        conn.commit()
    finally:
        conn.close()


# ── SQLite CRUD ───────────────────────────────────────────────────────────────

def save_subscription(user_id: str, endpoint: str, p256dh: str, auth: str) -> None:
    """구독 정보를 DB에 저장 (없으면 INSERT, 있으면 p256dh/auth UPDATE).

    Args:
        user_id:  JWT에서 추출한 학번 (백엔드 검증 완료된 값만 전달)
        endpoint: Push 서비스 엔드포인트 URL
        p256dh:   브라우저 공개 키 (Base64url)
        auth:     인증 시크릿 (Base64url)
    """
    conn = _get_conn()
    try:
        conn.execute("""
            INSERT INTO push_subscriptions (user_id, endpoint, p256dh, auth)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, endpoint) DO UPDATE SET
                p256dh = excluded.p256dh,
                auth   = excluded.auth
        """, (user_id, endpoint, p256dh, auth))
        conn.commit()
    finally:
        conn.close()


def delete_subscription(user_id: str, endpoint: str) -> None:
    """특정 사용자의 특정 엔드포인트 구독을 삭제한다.

    Push 서비스에서 410 Gone이 반환될 때 만료된 구독을 정리하는 데 사용.
    """
    conn = _get_conn()
    try:
        conn.execute(
            "DELETE FROM push_subscriptions WHERE user_id = ? AND endpoint = ?",
            (user_id, endpoint)
        )
        conn.commit()
    finally:
        conn.close()


def delete_all_subscriptions_for_user(user_id: str) -> None:
    """사용자의 모든 구독을 삭제한다 (알림 전체 해제 시 사용)."""
    conn = _get_conn()
    try:
        conn.execute(
            "DELETE FROM push_subscriptions WHERE user_id = ?",
            (user_id,)
        )
        conn.commit()
    finally:
        conn.close()


def get_subscriptions_by_user(user_id: str) -> list[dict]:
    """특정 사용자의 모든 구독 정보를 반환한다.

    Returns:
        [{"endpoint": ..., "p256dh": ..., "auth": ...}, ...]
    """
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT endpoint, p256dh, auth FROM push_subscriptions WHERE user_id = ?",
            (user_id,)
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def get_all_subscriptions() -> list[dict]:
    """모든 구독 정보를 반환한다 (전체 공지 발송에 사용).

    Returns:
        [{"user_id": ..., "endpoint": ..., "p256dh": ..., "auth": ...}, ...]
    """
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT user_id, endpoint, p256dh, auth FROM push_subscriptions"
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


# ── 알림 대상 카테고리 집합 ──────────────────────────────────────────────────
# 레슨(WED_LESSON)은 정원 개념이 없으므로 알림 기능 미지원.
NOTIF_CATEGORIES: frozenset[str] = frozenset({
    "WED_REGULAR", "WED_GUEST", "WED_LEFTOVER",
    "FRI_REGULAR", "FRI_GUEST", "FRI_LEFTOVER",
})

# ── In-Memory 상태 ────────────────────────────────────────────────────────────
#
# 아래 전역 변수들은 서버 프로세스 수명과 동일하게 메모리에 상주한다.
# DB를 거치지 않으므로 I/O 비용이 없으며, 서버 재시작 시 초기값으로 돌아간다.
# (구독 정보는 SQLite에서 복구되지만 아래 상태는 모두 초기화됨)

# 사용자별 카테고리별 알림 구독 상태
# 구조: {user_id: {category: bool}}
# 예: {"20231234": {"WED_REGULAR": True, "FRI_GUEST": False, ...}}
_DEFAULT_PREFS: dict[str, bool] = {cat: False for cat in sorted(NOTIF_CATEGORIES)}

category_subscribers: dict[str, dict[str, bool]] = {}

# 요일별 정원 확정 상태 (관리자가 확정 버튼을 눌렀을 때 True로 전환)
# 이 값이 True로 바뀌는 시점에 해당 요일 구독자들에게 푸시를 발송한다.
is_wed_confirmed: bool = False
is_fri_confirmed: bool = False

# Rate Limit 캐시: 알림 설정 토글 남용 방지
# 구조: {user_id: [timestamp_float, ...]}  (최근 N초 내 요청 타임스탬프 목록)
rate_limits: dict[str, list[float]] = {}

# ── In-Memory 헬퍼 함수 ───────────────────────────────────────────────────────

_mem_lock = threading.Lock()   # 인메모리 상태 동시 접근 보호


def get_user_prefs(user_id: str) -> dict[str, bool]:
    """사용자의 카테고리별 알림 설정을 반환한다.

    Returns:
        {category: bool, ...}  — NOTIF_CATEGORIES 전체 키, 미등록 시 기본값 False
    """
    with _mem_lock:
        return dict(category_subscribers.get(user_id, _DEFAULT_PREFS))


def set_user_pref(user_id: str, category: str, enabled: bool) -> None:
    """사용자의 특정 카테고리 알림 설정을 변경한다.

    Args:
        user_id:  JWT에서 추출한 학번
        category: NOTIF_CATEGORIES 중 하나 (예: "WED_REGULAR")
        enabled:  True(구독) / False(해제)
    """
    with _mem_lock:
        if user_id not in category_subscribers:
            category_subscribers[user_id] = dict(_DEFAULT_PREFS)
        if category in NOTIF_CATEGORIES:
            category_subscribers[user_id][category] = enabled


def get_subscribers_for_category(category: str) -> list[str]:
    """특정 카테고리 알림을 구독 중인 user_id 목록을 반환한다.

    Args:
        category: NOTIF_CATEGORIES 중 하나 (예: "WED_REGULAR")

    Returns:
        구독 중인 user_id 리스트
    """
    with _mem_lock:
        return [uid for uid, prefs in category_subscribers.items()
                if prefs.get(category, False)]


def set_wed_confirmed(value: bool) -> None:
    """수요일 정원 확정 상태를 변경한다.

    단순 대입(`is_wed_confirmed = True`)은 외부 모듈에서 전역 변수를 수정하지 못하므로
    반드시 이 함수를 통해 변경해야 한다.
    관리자가 수요일 정원을 확정할 때 호출하고, 매주 리셋 시 False로 되돌린다.
    """
    global is_wed_confirmed
    is_wed_confirmed = value


def set_fri_confirmed(value: bool) -> None:
    """금요일 정원 확정 상태를 변경한다."""
    global is_fri_confirmed
    is_fri_confirmed = value


def check_rate_limit(user_id: str, max_requests: int = 5,
                     window_seconds: float = 60.0) -> bool:
    """Rate limit 검사: window 내 요청 횟수가 max_requests를 초과하면 False 반환.

    동시성 안전: _mem_lock 보호 하에 오래된 타임스탬프를 제거하고
    현재 요청 시각을 추가한다.

    Args:
        user_id:        검사 대상 사용자
        max_requests:   허용 최대 요청 수
        window_seconds: 제한 윈도우 (초)

    Returns:
        True → 허용, False → 차단
    """
    import time
    now = time.monotonic()
    with _mem_lock:
        timestamps = rate_limits.get(user_id, [])
        # window 이전 항목 제거
        timestamps = [t for t in timestamps if now - t < window_seconds]
        if len(timestamps) >= max_requests:
            rate_limits[user_id] = timestamps
            return False
        timestamps.append(now)
        rate_limits[user_id] = timestamps
    return True
