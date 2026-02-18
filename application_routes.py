# application_routes.py — 운동 신청/취소/현황 API Blueprint
from flask import Blueprint, request, jsonify
from time_control.scheduler_logic import Category, get_current_status
from time_control.time_handler import (
    _now_kst,
    validate_apply_time,
    validate_cancel_time,
)

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
def apply():
    """운동 신청 API — OPEN 상태에서만 신청 가능"""
    data = request.get_json() or {}
    category = data.get('category')

    error = _validate_category(category)
    if error:
        return jsonify({"error": error}), 400

    # Guard Clause: time_handler에서 시간 규칙 검증
    now = _now_kst()
    time_error = validate_apply_time(category, now)
    if time_error:
        return jsonify({"error": time_error}), 400

    # TODO: DB에 신청 데이터 저장
    # user = request.current_user  (token_required 데코레이터 사용 시)
    # db.insert_application(user['id'], category, now)

    return jsonify({"message": "신청이 완료되었습니다."}), 200


@application_bp.route('/cancel', methods=['POST'])
def cancel():
    """운동 취소 API — OPEN 또는 CANCEL_ONLY 상태에서만 취소 가능"""
    data = request.get_json() or {}
    category = data.get('category')

    error = _validate_category(category)
    if error:
        return jsonify({"error": error}), 400

    # Guard Clause: time_handler에서 시간 규칙 검증
    now = _now_kst()
    time_error = validate_cancel_time(category, now)
    if time_error:
        return jsonify({"error": time_error}), 400

    # TODO: DB에서 신청 데이터 삭제
    # user = request.current_user
    # db.delete_application(user['id'], category)

    return jsonify({"message": "취소가 완료되었습니다."}), 200


@application_bp.route('/api/board-data', methods=['GET'])
def get_status():
    """현황 조회 API — 현재 상태와 신청 목록 반환"""
    category = request.args.get('category')

    error = _validate_category(category)
    if error:
        return jsonify({"error": error}), 400

    now = _now_kst()
    status = get_current_status(category, now)

    # TODO: DB에서 현황 데이터 조회
    # applications = db.get_applications(category)

    return jsonify({
        "status": status,
        "applications": [],  # TODO: DB 연동 후 실제 데이터로 교체
    }), 200
