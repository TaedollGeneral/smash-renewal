# apply/ — 운동 신청 핵심 로직 (일반 회원 본인 신청 전용)
#
# 요청 처리 순서 (반드시 이 순서를 지켜야 한다):
#   1. 타임스탬프 즉시 채번 (time.time(), 소수 둘째 자리)
#   2. 토큰에서 사용자 정보 추출 (token_required 데코레이터가 보장)
#   3. 시간 검증 — 항상 수행, 바이패스(Bypass) 없음
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


# ── 입력 새니타이즈 ──────────────────────────────────────────────────────────

def _sanitize_name(name: str) -> str:
    """게스트 이름의 XSS 특수문자를 이스케이프한다."""
    return html.escape(name, quote=True)


# ── 카테고리 타입 판별 ───────────────────────────────────────────────────────

_GUEST_CATEGORIES = {"WED_GUEST", "FRI_GUEST"}


def _is_guest_category(category: str) -> bool:
    return category in _GUEST_CATEGORIES


# ── 핵심 로직 ────────────────────────────────────────────────────────────────

def handle_apply(category: str) -> tuple[dict, int]:
    """일반 회원 본인 신청 요청을 처리한다.

    /apply 엔드포인트에서 호출된다.
    호출 전에 다음이 보장되어야 한다:
      - category는 유효한 Category enum 값
      - request.current_user가 설정됨 (token_required 통과)

    Args:
        category: 유효한 Category enum 값

    Returns:
        (response_dict, status_code)
    """
    # ── Step 1: 타임스탬프 즉시 채번 (최우선) ─────────────────────────────────
    ts = round(time.time(), 2)

    # ── Step 2: 토큰 정보 추출 ────────────────────────────────────────────────
    user = request.current_user  # token_required가 보장
    user_id = user["id"]
    user_name = user["name"]

    data = request.get_json() or {}

    # ── Step 3: 시간 검증 (바이패스 없음) ─────────────────────────────────────
    now = _now_kst()
    time_error = validate_apply_time(category, now)
    if time_error:
        return {"error": time_error}, 400

    # ── Step 4: 카테고리별 신청 항목 구성 ─────────────────────────────────────
    if _is_guest_category(category):
        # 게스트 신청: Request Body에서 게스트 이름 수신
        guest_name = data.get("guest_name", "").strip()
        if not guest_name:
            return {"error": "게스트 이름을 입력해주세요."}, 400

        # XSS 방어: 특수문자 이스케이프
        apply_name = _sanitize_name(guest_name)
        # 게스트 식별자: 신청자 ID + 게스트 이름으로 고유성 확보
        apply_user_id = f"guest_{user_id}_{apply_name}"
        apply_type = "guest"
    else:
        # 일반 회원 본인 신청 (운동 · 잔여석 · 레슨)
        apply_user_id = user_id
        apply_name = user_name
        apply_type = "member"

    # ── Step 5: 동시성 제어 + 인메모리 조작 ───────────────────────────────────
    # board_store.apply_entry()가 단일 Lock 내에서
    # 중복 검사 → append → 타임스탬프 정렬 → 더티 플래그 설정을 수행
    entry = {
        "user_id": apply_user_id,
        "name": apply_name,
        "type": apply_type,
        "timestamp": ts,
    }

    success, reason = apply_entry(category, entry)
    if not success:
        return {"error": reason}, 409

    # ── Step 6: 응답 반환 ─────────────────────────────────────────────────────
    return {"message": "신청이 완료되었습니다."}, 200
