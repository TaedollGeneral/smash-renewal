# apply/ — 운동 신청 핵심 로직 (일반 회원 본인 신청 전용)
#
# 요청 처리 순서:
#   1. 타임스탬프 즉시 채번 (time.time())
#   2. 토큰에서 사용자 정보 추출 (token_required 보장)
#   3. 시간 검증 — 항상 수행, 바이패스 없음
#   4. 카테고리별 신청 항목 구성
#   5. 동시성 제어: board_store.apply_entry() 원자적 조작
#   6. 응답 반환
#
# [분리 원칙]
#   매니저 대리 신청은 /admin/apply 엔드포인트(time_control/admin/)가 전담한다.
#   이 모듈은 오직 "로그인한 본인" 신청만 처리하며, role 분기가 존재하지 않는다.

import html
import time

from flask import request

from ..board_store import apply_entry
from ..time_handler import validate_apply_time, _now_kst


_GUEST_CATEGORIES = {"WED_GUEST", "FRI_GUEST", "WED_LEFTOVER", "FRI_LEFTOVER"}


def _is_guest_category(category: str) -> bool:
    return category in _GUEST_CATEGORIES


def _sanitize_name(name: str) -> str:
    return html.escape(name, quote=True)


def handle_apply(category: str) -> tuple[dict, int]:
    """일반 회원 본인 신청 요청을 처리한다.

    /apply 엔드포인트 전용. manager 바이패스 로직 없음.
    시간 검증은 모든 요청에 대해 항상 수행한다.
    """
    # Step 1: 타임스탬프 즉시 채번
    ts = round(time.time(), 2)

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
        # 게시판 표시: No | user_name(신청자) | guest_name(게스트) | 신청시간
        entry = {
            "user_id":    f"guest_{user_id}_{sanitized_guest}",
            "name":       user_name,         # 게시판 '신청자' 열
            "guest_name": sanitized_guest,   # 게시판 '게스트' 열
            "type":       "guest",
            "timestamp":  ts,
        }
    else:
        entry = {
            "user_id":   user_id,
            "name":      user_name,
            "type":      "member",
            "timestamp": ts,
        }

    # Step 5: 동시성 제어 + 인메모리 조작
    success, reason = apply_entry(category, entry)
    if not success:
        return {"error": reason}, 409

    # Step 6: 응답 반환
    return {"message": "신청이 완료되었습니다."}, 200
