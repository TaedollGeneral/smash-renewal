# apply/ — 운동 신청 핵심 로직 (일반 회원 본인 신청 전용)
#
# [Level 3 아키텍처 — Redis 비동기 큐]
#
# 요청 처리 순서:
#   1. 타임스탬프 즉시 채번 (time.time(), 밀리초 정밀도)
#   2. 토큰에서 사용자 정보 추출 (token_required 보장)
#   3. 시간 검증 — 항상 수행, 바이패스 없음
#   4. 카테고리별 신청 항목 구성
#   5. Redis apply_queue에 lpush (DB 쓰기 없음, Lock 없음)
#   6. 즉시 200 OK 응답 반환 (목표: 0.001초 이내)
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
import time

import redis
from flask import request

from ..time_handler import validate_apply_time, _now_kst


_GUEST_CATEGORIES = {"WED_GUEST", "FRI_GUEST", "WED_LEFTOVER", "FRI_LEFTOVER"}

_QUEUE_KEY = "apply_queue"

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


def handle_apply(category: str) -> tuple[dict, int]:
    """일반 회원 본인 신청 요청을 처리한다.

    [Level 3] Redis 큐 아키텍처:
      1) 타임스탬프 즉시 채번
      2) 시간 검증 (항상 수행)
      3) 신청 정보를 Redis apply_queue에 lpush
      4) DB 쓰기를 기다리지 않고 즉시 200 OK 반환

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
    _redis_client.lpush(_QUEUE_KEY, json.dumps(entry, ensure_ascii=False))

    # Step 6: 즉시 200 OK 반환
    return {"message": "신청이 접수되었습니다.", "timestamp": ts}, 200
