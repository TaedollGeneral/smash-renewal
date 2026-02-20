# application_routes.py — 운동 신청/취소/현황 API Blueprint
from flask import Blueprint, request, jsonify

from smash_db.auth import token_required
from time_control.scheduler_logic import Category, get_current_status
from time_control.time_handler import _now_kst
from time_control.rate_limiter import rate_limit
from time_control.apply import handle_apply
from time_control.cancel import handle_cancel
from time_control.board_store import get_board

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


@application_bp.route('/apply', methods=['POST'])
@token_required
@rate_limit(max_requests=5, window_seconds=10)
def apply():
    """운동 신청 API

    데코레이터 실행 순서:
      1) token_required — JWT 검증 + request.current_user 설정
      2) rate_limit     — User ID 기반 요청 횟수 제한 (매크로/도배 방지)

    이후 handle_apply()가 다음을 순서대로 수행:
      1) 타임스탬프 즉시 채번 (time.time())
      2) role 확인 → manager/user 분기
      3) 동시성 제어 + 인메모리 조작 (board_store.apply_entry)
      4) 응답 반환
    """
    data = request.get_json() or {}
    category = data.get('category')

    error = _validate_category(category)
    if error:
        return jsonify({"error": error}), 400

    result, status_code = handle_apply(category)
    return jsonify(result), status_code


@application_bp.route('/cancel', methods=['POST'])
@token_required
@rate_limit(max_requests=5, window_seconds=10)
def cancel():
    """운동 취소 API

    데코레이터 실행 순서:
      1) token_required — JWT 검증 + request.current_user 설정
      2) rate_limit     — User ID 기반 요청 횟수 제한 (매크로/도배 방지)

    이후 handle_cancel()이 다음을 순서대로 수행:
      1) role 확인 → manager/user 분기
      2) 시간 검증 (user만) + 본인 인가 검증
      3) 동시성 제어 + 인메모리 조작 (board_store.remove_entry)
      4) 응답 반환
    """
    data = request.get_json() or {}
    category = data.get('category')

    error = _validate_category(category)
    if error:
        return jsonify({"error": error}), 400

    result, status_code = handle_cancel(category)
    return jsonify(result), status_code


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

    # 인메모리 board_store에서 현황 조회
    applications = get_board(category)

    return jsonify({
        "status": status,
        "applications": applications,
    }), 200
