# apply/ — 운동 신청 핵심 로직
#
# 요청 처리 순서 (반드시 이 순서를 지켜야 한다):
#   1. 타임스탬프 즉시 채번 (time.time(), 소수 둘째 자리)
#   2. JWT 토큰 검증 + Role 확인 (token_required 데코레이터)
#   3. 권한별 분기 (Manager: 시간 검증 건너뜀, User: 시간 검증 수행)
#   4. 동시성 제어: board_store.apply_entry() 원자적 조작
#   5. 응답 반환

import html
import sqlite3
import time
import os

from flask import request, jsonify

from ..board_store import apply_entry
from ..time_handler import validate_apply_time, _now_kst

# ── 회원 검증 (Manager 대리 신청 시) ─────────────────────────────────────────

_DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "smash_db", "users.db"
)


def _validate_member(student_id: str) -> dict | None:
    """users.db에서 회원 존재 여부를 확인한다.

    Returns:
        {"student_id": str, "name": str} — 유효한 회원
        None — 존재하지 않는 회원
    """
    try:
        conn = sqlite3.connect(_DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT student_id, name FROM users WHERE student_id = ?",
            (student_id,),
        ).fetchone()
        conn.close()
        if row:
            return {"student_id": row["student_id"], "name": row["name"]}
    except sqlite3.Error:
        pass
    return None


# ── 입력 세니타이즈 ──────────────────────────────────────────────────────────

def _sanitize_name(name: str) -> str:
    """게스트 이름의 XSS 특수문자를 이스케이프한다."""
    return html.escape(name, quote=True)


# ── 카테고리 타입 판별 ───────────────────────────────────────────────────────

_GUEST_CATEGORIES = {"WED_GUEST", "FRI_GUEST"}


def _is_guest_category(category: str) -> bool:
    return category in _GUEST_CATEGORIES


# ── 핵심 로직 ────────────────────────────────────────────────────────────────

def handle_apply(category: str) -> tuple[dict, int]:
    """운동 신청 요청을 처리한다.

    이 함수는 application_routes.py의 /apply 엔드포인트에서 호출된다.
    호출 전에 다음이 보장되어야 한다:
      - category는 유효한 Category enum 값
      - request.current_user가 설정됨 (token_required 통과)
      - timestamp가 이미 채번됨 (인자로 전달)

    Args:
        category: 유효한 Category enum 값

    Returns:
        (response_dict, status_code)
    """
    # ── Step 1: 타임스탬프 즉시 채번 (최우선) ─────────────────────────────────
    ts = round(time.time(), 2)

    # ── Step 2: 토큰 정보 추출 ────────────────────────────────────────────────
    user = request.current_user  # token_required가 보장
    role = user["role"]
    user_id = user["id"]
    user_name = user["name"]

    data = request.get_json() or {}

    # ── Step 3: 권한별 분기 ───────────────────────────────────────────────────
    if role == "manager":
        # Manager: 시간 검증 건너뜀 (Bypass)
        target_user_id = data.get("target_user_id")
        target_name = data.get("target_name")

        if not target_user_id or not target_name:
            return {"error": "대리 신청 시 target_user_id와 target_name이 필요합니다."}, 400

        # 유효한 회원인지 대조
        member = _validate_member(target_user_id)
        if not member:
            return {"error": f"존재하지 않는 회원입니다: {target_user_id}"}, 404

        # DB의 실제 이름 사용 (조작 방지)
        apply_user_id = member["student_id"]
        apply_name = member["name"]
        apply_type = "member"

    else:
        # 일반 회원/게스트: 시간 검증 수행
        now = _now_kst()
        time_error = validate_apply_time(category, now)
        if time_error:
            return {"error": time_error}, 400

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
            # 일반 회원 본인 신청
            apply_user_id = user_id
            apply_name = user_name
            apply_type = "member"

    # ── Step 4: 동시성 제어 + 인메모리 조작 ───────────────────────────────────
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

    # ── Step 5: 응답 반환 ─────────────────────────────────────────────────────
    return {"message": "신청이 완료되었습니다."}, 200
