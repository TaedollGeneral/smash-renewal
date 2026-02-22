# cancel/ — 운동 취소 핵심 로직 (일반 회원 본인 취소 전용)
#
# 요청 처리 순서:
#   1. 토큰에서 사용자 정보 추출 (token_required 보장)
#   2. 시간 검증 — 항상 수행, 바이패스 없음
#   3. 취소 대상 user_id 결정
#      - 일반 카테고리: 토큰의 user_id 직접 사용
#      - 게스트 카테고리: "guest_{user_id}_*" prefix 탐색
#   4. 동시성 제어: board_store.remove_entry() 원자적 조작
#   5. 응답 반환
#
# [분리 원칙]
#   매니저 대리 취소는 /admin/cancel 엔드포인트(time_control/admin/)가 전담한다.
#   이 모듈은 오직 "로그인한 본인" 취소만 처리하며, role 분기가 존재하지 않는다.

from flask import request

from ..board_store import get_board, remove_entry
from ..time_handler import validate_cancel_time, _now_kst


_GUEST_CATEGORIES = {"WED_GUEST", "FRI_GUEST", "WED_LEFTOVER", "FRI_LEFTOVER"}


def _is_guest_category(category: str) -> bool:
    return category in _GUEST_CATEGORIES


def handle_cancel(category: str) -> tuple[dict, int]:
    """일반 회원 본인 취소 요청을 처리한다.

    /cancel 엔드포인트 전용. manager 바이패스 로직 없음.
    시간 검증은 모든 요청에 대해 항상 수행한다.
    """
    # Step 1: 토큰 정보 추출
    user = request.current_user
    user_id = user["id"]

    # Step 2: 시간 검증 (바이패스 없음 — role 무관하게 항상 실행)
    now = _now_kst()
    time_error = validate_cancel_time(category, now)
    if time_error:
        return {"error": time_error}, 400

    # Step 3: 취소 대상 user_id 결정
    if _is_guest_category(category):
        # 게스트 취소: 프론트엔드는 category만 전송.
        # "guest_{본인ID}_*" prefix로 인메모리 보드를 스캔해 본인 항목 식별.
        # 보안: prefix에 자신의 user_id가 포함되어 타인 항목 접근 불가.
        prefix = f"guest_{user_id}_"
        entries = get_board(category)
        cancel_user_id = next(
            (e["user_id"] for e in entries if e["user_id"].startswith(prefix)),
            None,
        )
        if cancel_user_id is None:
            return {"error": "취소할 게스트 신청 내역이 없습니다."}, 404
    else:
        # 일반 취소: 토큰의 user_id가 곧 취소 대상
        cancel_user_id = user_id

    # Step 4: 동시성 제어 + 인메모리 조작
    success = remove_entry(category, cancel_user_id)
    if not success:
        return {"error": "취소할 신청 내역이 존재하지 않습니다."}, 404

    # Step 5: 응답 반환
    return {"message": "취소가 완료되었습니다."}, 200
