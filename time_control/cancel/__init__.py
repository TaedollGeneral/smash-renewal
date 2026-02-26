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

# [변경됨] 빈자리 알림을 지원하는 카테고리 → (요일_한글, 요일_영문, 게스트_카테고리)
# 기존에는 정규 운동(WED_REGULAR, FRI_REGULAR)만 등록되어 있었으나,
# 게스트(_GUEST)와 잔여석(_LEFTOVER) 카테고리를 추가하여 전 카테고리 알림을 지원한다.
# 튜플 구조: (요일_한글, 요일_영문, 게스트_카테고리)
#   · 요일_한글: get_capacities() 딕셔너리 조회 키 ("수" / "금")
#   · 요일_영문: 확정 상태 플래그 선택 ("wed" / "fri")
#   · 게스트_카테고리: count_special_guests() 호출 시 사용할 게스트 보드 카테고리명
_VACANCY_CATEGORY_MAP: dict[str, tuple[str, str, str]] = {
    # ── 정규 운동 ─────────────────────────────────────────────────────────────
    "WED_REGULAR":  ("수", "wed", "WED_GUEST"),
    "FRI_REGULAR":  ("금", "fri", "FRI_GUEST"),
    # ── [추가] 게스트 ──────────────────────────────────────────────────────────
    "WED_GUEST":    ("수", "wed", "WED_GUEST"),
    "FRI_GUEST":    ("금", "fri", "FRI_GUEST"),
    # ── [추가] 잔여석 ──────────────────────────────────────────────────────────
    "WED_LEFTOVER": ("수", "wed", "WED_GUEST"),
    "FRI_LEFTOVER": ("금", "fri", "FRI_GUEST"),
}

# [추가] 카테고리 영문 키 → 한글 표시명 매핑 (알림 메시지 동적 생성에 사용)
_CATEGORY_DISPLAY_NAMES: dict[str, str] = {
    "WED_REGULAR":  "수요일 운동",
    "FRI_REGULAR":  "금요일 운동",
    "WED_GUEST":    "수요일 게스트",
    "FRI_GUEST":    "금요일 게스트",
    "WED_LEFTOVER": "수요일 잔여석",
    "FRI_LEFTOVER": "금요일 잔여석",
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
      1) 카테고리 필터 — _VACANCY_CATEGORY_MAP 에 없는 카테고리는 즉시 리턴
      2) 해당 요일 정원 확정 여부 확인 (is_*_confirmed == True일 때만 진행)
      3) admin/capacity/store에서 총 정원 조회
      4) calculate_capacity_details()로 유효 정원 계산
         · 카테고리 종류에 따라 effective_capacity를 다르게 분기:
           - _REGULAR  : details["운동"] + details["잔여석"]
           - _GUEST    : details["게스트"]["limit"] + details["게스트"]["special_count"]
           - _LEFTOVER : details["잔여석"]
      5) cancel_pos(0-based) < effective_capacity → 정원 내 인원이었음
         → enqueue_push_to_category_subscribers()로 타겟 알림 큐잉 (Non-blocking)

    Args:
        category:   취소가 발생한 카테고리 (예: "WED_REGULAR", "FRI_GUEST")
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
    # effective_capacity 는 총 유효 슬롯 수로 항상 일정하다
    # (일반 보드 크기와 무관한 값 — total_capacity와 게스트 보드에만 의존)
    from admin.capacity.calculator import calculate_capacity_details, count_special_guests
    special_count = count_special_guests(guest_category)
    details = calculate_capacity_details(day_korean, total_capacity, special_count)

    # [변경됨] 기존의 하드코딩된 effective_capacity 식을 제거하고,
    # 카테고리 종류(_REGULAR / _GUEST / _LEFTOVER)에 따라 동적으로 분기한다.
    if category.endswith("_REGULAR"):
        # 정규 운동: 운동 슬롯 + 잔여석 슬롯의 합 (총 유효 슬롯)
        effective_capacity = details["운동"] + details["잔여석"]
    elif category.endswith("_GUEST"):
        # 게스트: 일반 게스트 정원 + 특수 인원(ob / 교류전) 수
        effective_capacity = details["게스트"]["limit"] + details["게스트"]["special_count"]
    else:
        # 잔여석(_LEFTOVER): 잔여석 슬롯만
        effective_capacity = details["잔여석"]

    # ⑤ 정원 내 인원 판별 (0-based index: cancel_pos < effective_capacity)
    if cancel_pos >= effective_capacity:
        return  # 대기 순번이었음 → 실제 빈자리 없음

    # 빈자리 발생! 해당 카테고리 알림 구독자에게 타겟 발송 큐잉 (Non-blocking)
    from notifications.sender import enqueue_push_to_category_subscribers

    # [변경됨] 하드코딩된 _MESSAGES 딕셔너리를 삭제하고,
    # _CATEGORY_DISPLAY_NAMES 를 참조하여 title·body를 동적으로 생성한다.
    category_name = _CATEGORY_DISPLAY_NAMES[category]
    title = f"{category_name} 빈자리 알림"
    body  = f"{category_name}에 빈자리가 생겼습니다!"
    enqueue_push_to_category_subscribers(category, title=title, body=body)