# notifications/store.py — 푸시 알림 저장소
#
# 저장소 분리 원칙:
#   - 브라우저 Push 구독 정보 (endpoint, p256dh, auth) → push_db.sqlite (영속)
#   - 카테고리 알림 On/Off, 요일별 정원 확정 상태 → Redis (Gunicorn 멀티 워커 간 공유)
#   - Rate Limit 캐시 → In-Memory (프로세스별, 정확도보다 성능 우선)
#
# DB I/O는 SQLite 구독 테이블 CRUD에서만 발생한다.
# 확정 상태와 알림 구독 설정은 Redis로 관리하여
# Gunicorn 멀티 워커 간 데이터 정합성을 보장한다.

import os
import sqlite3
import threading
from pathlib import Path

import redis

# ── 경로 설정 ─────────────────────────────────────────────────────────────────

_BASE_DIR = Path(__file__).resolve().parent        # notifications/
_DB_PATH  = _BASE_DIR / "push_db.sqlite"

# ── Redis 연결 (Gunicorn 멀티 워커 간 상태 공유) ──────────────────────────────
_redis = redis.Redis(
    host=os.environ.get("REDIS_HOST", "127.0.0.1"),
    port=int(os.environ.get("REDIS_PORT", 6379)),
    db=int(os.environ.get("REDIS_DB", 0)),
    decode_responses=True,
)

# Redis 키 접두사
_CONFIRMED_KEY_WED = "notif:confirmed:wed"
_CONFIRMED_KEY_FRI = "notif:confirmed:fri"
_CAT_SUB_PREFIX    = "notif:cat:"          # notif:cat:{category} → SET of user_ids

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
        # 동일 endpoint를 가진 다른 user_id의 레코드를 먼저 삭제한다.
        # 한 기기(브라우저)는 마지막으로 로그인한 1명의 유저만 알림 소유권을 갖는다.
        conn.execute(
            "DELETE FROM push_subscriptions WHERE endpoint = ? AND user_id != ?",
            (endpoint, user_id)
        )
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

# ── Redis-backed 상태 (Gunicorn 멀티 워커 간 공유) ─────────────────────────
#
# 정원 확정 상태와 카테고리 알림 구독 설정을 Redis로 관리하여
# Gunicorn fork된 여러 워커 프로세스가 동일한 상태를 공유한다.
#
# Rate Limit 캐시만 In-Memory로 유지 (프로세스별 독립, 정밀도보다 성능 우선)

# Rate Limit 캐시: 알림 설정 토글 남용 방지 (프로세스 로컬)
rate_limits: dict[str, list[float]] = {}
_mem_lock = threading.Lock()


# ── 정원 확정 상태 (Redis) ────────────────────────────────────────────────────

def get_wed_confirmed() -> bool:
    """수요일 정원 확정 상태를 Redis에서 읽어 반환한다."""
    return _redis.get(_CONFIRMED_KEY_WED) == "1"


def get_fri_confirmed() -> bool:
    """금요일 정원 확정 상태를 Redis에서 읽어 반환한다."""
    return _redis.get(_CONFIRMED_KEY_FRI) == "1"


def set_wed_confirmed(value: bool) -> None:
    """수요일 정원 확정 상태를 변경한다 (Redis, 모든 워커에 즉시 반영)."""
    if value:
        _redis.set(_CONFIRMED_KEY_WED, "1")
    else:
        _redis.delete(_CONFIRMED_KEY_WED)


def set_fri_confirmed(value: bool) -> None:
    """금요일 정원 확정 상태를 변경한다 (Redis, 모든 워커에 즉시 반영)."""
    if value:
        _redis.set(_CONFIRMED_KEY_FRI, "1")
    else:
        _redis.delete(_CONFIRMED_KEY_FRI)


# ── 카테고리 알림 구독 (Redis SET per category) ──────────────────────────────

def get_user_prefs(user_id: str) -> dict[str, bool]:
    """사용자의 카테고리별 알림 설정을 반환한다.

    Redis에서 각 카테고리 SET에 user_id가 포함되어 있는지 확인한다.
    Pipeline으로 1회 라운드트립에 전체 카테고리를 조회한다.

    Returns:
        {category: bool, ...}  — NOTIF_CATEGORIES 전체 키
    """
    pipe = _redis.pipeline()
    cats = sorted(NOTIF_CATEGORIES)
    for cat in cats:
        pipe.sismember(f"{_CAT_SUB_PREFIX}{cat}", user_id)
    results = pipe.execute()
    return {cat: bool(r) for cat, r in zip(cats, results)}


def set_user_pref(user_id: str, category: str, enabled: bool) -> None:
    """사용자의 특정 카테고리 알림 설정을 변경한다.

    Args:
        user_id:  JWT에서 추출한 학번
        category: NOTIF_CATEGORIES 중 하나 (예: "WED_REGULAR")
        enabled:  True(구독) / False(해제)
    """
    if category not in NOTIF_CATEGORIES:
        return
    key = f"{_CAT_SUB_PREFIX}{category}"
    if enabled:
        _redis.sadd(key, user_id)
    else:
        _redis.srem(key, user_id)


def get_subscribers_for_category(category: str) -> list[str]:
    """특정 카테고리 알림을 구독 중인 user_id 목록을 반환한다.

    Args:
        category: NOTIF_CATEGORIES 중 하나 (예: "WED_REGULAR")

    Returns:
        구독 중인 user_id 리스트
    """
    return list(_redis.smembers(f"{_CAT_SUB_PREFIX}{category}"))


def reset_weekly_state() -> None:
    """주간 초기화: 카테고리 구독 설정과 정원 확정 상태를 모두 리셋한다.

    매주 토요일 00:00 KST에 time_control/scheduler_logic.py의 weekly-reset
    스레드에서 호출된다. notifications/scheduler.py → 이 함수 순으로 실행된다.

    초기화 대상:
      - 카테고리별 구독 SET 전부 삭제 (알림 On/Off 설정)
        push_subscriptions SQLite 테이블은 건드리지 않는다 (기기 등록 정보 보존).
      - confirmed 키 삭제
        → 프론트엔드의 벨 버튼이 다시 비활성(disabled) 상태로 돌아간다.
    """
    pipe = _redis.pipeline()
    for cat in NOTIF_CATEGORIES:
        pipe.delete(f"{_CAT_SUB_PREFIX}{cat}")
    pipe.delete(_CONFIRMED_KEY_WED)
    pipe.delete(_CONFIRMED_KEY_FRI)
    pipe.execute()


def check_rate_limit(user_id: str, max_requests: int = 5,
                     window_seconds: float = 60.0) -> bool:
    """Rate limit 검사: window 내 요청 횟수가 max_requests를 초과하면 False 반환.

    프로세스 로컬 In-Memory로 유지 (정밀도보다 성능 우선).

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
        timestamps = [t for t in timestamps if now - t < window_seconds]
        if len(timestamps) >= max_requests:
            rate_limits[user_id] = timestamps
            return False
        timestamps.append(now)
        rate_limits[user_id] = timestamps
    return True
