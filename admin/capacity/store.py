# admin/capacity/store.py — 운동 정원 Redis + SQLite 저장소
#
# 구조:
#   Redis: capacity:wed, capacity:fri  (int as string | absent → None)
#   SQLite: capacities 테이블         (서버 재시작 후 Redis 복원용)
#
# 동작:
#   init_cache()          — 서버 부팅 시 1회, SQLite → Redis 적재
#   get_capacities()      — Redis에서 반환 (모든 Gunicorn 워커 공유)
#   update_capacities()   — Redis 업데이트 + SQLite 영구 저장
#   reset_capacities()    — 주간 리셋 시 Redis + SQLite 모두 초기화
import os
import sqlite3

import redis as _redis_mod

# ── DB 경로 (smash_db/users.db 와 같은 디렉터리) ───────────────────────────────
_DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', '..', 'smash_db', 'users.db',
)

# ── Redis 연결 (notifications/store.py 와 동일한 패턴) ───────────────────────────
_redis = _redis_mod.Redis(
    host=os.environ.get("REDIS_HOST", "127.0.0.1"),
    port=int(os.environ.get("REDIS_PORT", 6379)),
    db=int(os.environ.get("REDIS_DB", 0)),
    decode_responses=True,
)

# Redis 키: 요일 한글 → 키 이름
_DAY_KEYS: dict[str, str] = {
    "수": "capacity:wed",
    "금": "capacity:fri",
}


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
    """서버 부팅 시 1회 호출. SQLite에서 마지막 확정 정원을 읽어 Redis에 적재한다."""
    conn = sqlite3.connect(_DB_PATH)
    try:
        _ensure_table(conn)
        rows = conn.execute("SELECT day, value FROM capacities").fetchall()
        for day, value in rows:
            if day in _DAY_KEYS:
                _redis.set(_DAY_KEYS[day], value)
    finally:
        conn.close()


def get_capacities() -> dict[str, int | None]:
    """Redis에서 정원을 반환한다. (모든 Gunicorn 워커가 동일한 값을 본다)"""
    result: dict[str, int | None] = {}
    for day, key in _DAY_KEYS.items():
        val = _redis.get(key)
        result[day] = int(val) if val is not None else None
    return result


def update_capacities(data: dict) -> None:
    """Redis를 먼저 업데이트한 뒤, SQLite에도 영구 저장한다.

    Args:
        data: {"수"?: int, "금"?: int} — 변경할 요일의 정원만 포함.
    """
    updates = {k: v for k, v in data.items() if k in _DAY_KEYS and isinstance(v, int)}
    if not updates:
        return

    # 1) Redis 업데이트 (즉시 모든 워커에 반영)
    for day, value in updates.items():
        _redis.set(_DAY_KEYS[day], value)

    # 2) SQLite 영구 저장 (재시작 후 Redis 복원용)
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


def reset_capacities() -> None:
    """주간 리셋: Redis 키를 삭제하고 SQLite 행도 삭제한다."""
    # 1) Redis 초기화
    for key in _DAY_KEYS.values():
        _redis.delete(key)

    # 2) SQLite 삭제
    conn = sqlite3.connect(_DB_PATH)
    try:
        _ensure_table(conn)
        conn.execute("DELETE FROM capacities")
        conn.commit()
    finally:
        conn.close()
