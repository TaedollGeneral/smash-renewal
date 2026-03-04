# worker.py — Redis → SQLite 백그라운드 워커
#
# API 서버(Gunicorn)와 완전히 독립적으로 실행되는 단일 프로세스 스크립트.
# Redis의 apply_queue에서 brpop으로 신청 데이터를 꺼내
# SQLite(smash_db/users.db)의 applications 테이블에 순차적으로 INSERT한다.
#
# [핵심 설계]
#   - 단일 워커 = 단일 SQLite 연결 → "database is locked" 경합 완벽 회피
#   - brpop은 큐가 빌 때까지 블로킹 대기하므로 CPU를 낭비하지 않음
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

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_DB_PATH = os.path.join(_BASE_DIR, "smash_db", "users.db")

_QUEUE_KEY = "apply_queue"
_BRPOP_TIMEOUT = 0  # 0 = 무한 대기 (데이터가 들어올 때까지 블로킹)

# ── Redis 연결 ────────────────────────────────────────────────────────────────

_redis_client = redis.Redis(
    host=os.environ.get("REDIS_HOST", "127.0.0.1"),
    port=int(os.environ.get("REDIS_PORT", 6379)),
    db=int(os.environ.get("REDIS_DB", 0)),
    decode_responses=True,
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
            created_at TEXT    DEFAULT (datetime('now', '+9 hours'))
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


def main() -> None:
    """워커 메인 루프: brpop → INSERT 를 무한 반복한다."""
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    print("[worker] ========================================")
    print("[worker] Redis → SQLite 백그라운드 워커 시작")
    print(f"[worker] DB   : {_DB_PATH}")
    print(f"[worker] Queue : {_QUEUE_KEY}")
    print("[worker] ========================================")

    conn = _init_db()
    processed = 0

    while _running:
        try:
            # brpop: 큐의 오른쪽(가장 오래된 데이터)부터 꺼낸다 (FIFO 순서 보장)
            # timeout=1로 설정하여 _running 플래그를 주기적으로 확인
            result = _redis_client.brpop(_QUEUE_KEY, timeout=1)
            if result is None:
                # 타임아웃 — 큐가 비어있음, 다시 대기
                continue

            _, raw = result  # (queue_name, data)
            entry = json.loads(raw)

            # SQLite INSERT
            conn.execute(
                """INSERT INTO applications
                       (user_id, name, category, type, guest_name, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    entry["user_id"],
                    entry["name"],
                    entry["category"],
                    entry["type"],
                    entry.get("guest_name"),
                    entry["timestamp"],
                ),
            )
            conn.commit()

            processed += 1
            if processed % 100 == 0:
                print(f"[worker] {processed}건 처리 완료")

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

        except json.JSONDecodeError as e:
            # 파싱 불가능한 메시지는 스킵 (큐에서 이미 빠졌으므로 유실)
            print(f"[worker] JSON 파싱 에러: {e} — 해당 메시지 스킵")

        except Exception as e:
            print(f"[worker] 예상치 못한 에러: {e} — 1초 후 재시도")
            time.sleep(1)

    # ── Graceful Shutdown ─────────────────────────────────────────────────
    try:
        conn.close()
    except Exception:
        pass
    print(f"[worker] 종료 완료 — 총 {processed}건 처리")


if __name__ == "__main__":
    main()
