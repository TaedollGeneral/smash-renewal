# cancel/ — 운동 취소 핵심 로직 (일반 회원 본인 취소 전용)
#
# 요청 처리 순서:
#   1. 토큰에서 사용자 정보 추출 (token_required 보장)
#   2. 시간 검증 — 항상 수행, 바이패스 없음
#   3. 취소 대상 user_id 결정
#      - 일반 카테고리: 토큰의 user_id 직접 사용
#      - 게스트 카테고리: "guest_{user_id}_*" prefix 탐색
#   3.5. 빈자리 감지를 위한 취소 전 보드 위치 기록
#   4. 동시성 제어: board_store.remove_entry() 원자적 조작
#   5. 빈자리 알림 트리거 (정원 확정 상태 + 정원 내 인원이었을 때만)
#   6. 응답 반환
#
# [분리 원칙]
#   매니저 대리 취소는 /admin/cancel 엔드포인트(time_control/admin/)가 전담한다.
#   이 모듈은 오직 "로그인한 본인" 취소만 처리하며, role 분기가 존재하지 않는다.

from flask import request

from ..board_store import get_board, remove_entry
from ..time_handler import validate_cancel_time, _now_kst


_GUEST_CATEGORIES = {"WED_GUEST", "FRI_GUEST", "WED_LEFTOVER", "FRI_LEFTOVER"}

# 빈자리 알림을 지원하는 카테고리 → (요일_한글, 요일_영문, 게스트_카테고리)
# 운동 카테고리만 관리자 정원 확정 + 빈자리 알림 대상이다.
_VACANCY_CATEGORY_MAP: dict[str, tuple[str, str, str]] = {
    "WED_REGULAR": ("수", "wed", "WED_GUEST"),
    "FRI_REGULAR": ("금", "fri", "FRI_GUEST"),
}


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

    # Step 3.5: 빈자리 감지를 위한 취소 전 순번 기록
    # remove_entry() 호출 후에는 위치 정보가 사라지므로 반드시 먼저 스냅샷한다.
    # get_board()는 얕은 복사본을 반환하므로 이후 보드 변경과 무관하게 안전하다.
    entries_pre = get_board(category)
    cancel_pos = next(
        (i for i, e in enumerate(entries_pre) if e["user_id"] == cancel_user_id),
        -1,
    )

    # Step 4: 동시성 제어 + 인메모리 조작
    success = remove_entry(category, cancel_user_id)
    if not success:
        return {"error": "취소할 신청 내역이 존재하지 않습니다."}, 404

    # Step 5: 빈자리 알림 트리거
    # 정원 확정 상태이고, 취소한 인원이 정원 내에 있던 경우에만 알림을 발송한다.
    # Non-blocking: 큐에 추가만 하고 즉시 반환 (응답 지연 없음)
    _check_and_notify_vacancy(category, cancel_pos)

    # Step 6: 응답 반환
    return {"message": "취소가 완료되었습니다."}, 200


# ── 빈자리 감지 + 알림 큐잉 ──────────────────────────────────────────────────

def _check_and_notify_vacancy(category: str, cancel_pos: int) -> None:
    """취소된 사용자가 확정 정원 내 인원이었는지 판별하고, 빈자리 알림을 큐잉한다.

    처리 흐름:
      1) 카테고리 필터 — WED_REGULAR / FRI_REGULAR 외 즉시 리턴
      2) 해당 요일 정원 확정 여부 확인 (is_*_confirmed == True일 때만 진행)
      3) admin/capacity/store에서 총 정원 조회
      4) calculate_capacity_details()로 유효 정원 계산
         · effective_capacity = details["운동"] + details["잔여석"]
         · 이 합은 총 유효 슬롯 수로 항상 일정 (일반 보드 변경에 무관)
      5) cancel_pos(0-based) < effective_capacity → 정원 내 인원이었음
         → enqueue_push_to_day_subscribers()로 타겟 알림 큐잉 (Non-blocking)

    Args:
        category:   취소가 발생한 카테고리 (예: "WED_REGULAR")
        cancel_pos: 취소 전 보드에서의 0-based 인덱스.
                    항목을 찾지 못한 경우 -1 (알림 발송 안 함).
    """
    # ① 알림 대상 카테고리만 처리
    if category not in _VACANCY_CATEGORY_MAP:
        return

    if cancel_pos < 0:
        return

    day_korean, day_eng, guest_category = _VACANCY_CATEGORY_MAP[category]

    # ② 요일별 정원 확정 상태 확인 (In-Memory, I/O 없음)
    # 모듈 참조로 접근하여 항상 최신값을 읽는다 (직접 import 시 stale 값 문제 방지)
    import notifications.store as _nstore
    confirmed = _nstore.is_wed_confirmed if day_eng == "wed" else _nstore.is_fri_confirmed
    if not confirmed:
        return

    # ③ 총 정원 조회 (In-Memory Write-Through 캐시, DB I/O 없음)
    from admin.capacity.store import get_capacities
    caps = get_capacities()
    total_capacity = caps.get(day_korean)
    if total_capacity is None:
        return  # 아직 정원이 설정되지 않음

    # ④ 유효 정원 계산
    # calculate_capacity_details()는 취소 후 호출하지만,
    # effective_capacity = details["운동"] + details["잔여석"] 는 항상 총 유효 슬롯 수와 같다.
    # (일반 보드 크기와 무관한 값 — total_capacity와 게스트 보드에만 의존)
    from admin.capacity.calculator import calculate_capacity_details, count_special_guests
    special_count = count_special_guests(guest_category)
    details = calculate_capacity_details(day_korean, total_capacity, special_count)
    effective_capacity = details["운동"] + details["잔여석"]

    # ⑤ 정원 내 인원 판별 (0-based index: cancel_pos < effective_capacity)
    if cancel_pos >= effective_capacity:
        return  # 대기 순번이었음 → 실제 빈자리 없음

    # 빈자리 발생! 해당 요일 알림 구독자에게 타겟 발송 큐잉 (Non-blocking)
    from notifications.sender import enqueue_push_to_day_subscribers

    _MESSAGES = {
        "wed": ("수요일 빈자리 알림", "수요일 운동에 빈자리가 생겼습니다!"),
        "fri": ("금요일 빈자리 알림", "금요일 운동에 빈자리가 생겼습니다!"),
    }
    title, body = _MESSAGES[day_eng]
    enqueue_push_to_day_subscribers(day_eng, title=title, body=body)
