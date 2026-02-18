# time_handler.py — 시간 상태 게이트키퍼 (Gatekeeper)
#
# 역할 1 (Query):  프론트엔드 폴링 요청(카테고리 상태 / 카운트다운)에 응답.
#                  네트워크 딜레이를 고려해 절대 마감 타임스탬프(Unix ms)를 반환.
#
# 역할 2 (Command Validation): Apply/Cancel 요청 시 scheduler_logic으로
#                  현재 시각이 유효한 윈도우인지 검증(Guard Clause)한 뒤
#                  하위 apply/ · cancel/ 모듈로 라우팅.
from datetime import datetime, timezone, timedelta

from flask import Blueprint, request, jsonify

from .scheduler_logic import (
    Category,
    Status,
    get_current_status,
    get_next_change,
)

time_bp = Blueprint("time", __name__)

KST = timezone(timedelta(hours=9))


# ── 내부 유틸 ──────────────────────────────────────────────────────────────────

def _now_kst() -> datetime:
    """현재 KST 시각을 반환한다."""
    return datetime.now(KST)


# ── 매핑 테이블 ────────────────────────────────────────────────────────────────

# 백엔드 Status → (프론트엔드 StatusType, statusText)
# StatusType 명세: 'before-open' | 'open' | 'cancel-period' | 'waiting'
# statusText 명세: '오픈까지' | '신청 마감까지' | '취소 마감까지' | '종료'
_STATUS_MAP: dict[str, tuple[str, str]] = {
    Status.BEFORE_OPEN: ("before-open",   "오픈까지"),
    Status.OPEN:        ("open",          "신청 마감까지"),
    Status.CANCEL_ONLY: ("cancel-period", "취소 마감까지"),
    Status.CLOSED:      ("waiting",       "종료"),
}

# 백엔드 Category → (프론트엔드 DayType, BoardType)
# DayType  = '수' | '금'
# BoardType = '운동' | '게스트' | '잔여석' | '레슨'
_CATEGORY_MAP: list[tuple[str, str, str]] = [
    (Category.WED_REGULAR,  "수", "운동"),
    (Category.WED_GUEST,    "수", "게스트"),
    (Category.WED_LEFTOVER, "수", "잔여석"),
    (Category.WED_LESSON,   "수", "레슨"),
    (Category.FRI_REGULAR,  "금", "운동"),
    (Category.FRI_GUEST,    "금", "게스트"),
    (Category.FRI_LEFTOVER, "금", "잔여석"),
]


# ── 역할 1: Query — 프론트엔드 폴링 응답 ──────────────────────────────────────

@time_bp.route("/api/category-states", methods=["GET"])
def get_category_states():
    """카테고리별 현재 상태와 마감 타임스탬프를 반환한다.

    Query params (무시되지 않음 — 추후 DB 연동 시 주차 필터링에 사용):
        semester: str   예) "1"
        week:     str   예) "3"

    Response (JSON):
        {
          "수": {
            "운동":   { "status": "open",    "statusText": "신청 마감까지", "deadlineTimestamp": 1234567890000 },
            "게스트": { ... },
            "잔여석": { ... },
            "레슨":   { ... }
          },
          "금": {
            "운동":   { ... },
            "게스트": { ... },
            "잔여석": { ... }
          }
        }

    deadlineTimestamp 규칙:
        - CLOSED 상태: 돌아오는 토요일 00:00 KST (Unix ms)
          → get_next_change()가 이미 이 값을 반환하므로 별도 분기 없음.
        - 그 외 상태: 다음 상태 전환 시각 (Unix ms)
    """
    now = _now_kst()

    result: dict = {"수": {}, "금": {}}

    for category, day, board in _CATEGORY_MAP:
        status = get_current_status(category, now)
        next_time, _ = get_next_change(category, now)

        # Unix ms 타임스탬프 (절대 시각) — 프론트엔드에서 Date.now()와 비교해 카운트다운 계산
        deadline_ms = int(next_time.timestamp() * 1000)

        frontend_status, status_text = _STATUS_MAP[status]

        result[day][board] = {
            "status":            frontend_status,
            "statusText":        status_text,
            "deadlineTimestamp": deadline_ms,
        }

    return jsonify(result), 200


@time_bp.route("/api/capacities", methods=["GET"])
def get_capacities():
    """운동 정원을 반환한다.

    Query params (추후 DB 연동 시 주차별 정원 조회에 사용):
        semester: str
        week:     str

    Response (JSON):
        { "수": number, "금": number }

    TODO: DB에서 임원진이 설정한 해당 주차 정원을 조회하도록 교체.
    """
    # TODO: semester/week 파라미터로 DB 조회
    # semester = request.args.get("semester", "1")
    # week     = request.args.get("week", "1")
    return jsonify({"수": 12, "금": 14}), 200


# ── 역할 2: Command Validation — Guard Clause ──────────────────────────────────
# 아래 함수들은 apply/ · cancel/ 하위 모듈에서 import하여 사용한다.

def validate_apply_time(category: str, now: datetime) -> str | None:
    """신청 가능한 시간(OPEN)인지 검증한다.

    Returns:
        None  — 검증 통과 (신청 가능)
        str   — 오류 메시지 (신청 불가 이유)
    """
    status = get_current_status(category, now)
    if status == Status.OPEN:
        return None

    messages: dict[str, str] = {
        Status.BEFORE_OPEN: "아직 신청이 오픈되지 않았습니다.",
        Status.CANCEL_ONLY: "신청 마감 후 취소만 가능한 시간입니다.",
        Status.CLOSED:      "신청이 마감되었습니다.",
    }
    return messages.get(status, "신청 가능한 시간이 아닙니다.")


def validate_cancel_time(category: str, now: datetime) -> str | None:
    """취소 가능한 시간(OPEN 또는 CANCEL_ONLY)인지 검증한다.

    Returns:
        None  — 검증 통과 (취소 가능)
        str   — 오류 메시지 (취소 불가 이유)
    """
    status = get_current_status(category, now)
    if status in (Status.OPEN, Status.CANCEL_ONLY):
        return None

    messages: dict[str, str] = {
        Status.BEFORE_OPEN: "아직 신청이 오픈되지 않았습니다.",
        Status.CLOSED:      "취소 기간이 종료되었습니다.",
    }
    return messages.get(status, "취소 가능한 시간이 아닙니다.")
