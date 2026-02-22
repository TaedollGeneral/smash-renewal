# admin/capacity/calculator.py — 정원 상세 분할 연산 모듈
#
# 총 정원(total)을 동아리 규칙에 따라
# 운동 / 게스트 / 잔여석 3개 카테고리로 분리하는 순수 연산 함수.

from time_control import board_store


def calculate_capacity_details(total_capacity: int, special_count: int) -> dict:
    """총 정원을 동아리 규칙에 따라 3가지 카테고리로 분리한다.

    현재는 더미 로직으로 하드코딩:
        total_capacity 값에 관계없이 → 운동 40, 게스트 limit 4, 잔여석 4

    Args:
        total_capacity: 총 정원 (예: 48)
        special_count: 게스트 명단 중 (ob)/(교류전) 특수 인원 수

    Returns:
        {"운동": int, "게스트": {"limit": int, "special_count": int}, "잔여석": int}
    """
    return {
        "운동": 40,
        "게스트": {
            "limit": 4,
            "special_count": special_count,
        },
        "잔여석": 4,
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
        name_lower = entry["name"].lower()
        if "(ob)" in name_lower or "(교류전)" in name_lower:
            count += 1
    return count
