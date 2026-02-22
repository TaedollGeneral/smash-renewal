# admin/capacity/routes.py — 임원진 운동 정원 확정 API
from flask import Blueprint, request, jsonify
from admin.auth import admin_required
from admin.capacity.store import update_capacities, get_capacities
from time_control.scheduler_logic import Category
from admin.capacity.calculator import calculate_capacity_details, count_special_guests

capacity_bp = Blueprint('admin_capacity', __name__)


@capacity_bp.route('/api/admin/capacity', methods=['POST'])
@admin_required
def set_capacity():
    """임원진 운동 정원 확정 API

    Body: { "수"?: number, "금"?: number }
    - 수: 수요일 운동 정원
    - 금: 금요일 운동 정원

    메모리 + DB 동시 업데이트 (Write-Through).
    응답에 상세 포맷(details)을 포함하여 반환한다.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': '요청 데이터가 없습니다.'}), 400

    update_capacities(data)

    raw = get_capacities()
    guest_category_map = {"수": Category.WED_GUEST, "금": Category.FRI_GUEST}

    capacities = {}
    for day, total in raw.items():
        if total is None:
            capacities[day] = None
        else:
            special_count = count_special_guests(guest_category_map[day])
            capacities[day] = {
                "total": total,
                "details": calculate_capacity_details(total, special_count),
            }

    return jsonify({'message': '정원이 확정되었습니다.', 'capacities': capacities}), 200
