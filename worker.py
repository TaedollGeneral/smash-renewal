# worker.py — Redis → SQLite 백그라운드 워커
#
# API 서버(Gunicorn)와 완전히 독립적으로 실행되는 단일 프로세스 스크립트.
# Redis의 apply_queue에서 데이터를 꺼내
# SQLite(smash_db/users.db)의 applications 테이블에 INSERT한다.
#
# [핵심 설계]
#   - 단일 워커 = 단일 SQLite 연결 → "database is locked" 경합 완벽 회피
#   - 배치 처리: 최대 BATCH_SIZE건을 한 트랜잭션으로 묶어 INSERT
#     → SQLite lock 점유 횟수를 최대 1/BATCH_SIZE로 감소
#     → 피크타임 큐 적체 시 처리량 대폭 향상
#   - 큐가 빌 때까지 처리 후 짧게 대기(블로킹 없이 반복)
#   - Redis 또는 SQLite 장애 시 자동 재연결 + 로그 출력
#
# 실행: python worker.py

import json
import os
import sqlite3
import signal
import sys
import time

import redis
from dotenv import load_dotenv

load_dotenv()

# ── 설정 ──────────────────────────────────────────────────────────────────────

_BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
_DB_PATH   = os.path.join(_BASE_DIR, "smash_db", "users.db")
_QUEUE_KEY = "apply_queue"

# 배치 크기: 한 트랜잭션에서 처리할 최대 건수
# 평시에는 대부분 1~5건이지만, 피크타임에는 수십~수백 건이 한꺼번에 적재될 수 있다.
_BATCH_SIZE = int(os.environ.get("WORKER_BATCH_SIZE", "50"))

# ── Redis 연결 ────────────────────────────────────────────────────────────────

_redis_client = redis.Redis(
    host=os.environ.get("REDIS_HOST", "127.0.0.1"),
    port=int(os.environ.get("REDIS_PORT", 6379)),
    db=int(os.environ.get("REDIS_DB", 0)),
    decode_responses=True,
    socket_timeout=5,           # Redis hang 시 5초 후 TimeoutError → 자동 재연결
    socket_connect_timeout=3,   # 연결 수립 타임아웃
)


# ── SQLite 초기화 ─────────────────────────────────────────────────────────────

def _init_db() -> sqlite3.Connection:
    """applications 테이블이 없으면 생성하고 연결을 반환한다.

    - WAL 모드: 읽기(API 서버)와 쓰기(워커)가 서로를 블로킹하지 않음
    - 단일 워커만 쓰기를 수행하므로 write lock 경합 없음
    """
    conn = sqlite3.connect(_DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
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
    print(f"[worker] SQLite 연결 완료 (WAL 모드) — {_DB_PATH}")
    return conn


# ── 메인 루프 ─────────────────────────────────────────────────────────────────

_running = True


def _signal_handler(signum, frame):
    """SIGINT/SIGTERM 수신 시 graceful shutdown."""
    global _running
    print(f"\n[worker] 종료 신호 수신 (signal={signum}) — 정상 종료 중...")
    _running = False


def _fetch_batch() -> list[dict]:
    """Redis apply_queue에서 최대 _BATCH_SIZE건을 꺼내 반환한다.

    rpop을 _BATCH_SIZE번 호출하여 현재 적재된 항목을 일괄 수집한다.
    큐가 비어있으면 빈 리스트를 반환한다.
    FIFO 순서 보장: lpush(최신) → rpop(가장 오래된) 순으로 처리.

    ConnectionError/TimeoutError 발생 시 루프를 중단하고 현재까지 수집된
    entries를 반환한다. 이미 rpop된 항목을 버리지 않고 INSERT까지 처리한 뒤,
    다음 iteration에서 재연결을 시도한다. (D1 데이터 유실 방지)
    """
    entries = []
    for _ in range(_BATCH_SIZE):
        try:
            raw = _redis_client.rpop(_QUEUE_KEY)
        except (redis.ConnectionError, redis.TimeoutError):
            break  # 현재까지 수집된 entries 반환 후 처리, 재연결은 다음 루프에서
        if raw is None:
            break  # 큐 소진
        try:
            entries.append(json.loads(raw))
        except json.JSONDecodeError as e:
            print(f"[worker] JSON 파싱 에러: {e} — 해당 메시지 스킵")
    return entries


def _insert_batch(conn: sqlite3.Connection, entries: list[dict]) -> int:
    """entries 목록을 단일 트랜잭션으로 SQLite에 INSERT한다.

    중복 신청은 UNIQUE(category, user_id) 제약으로 자동 무시(INSERT OR IGNORE).
    반환값: 실제 삽입된 건수.
    """
    rows = [
        (
            e["user_id"],
            e["name"],
            e["category"],
            e["type"],
            e.get("guest_name"),
            e["timestamp"],
        )
        for e in entries
    ]
    cursor = conn.executemany(
        """INSERT OR IGNORE INTO applications
               (user_id, name, category, type, guest_name, timestamp)
           VALUES (?, ?, ?, ?, ?, ?)""",
        rows,
    )
    conn.commit()
    return cursor.rowcount  # INSERT OR IGNORE: 실제 삽입 건수


def main() -> None:
    """워커 메인 루프: 배치 fetch → 배치 INSERT를 무한 반복한다."""
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    print("[worker] ========================================")
    print("[worker] Redis → SQLite 백그라운드 워커 시작 (배치 모드)")
    print(f"[worker] DB        : {_DB_PATH}")
    print(f"[worker] Queue     : {_QUEUE_KEY}")
    print(f"[worker] BatchSize : {_BATCH_SIZE}")
    print("[worker] ========================================")

    conn = _init_db()
    processed = 0

    while _running:
        try:
            # 배치 수집: 큐에서 최대 _BATCH_SIZE건 rpop
            entries = _fetch_batch()

            if not entries:
                # 큐가 비어있음 — CPU 낭비 방지를 위해 짧게 대기 후 재확인
                time.sleep(0.1)
                continue

            # 배치 INSERT: 단일 트랜잭션 (SQLite lock 점유 1회)
            inserted = _insert_batch(conn, entries)
            processed += len(entries)

            if processed % 100 == 0:
                print(f"[worker] {processed}건 처리 완료 (이번 배치: {len(entries)}건, 실삽입: {inserted}건)")

        except redis.ConnectionError as e:
            print(f"[worker] Redis 연결 실패: {e} — 3초 후 재시도")
            time.sleep(3)

        except sqlite3.Error as e:
            print(f"[worker] SQLite 에러: {e} — 연결 재시도")
            try:
                conn.close()
            except Exception:
                pass
            time.sleep(1)
            conn = _init_db()

        except Exception as e:
            print(f"[worker] 예상치 못한 에러: {e} — 1초 후 재시도")
            time.sleep(1)

    # ── Graceful Shutdown ─────────────────────────────────────────────────
    # 종료 신호 수신 후 큐에 남은 항목을 마지막으로 한 번 더 처리
    try:
        remaining = _fetch_batch()
        if remaining:
            _insert_batch(conn, remaining)
            processed += len(remaining)
            print(f"[worker] 종료 전 잔여 {len(remaining)}건 처리")
    except Exception:
        pass
    try:
        conn.close()
    except Exception:
        pass
    print(f"[worker] 종료 완료 — 총 {processed}건 처리")


if __name__ == "__main__":
    main()
