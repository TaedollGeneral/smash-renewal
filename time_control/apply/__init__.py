# apply/ — 운동 신청 핵심 로직 (일반 회원 본인 신청 전용)
#
# [Level 3 아키텍처 — Redis 비동기 큐]
#
# 요청 처리 순서:
#   1. 타임스탬프 즉시 채번 (time.time(), 밀리초 정밀도)
#   2. 토큰에서 사용자 정보 추출 (token_required 보장)
#   3. 시간 검증 — 항상 수행, 바이패스 없음
#   3.5. 중복 신청 검증 — SQLite에서 기존 신청 여부 확인 (UNIQUE 인덱스 활용, ~0.3ms)
#   4. 카테고리별 신청 항목 구성
#   5. Redis apply_queue에 lpush (DB 쓰기 없음, Lock 없음)
#   6. 즉시 200 OK 응답 반환
#
# 기존 board_store.apply_entry() 호출을 제거하고
# Redis In-memory Queue로 대체하여 I/O 병목을 완전 해소한다.
# 실제 SQLite 쓰기는 별도의 worker.py가 brpop으로 처리한다.
#
# [분리 원칙]
#   매니저 대리 신청은 /admin/apply 엔드포인트(time_control/admin/)가 전담한다.
#   이 모듈은 오직 "로그인한 본인" 신청만 처리하며, role 분기가 존재하지 않는다.

import html
import json
import os
import sqlite3
import time

import redis
from flask import request

from ..time_handler import validate_apply_time, _now_kst


_GUEST_CATEGORIES = {"WED_GUEST", "FRI_GUEST", "WED_LEFTOVER", "FRI_LEFTOVER"}

_QUEUE_KEY = "apply_queue"

# ── 중복 신청 검증용 카테고리 (게스트 제외 — 동일 사용자 1회만 신청 가능) ──────
_UNIQUE_APPLY_CATEGORIES = {"WED_REGULAR", "FRI_REGULAR", "WED_LESSON"}

# ── SQLite 경로 ──────────────────────────────────────────────────────────────
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DB_PATH = os.path.join(_BASE_DIR, "smash_db", "users.db")

# ── Redis 연결 ────────────────────────────────────────────────────────────────
# Gunicorn fork 이후 각 워커가 독립적으로 연결을 생성한다.
# redis-py는 lazy connection이므로 모듈 레벨 초기화가 안전하다.
_redis_client = redis.Redis(
    host=os.environ.get("REDIS_HOST", "127.0.0.1"),
    port=int(os.environ.get("REDIS_PORT", 6379)),
    db=int(os.environ.get("REDIS_DB", 0)),
    decode_responses=True,
)


def _is_guest_category(category: str) -> bool:
    return category in _GUEST_CATEGORIES


def _sanitize_name(name: str) -> str:
    return html.escape(name, quote=True)


def _is_already_applied(category: str, user_id: str) -> bool:
    """SQLite에서 해당 카테고리에 이미 신청했는지 확인한다.

    UNIQUE(category, user_id) 인덱스를 활용하므로 ~0.3ms 이내로 완료된다.
    WAL 모드에서 읽기는 쓰기와 비블로킹이므로 worker와 경합하지 않는다.
    """
    conn = sqlite3.connect(_DB_PATH, timeout=5)
    try:
        row = conn.execute(
            "SELECT 1 FROM applications WHERE category = ? AND user_id = ? LIMIT 1",
            (category, user_id),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def handle_apply(category: str) -> tuple[dict, int]:
    """일반 회원 본인 신청 요청을 처리한다.

    [Level 3] Redis 큐 아키텍처:
      1) 타임스탬프 즉시 채번
      2) 시간 검증 (항상 수행)
      3) 중복 신청 검증 (WED_REGULAR, FRI_REGULAR, WED_LESSON)
      4) 신청 정보를 Redis apply_queue에 lpush
      5) DB 쓰기를 기다리지 않고 즉시 200 OK 반환

    /apply 엔드포인트 전용. manager 바이패스 로직 없음.
    """
    # Step 1: 타임스탬프 즉시 채번 (밀리초 정밀도)
    ts = time.time()

    # Step 2: 토큰 정보 추출
    user = request.current_user
    user_id = user["id"]
    user_name = user["name"]
    data = request.get_json() or {}

    # Step 3: 시간 검증 (바이패스 없음 — role 무관하게 항상 실행)
    now = _now_kst()
    time_error = validate_apply_time(category, now)
    if time_error:
        return {"error": time_error}, 400

    # Step 3.5: 중복 신청 검증 (수요일 운동, 금요일 운동, 수요일 레슨)
    if category in _UNIQUE_APPLY_CATEGORIES:
        if _is_already_applied(category, user_id):
            return {"error": "이미 신청되어 있습니다."}, 409

    # Step 4: 카테고리별 신청 항목 구성
    if _is_guest_category(category):
        guest_name = data.get("guest_name", "").strip()
        if not guest_name:
            return {"error": "게스트 이름을 입력해주세요."}, 400
        if len(guest_name) > 20:
            return {"error": "게스트 이름은 20자 이하로 입력해주세요."}, 400
        sanitized_guest = _sanitize_name(guest_name)
        entry = {
            "user_id":    f"guest_{user_id}_{sanitized_guest}",
            "name":       user_name,
            "guest_name": sanitized_guest,
            "type":       "guest",
            "category":   category,
            "timestamp":  ts,
        }
    else:
        entry = {
            "user_id":   user_id,
            "name":      user_name,
            "type":      "member",
            "category":  category,
            "timestamp": ts,
        }

    # Step 5: Redis 큐에 즉시 밀어넣기 (DB 쓰기 대기 없음, Lock 없음)
    # Redis 장애 시 SQLite 직접 쓰기로 폴백하여 서비스 가용성을 보장한다.
    try:
        _redis_client.lpush(_QUEUE_KEY, json.dumps(entry, ensure_ascii=False))
    except Exception:
        # Redis 장애 → SQLite 직접 INSERT (매니저 대리 신청과 동일 경로)
        from ..board_store import apply_entry as _direct_apply
        success, reason = _direct_apply(category, entry)
        if not success:
            return {"error": reason}, 409

    # Step 6: 즉시 200 OK 반환
    return {"message": "신청이 접수되었습니다.", "timestamp": ts}, 200
