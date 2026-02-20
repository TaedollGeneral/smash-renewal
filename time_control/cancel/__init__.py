# cancel/ — 운동 취소 핵심 로직
#
# 요청 처리 순서 (반드시 이 순서를 지켜야 한다):
#   1. JWT 토큰 검증 + Role 확인 (token_required 데코레이터)
#   2. 권한별 분기 (Manager: 시간 검증 건너뜀, User: 시간 검증 수행 + 본인 인가)
#   3. 동시성 제어: board_store.remove_entry() 원자적 조작
#   4. 응답 반환

from flask import request

from ..board_store import remove_entry
from ..time_handler import validate_cancel_time, _now_kst

# ── 게스트 카테고리 판별 ─────────────────────────────────────────────────────

_GUEST_CATEGORIES = {"WED_GUEST", "FRI_GUEST"}


def _is_guest_category(category: str) -> bool:
    return category in _GUEST_CATEGORIES


# ── 핵심 로직 ────────────────────────────────────────────────────────────────

def handle_cancel(category: str) -> tuple[dict, int]:
    """운동 취소 요청을 처리한다.

    이 함수는 application_routes.py의 /cancel 엔드포인트에서 호출된다.
    호출 전에 다음이 보장되어야 한다:
      - category는 유효한 Category enum 값
      - request.current_user가 설정됨 (token_required 통과)

    Args:
        category: 유효한 Category enum 값

    Returns:
        (response_dict, status_code)
    """
    # ── Step 1: 토큰 정보 추출 ────────────────────────────────────────────────
    user = request.current_user  # token_required가 보장
    role = user["role"]
    user_id = user["id"]

    data = request.get_json() or {}

    # ── Step 2: 권한별 분기 ───────────────────────────────────────────────────
    if role == "manager":
        # Manager: 시간 검증 건너뜀 (Bypass)
        target_user_id = data.get("target_user_id")
        if not target_user_id:
            return {"error": "취소 대상 target_user_id가 필요합니다."}, 400

        cancel_user_id = target_user_id

    else:
        # 일반 회원/게스트: 시간 검증 수행
        now = _now_kst()
        time_error = validate_cancel_time(category, now)
        if time_error:
            return {"error": time_error}, 400

        if _is_guest_category(category):
            # 게스트 취소: body에서 target_user_id를 받되,
            # 반드시 본인이 등록한 게스트인지 인가 검증
            target_user_id = data.get("target_user_id", "").strip()
            if not target_user_id:
                return {"error": "취소할 게스트의 target_user_id가 필요합니다."}, 400

            # 핵심 보안: 게스트 ID는 "guest_{등록자ID}_{이름}" 형식
            # 본인 토큰의 user_id가 접두사에 포함되어야 한다
            expected_prefix = f"guest_{user_id}_"
            if not target_user_id.startswith(expected_prefix):
                return {"error": "본인이 등록한 게스트만 취소할 수 있습니다."}, 403

            cancel_user_id = target_user_id
        else:
            # 일반 회원 본인 취소: 토큰의 user_id를 취소 대상으로 사용
            cancel_user_id = user_id

    # ── Step 3: 동시성 제어 + 인메모리 조작 ───────────────────────────────────
    # board_store.remove_entry()가 단일 Lock 내에서
    # 대상 검색 → pop → 더티 플래그 설정을 수행
    success = remove_entry(category, cancel_user_id)
    if not success:
        return {"error": "취소할 신청 내역이 존재하지 않습니다."}, 404

    # ── Step 4: 응답 반환 ─────────────────────────────────────────────────────
    return {"message": "취소가 완료되었습니다."}, 200
