# admin/capacity/routes.py — 임원진 운동 정원 확정 API
from flask import Blueprint, request, jsonify
from admin.auth import admin_required
from admin.capacity.store import update_capacities, get_capacities

capacity_bp = Blueprint('admin_capacity', __name__)


@capacity_bp.route('/api/admin/capacity', methods=['POST'])
@admin_required
def set_capacity():
    """임원진 운동 정원 확정 API

    Body: { "수"?: number, "금"?: number }
    - 수: 수요일 운동 정원
    - 금: 금요일 운동 정원

    메모리 + DB 동시 업데이트 (Write-Through).
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': '요청 데이터가 없습니다.'}), 400

    update_capacities(data)
    return jsonify({'message': '정원이 확정되었습니다.', 'capacities': get_capacities()}), 200
