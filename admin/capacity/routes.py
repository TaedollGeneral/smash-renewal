# admin/capacity/routes.py — 임원진 운동 정원 확정 API
from flask import Blueprint, request, jsonify
from admin.auth import admin_required

capacity_bp = Blueprint('admin_capacity', __name__)


@capacity_bp.route('/api/admin/capacity', methods=['POST'])
@admin_required
def set_capacity():
    """임원진 운동 정원 확정 API

    Body: { "수"?: number, "금"?: number }
    - 수: 수요일 운동 정원
    - 금: 금요일 운동 정원
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': '요청 데이터가 없습니다.'}), 400

    # TODO: 3단계에서 DB 저장 로직 구현
    return jsonify({'message': '정원이 확정되었습니다.', 'capacities': data}), 200
