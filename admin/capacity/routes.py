# admin/capacity/routes.py — 임원진 운동 정원 확정 API
from flask import Blueprint, request, jsonify
from admin.auth import admin_required
from admin.capacity.store import update_capacities, get_capacities
from time_control.scheduler_logic import Category
from admin.capacity.calculator import calculate_capacity_details, count_special_guests
import notifications.store
from notifications.store import set_wed_confirmed, set_fri_confirmed
from notifications.sender import enqueue_push_to_all

capacity_bp = Blueprint('admin_capacity', __name__)

# 요일별 알림 문구 (확정 메시지)
_CONFIRM_MESSAGES: dict[str, tuple[str, str]] = {
    "수": ("수요일 운동 알림",  "수요일 운동 정원이 확정되었습니다!"),
    "금": ("금요일 운동 알림",  "금요일 운동 정원이 확정되었습니다!"),
}


@capacity_bp.route('/api/admin/capacity', methods=['POST'])
@admin_required
def set_capacity():
    """임원진 운동 정원 확정 API

    Body: { "수"?: number, "금"?: number }
    - 수: 수요일 운동 정원
    - 금: 금요일 운동 정원

    메모리 + DB 동시 업데이트 (Write-Through).
    정원이 확정된 요일은 is_*_confirmed = True로 변경하고,
    push_subscriptions에 등록된 모든 사용자에게 푸시 알림을 큐잉한다.
    응답에 상세 포맷(details)을 포함하여 반환한다.
    """
    data = request.get_json()
    if data is None:
        return jsonify({'error': '요청 데이터가 없습니다.'}), 400

    # 만약을 대비해 확실하게 정수로 변환하여 업데이트 로직에 전달 (문자열 폭탄 방어)
    safe_data = {k: int(v) for k, v in data.items() if v is not None}
    update_capacities(safe_data)

    # ── 확정 상태 업데이트 + 전체 푸시 알림 트리거 ─────────────────────────────
    # enqueue_push_to_all()은 Non-blocking (큐에 추가만 하고 즉시 반환)
    # → HTTP 응답 지연 없음; 실제 발송은 push-worker 데몬 스레드에서 처리
    if "수" in safe_data:
        if not notifications.store.is_wed_confirmed:
            set_wed_confirmed(True)
            title, body = _CONFIRM_MESSAGES["수"]
            enqueue_push_to_all(title=title, body=body)

    if "금" in safe_data:
        if not notifications.store.is_fri_confirmed:
            set_fri_confirmed(True)
            title, body = _CONFIRM_MESSAGES["금"]
            enqueue_push_to_all(title=title, body=body)

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
                "details": calculate_capacity_details(day, total, special_count),
            }

    return jsonify({'message': '정원이 확정되었습니다.', 'capacities': capacities}), 200
