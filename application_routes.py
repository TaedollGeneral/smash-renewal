# application_routes.py — 운동 신청/취소/현황 API Blueprint
from flask import Blueprint, request, jsonify

from smash_db.auth import token_required
from time_control.scheduler_logic import Category, get_current_status
from time_control.time_handler import _now_kst
from time_control.rate_limiter import rate_limit
from time_control.apply import handle_apply
from time_control.cancel import handle_cancel
from time_control.admin import handle_admin_apply, handle_admin_cancel
from time_control.board_store import get_board, get_all_boards

application_bp = Blueprint('application', __name__)


def _validate_category(category: str | None) -> str | None:
    """유효한 카테고리인지 검증하여 오류 메시지를 반환한다. 유효하면 None."""
    if not category:
        return "category 파라미터가 필요합니다."
    try:
        Category(category)
    except ValueError:
        return f"유효하지 않은 카테고리입니다: {category}"
    return None


# ── 일반 신청/취소 (본인 전용) ────────────────────────────────────────────────

@application_bp.route('/api/apply', methods=['POST'])
@token_required
@rate_limit(max_requests=5, window_seconds=10)
def apply():
    """운동 신청 API (일반 회원 본인 신청 전용)

    handle_apply() 처리 순서:
      1) 타임스탬프 즉시 채번
      2) 시간 검증 (항상 수행, 바이패스 없음)
      3) 인메모리 조작 (board_store.apply_entry)

    매니저 대리 신청은 /admin/apply가 전담한다.
    """
    data = request.get_json() or {}
    category = data.get('category')

    error = _validate_category(category)
    if error:
        return jsonify({"error": error}), 400

    result, status_code = handle_apply(category)
    return jsonify(result), status_code


@application_bp.route('/api/cancel', methods=['POST'])
@token_required
@rate_limit(max_requests=5, window_seconds=10)
def cancel():
    """운동 취소 API (일반 회원 본인 취소 전용)

    handle_cancel() 처리 순서:
      1) 시간 검증 (항상 수행, 바이패스 없음)
      2) 취소 대상 결정
         - 일반 카테고리: 토큰 ID
         - 게스트 카테고리: guest_name 지정 시 정확 일치, 미지정 시 prefix 탐색
      3) 인메모리 조작 (board_store.remove_entry)

    요청 Body (선택):
      guest_name (str): 게스트 카테고리에서 취소할 특정 게스트 이름.

    매니저 대리 취소는 /admin/cancel이 전담한다.
    """
    data = request.get_json() or {}
    category = data.get('category')

    error = _validate_category(category)
    if error:
        return jsonify({"error": error}), 400

    result, status_code = handle_cancel(category)
    return jsonify(result), status_code


# ── 매니저 대리 신청/취소 ──────────────────────────────────────────────────────

@application_bp.route('/api/admin/apply', methods=['POST'])
@token_required
@rate_limit(max_requests=5, window_seconds=10)
def admin_apply():
    """매니저 대리 신청 API

    handle_admin_apply() 처리 순서:
      1) role == 'manager' 검증 (실패 시 즉시 403)
      2) 시간 검증 없음 (의도적 생략)
      3) target_user_id → DB 조회 → entry 구성
      4) 인메모리 조작 (board_store.apply_entry)
    """
    data = request.get_json() or {}
    category = data.get('category')

    error = _validate_category(category)
    if error:
        return jsonify({"error": error}), 400

    result, status_code = handle_admin_apply(category)
    return jsonify(result), status_code


@application_bp.route('/api/admin/cancel', methods=['POST'])
@token_required
@rate_limit(max_requests=5, window_seconds=10)
def admin_cancel():
    """매니저 대리 취소 API

    handle_admin_cancel() 처리 순서:
      1) role == 'manager' 검증 (실패 시 즉시 403)
      2) 시간 검증 없음 (의도적 생략)
      3) 정확 일치(일반 항목) → 실패 시 게스트 항목 탐색
         - target_guest_name 지정 시 정확 일치, 미지정 시 prefix 탐색
      4) 인메모리 조작 (board_store.remove_entry)

    요청 Body:
      target_user_id   (str, 필수): 취소 대상 회원 학번.
      target_guest_name (str, 선택): 게스트 항목 중 취소할 특정 게스트 이름.
    """
    data = request.get_json() or {}
    category = data.get('category')

    error = _validate_category(category)
    if error:
        return jsonify({"error": error}), 400

    result, status_code = handle_admin_cancel(category)
    return jsonify(result), status_code


# ── 현황 조회 ─────────────────────────────────────────────────────────────────

@application_bp.route('/api/board-data', methods=['GET'])
def get_status():
    """현황 조회 API — 현재 상태와 신청 목록 반환

    2초 폴링 대상 엔드포인트. 인메모리에서 즉시 응답한다.
    """
    category = request.args.get('category')

    error = _validate_category(category)
    if error:
        return jsonify({"error": error}), 400

    now = _now_kst()
    status = get_current_status(category, now)
    applications = get_board(category)

    # user_id(학번)는 공개 API에서 제외 — 이름/게스트명/타입/순번만 노출
    safe_applications = [
        {k: v for k, v in entry.items() if k != "user_id"}
        for entry in applications
    ]

    return jsonify({
        "status": status,
        "applications": safe_applications,
    }), 200


@application_bp.route('/api/all-boards', methods=['GET'])
def get_all_statuses():
    """전체 카테고리 현황 일괄 조회 API

    기존 /api/board-data 를 카테고리별로 7회 호출하던 것을 1회로 통합한다.
    인메모리에서 전체 스냅샷을 한 번에 반환하므로 Lock 획득도 1회로 줄어든다.

    Response (JSON):
        {
          "WED_REGULAR": { "status": "OPEN", "applications": [...] },
          "WED_GUEST":   { ... },
          ...
        }
    """
    now = _now_kst()
    all_data = get_all_boards()

    result = {}
    for cat_enum in Category:
        cat = cat_enum.value
        status = get_current_status(cat, now)
        applications = all_data.get(cat, [])

        safe_applications = [
            {k: v for k, v in entry.items() if k != "user_id"}
            for entry in applications
        ]

        result[cat] = {
            "status": status,
            "applications": safe_applications,
        }

    return jsonify(result), 200
