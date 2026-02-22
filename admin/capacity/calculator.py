# admin/capacity/calculator.py — 정원 상세 분할 연산 모듈
#
# 총 정원(total)을 동아리 규칙에 따라
# 운동 / 게스트 / 잔여석 3개 카테고리로 분리하는 순수 연산 함수.

from time_control import board_store
from time_control.scheduler_logic import Category


def calculate_capacity_details(day: str, total_capacity: int, special_count: int) -> dict:
    """총 정원을 동아리 규칙에 따라 3가지 카테고리로 분리한다.

    수요일: 게스트 0 → 운동 = min(신청자, 총정원), 잔여석 = 나머지
    금요일: 게스트 최대 2 (일반 게스트 기준) → 나머지를 운동으로 이월,
            운동 = min(신청자, 이월 후 정원), 잔여석 = 나머지

    Args:
        day: 요일 ("수" 또는 "금")
        total_capacity: 총 정원 (예: 48)
        special_count: 게스트 명단 중 (ob)/(교류전) 특수 인원 수

    Returns:
        {"운동": int, "게스트": {"limit": int, "special_count": int}, "잔여석": int}
    """
    if day == "수":
        # 수요일: 게스트 정원 0, 총정원 전체가 운동 카테고리
        s = total_capacity
        guest_limit = 0
        e = len(board_store.get_board(Category.WED_REGULAR))
        exercise = min(e, s)
        leftover = max(0, s - e)
    else:
        # 금요일: 게스트 최대 2 (특수 인원 제외한 일반 게스트 기준)
        f = total_capacity
        guest_entries = board_store.get_board(Category.FRI_GUEST)
        g = sum(
            1 for entry in guest_entries
            if "(ob)" not in entry.get("guest_name", "").lower()
            and "(교류전)" not in entry.get("guest_name", "").lower()
        )
        guest_limit = min(g, 2)
        r = f - guest_limit
        e = len(board_store.get_board(Category.FRI_REGULAR))
        exercise = min(e, r)
        leftover = max(0, r - e)

    return {
        "운동": exercise,
        "게스트": {
            "limit": guest_limit,
            "special_count": special_count,
        },
        "잔여석": leftover,
    }


def count_special_guests(category: str) -> int:
    """해당 카테고리 게스트 명단에서 (ob)/(교류전) 특수 인원 수를 센다.

    Args:
        category: Category enum 값 (예: "WED_GUEST", "FRI_GUEST")

    Returns:
        특수 키워드가 포함된 게스트 수
    """
    entries = board_store.get_board(category)
    count = 0
    for entry in entries:
        guest_lower = entry.get("guest_name", "").lower()
        if "(ob)" in guest_lower or "(교류전)" in guest_lower:
            count += 1
    return count
