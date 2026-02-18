# scheduler_logic.py — 순수 시간 규칙 (외부 의존성 없음, datetime만 사용)
from datetime import datetime, timedelta
from enum import Enum


class Category(str, Enum):
    WED_REGULAR = "WED_REGULAR"    # 수요일 운동
    WED_GUEST = "WED_GUEST"        # 수요일 게스트
    WED_LEFTOVER = "WED_LEFTOVER"  # 수요일 잔여석
    WED_LESSON = "WED_LESSON"      # 수요일 레슨
    FRI_REGULAR = "FRI_REGULAR"    # 금요일 운동
    FRI_GUEST = "FRI_GUEST"        # 금요일 게스트
    FRI_LEFTOVER = "FRI_LEFTOVER"  # 금요일 잔여석


class Status(str, Enum):
    BEFORE_OPEN = "BEFORE_OPEN"    # 오픈 대기
    OPEN = "OPEN"                  # 신청/취소 가능
    CANCEL_ONLY = "CANCEL_ONLY"    # 취소만 가능
    CLOSED = "CLOSED"              # 마감


def _get_week_start(now: datetime) -> datetime:
    """현재 시각 기준으로 가장 최근 토요일 00:00:00을 반환한다.
    주차 사이클: 토 00:00 ~ 금 23:59:59
    Python weekday(): Mon=0 … Sat=5, Sun=6
    """
    days_since_saturday = (now.weekday() - 5) % 7
    return (now - timedelta(days=days_since_saturday)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )


def _get_transitions(category: str, week_start: datetime) -> list[tuple[datetime, str]]:
    """카테고리별 상태 전환 타임라인을 (시각, 상태) 리스트로 반환한다.
    week_start는 토요일 00:00:00이어야 한다.

    시간 규칙 (KST):
    토 00:00  ALL           -> BEFORE_OPEN
    토 22:00  수/금 운동     -> OPEN
    토 22:01  수/금 게스트    -> OPEN
    일 10:00  수/금 운동     -> CANCEL_ONLY
    일 22:00  수 레슨        -> OPEN
    일 22:01  수/금 잔여석    -> OPEN
    수 00:00  수 운동        -> CLOSED
    수 18:00  수 게스트/잔여/레슨 -> CLOSED
    금 00:00  금 운동        -> CLOSED
    금 17:00  금 게스트/잔여  -> CLOSED
    """
    sat = week_start
    # 모든 카테고리의 첫 전환: 토요일 00:00 -> BEFORE_OPEN
    transitions: list[tuple[datetime, str]] = [(sat, Status.BEFORE_OPEN)]

    if category == Category.WED_REGULAR:
        transitions.append((sat + timedelta(hours=22), Status.OPEN))
        transitions.append((sat + timedelta(days=1, hours=10), Status.CANCEL_ONLY))
        transitions.append((sat + timedelta(days=4), Status.CLOSED))

    elif category == Category.WED_GUEST:
        transitions.append((sat + timedelta(hours=22, minutes=1), Status.OPEN))
        transitions.append((sat + timedelta(days=4, hours=18), Status.CLOSED))

    elif category == Category.WED_LEFTOVER:
        transitions.append((sat + timedelta(days=1, hours=22, minutes=1), Status.OPEN))
        transitions.append((sat + timedelta(days=4, hours=18), Status.CLOSED))

    elif category == Category.WED_LESSON:
        transitions.append((sat + timedelta(days=1, hours=22), Status.OPEN))
        transitions.append((sat + timedelta(days=4, hours=18), Status.CLOSED))

    elif category == Category.FRI_REGULAR:
        transitions.append((sat + timedelta(hours=22), Status.OPEN))
        transitions.append((sat + timedelta(days=1, hours=10), Status.CANCEL_ONLY))
        transitions.append((sat + timedelta(days=6), Status.CLOSED))

    elif category == Category.FRI_GUEST:
        transitions.append((sat + timedelta(hours=22, minutes=1), Status.OPEN))
        transitions.append((sat + timedelta(days=6, hours=17), Status.CLOSED))

    elif category == Category.FRI_LEFTOVER:
        transitions.append((sat + timedelta(days=1, hours=22, minutes=1), Status.OPEN))
        transitions.append((sat + timedelta(days=6, hours=17), Status.CLOSED))

    return transitions


def get_current_status(category: str, now: datetime) -> str:
    """주어진 카테고리의 현재 상태를 반환한다.
    now는 KST 기준 datetime이어야 한다.
    """
    week_start = _get_week_start(now)
    transitions = _get_transitions(category, week_start)

    current_status = Status.CLOSED
    for transition_time, status in transitions:
        if now >= transition_time:
            current_status = status
        else:
            break

    return current_status


def get_next_change(category: str, now: datetime) -> tuple[datetime, str]:
    """다음 상태 전환 시각과 전환될 상태를 (datetime, status) 튜플로 반환한다.
    이번 주 남은 전환이 없으면 다음 주 토요일 BEFORE_OPEN을 반환한다.
    CLOSED 상태에서는 돌아오는 토요일 00:00을 반환하므로 카운트다운에 직접 사용 가능.
    """
    week_start = _get_week_start(now)
    transitions = _get_transitions(category, week_start)

    for transition_time, status in transitions:
        if now < transition_time:
            return transition_time, status

    # 이번 주 전환이 모두 지남(= CLOSED) → 다음 주 토요일 00:00
    return week_start + timedelta(days=7), Status.BEFORE_OPEN
