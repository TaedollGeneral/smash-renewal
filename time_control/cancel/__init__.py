# cancel/ — 운동 취소 핵심 로직 (일반 회원 본인 취소 전용)
#
# 요청 처리 순서 (반드시 이 순서를 지켜야 한다):
#   1. 토큰에서 사용자 정보 추출 (token_required 데코레이터가 보장)
#   2. 시간 검증 — 항상 수행, 바이패스(Bypass) 없음
#   3. 취소 대상 user_id 결정
#      - 일반 카테고리: 토큰의 user_id를 직접 사용
#      - 게스트 카테고리: "guest_{user_id}_*" prefix 탐색으로 본인 항목 확인
#   4. 동시성 제어: board_store.remove_entry() 원자적 조작
#   5. 응답 반환
#
# [분리 원칙]
#   매니저 대리 취소는 /admin/cancel 엔드포인트(time_control/admin/)가 전담한다.
#   이 모듈은 오직 "로그인한 본인" 취소만 처리하며, role 분기가 존재하지 않는다.

from flask import request

from ..board_store import get_board, remove_entry
from ..time_handler import validate_cancel_time, _now_kst


# ── 게스트 카테고리 판별 ─────────────────────────────────────────────────────

_GUEST_CATEGORIES = {"WED_GUEST", "FRI_GUEST"}


def _is_guest_category(category: str) -> bool:
    return category in _GUEST_CATEGORIES


# ── 핵심 로직 ────────────────────────────────────────────────────────────────

def handle_cancel(category: str) -> tuple[dict, int]:
    """일반 회원 본인 취소 요청을 처리한다.

    /cancel 엔드포인트에서 호출된다.
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
    user_id = user["id"]

    # ── Step 2: 시간 검증 (바이패스 없음) ─────────────────────────────────────
    now = _now_kst()
    time_error = validate_cancel_time(category, now)
    if time_error:
        return {"error": time_error}, 400

    # ── Step 3: 취소 대상 user_id 결정 ───────────────────────────────────────
    if _is_guest_category(category):
        # 게스트 취소: 본인이 등록한 게스트 항목을 prefix 탐색으로 식별.
        # 프론트엔드는 category만 전송하므로, "guest_{본인ID}_*" 형식으로
        # 인메모리 보드를 스캔하여 대상 항목을 찾는다.
        # 보안: prefix에 자신의 user_id가 포함되어 있으므로 타인 항목 접근 불가.
        prefix = f"guest_{user_id}_"
        entries = get_board(category)  # 얕은 복사본(snapshot)
        cancel_user_id = next(
            (e["user_id"] for e in entries if e["user_id"].startswith(prefix)),
            None,
        )
        if cancel_user_id is None:
            return {"error": "취소할 게스트 신청 내역이 없습니다."}, 404
    else:
        # 일반 회원 본인 취소: 토큰의 user_id가 곧 취소 대상
        cancel_user_id = user_id

    # ── Step 4: 동시성 제어 + 인메모리 조작 ───────────────────────────────────
    # board_store.remove_entry()가 단일 Lock 내에서
    # 대상 검색 → pop → 더티 플래그 설정을 수행
    success = remove_entry(category, cancel_user_id)
    if not success:
        return {"error": "취소할 신청 내역이 존재하지 않습니다."}, 404

    # ── Step 5: 응답 반환 ─────────────────────────────────────────────────────
    return {"message": "취소가 완료되었습니다."}, 200
