# notifications/routes.py — 푸시 알림 API 엔드포인트
#
# 보안 원칙:
#   - 모든 엔드포인트는 @token_required로 보호 (미인증 → 401)
#   - user_id는 반드시 JWT 페이로드(request.current_user)에서 추출
#     프론트에서 전달된 body의 user_id는 절대 사용하지 않는다
#
# 엔드포인트:
#   GET  /api/vapid-public-key         — VAPID 공개 키 반환 (인증 불필요)
#   POST /api/notifications/subscribe  — Push 구독 정보 저장 (SQLite Upsert)
#   POST /api/notifications/toggle     — 요일별 알림 On/Off (In-Memory + Rate Limit)
#   GET  /api/notifications/status     — 확정 상태 + 본인 알림 설정 조회

from flask import Blueprint, request, jsonify

from smash_db.auth import token_required
import notifications.store as _store   # 모듈 참조: 전역 변수 최신값을 항상 반영

notif_bp = Blueprint('notifications', __name__)


# ── GET /api/vapid-public-key ─────────────────────────────────────────────────

@notif_bp.route('/api/vapid-public-key', methods=['GET'])
def vapid_public_key():
    """VAPID 공개 키를 반환한다 (인증 불필요 — 공개 정보).

    프론트엔드가 PushManager.subscribe() 시 applicationServerKey로 사용한다.
    VAPID 공개 키는 암호학적으로 공개(public)이므로 인증 없이 노출해도 안전하다.

    Responses:
        200: { publicKey: string }  — VAPID_PUBLIC_KEY 환경변수 값 (미설정 시 빈 문자열)
    """
    import os
    key = os.environ.get('VAPID_PUBLIC_KEY', '')
    return jsonify({'publicKey': key}), 200


# ── POST /api/notifications/subscribe ────────────────────────────────────────

@notif_bp.route('/api/notifications/subscribe', methods=['POST'])
@token_required
def subscribe():
    """브라우저 WebPush Subscription 객체를 파싱해 DB에 저장한다 (Upsert).

    Request Headers:
        Authorization: Bearer <JWT>

    Request Body (JSON):
        subscription (object):
            endpoint (str): Push 서비스 URL
            keys (object):
                p256dh (str): 브라우저 공개 키 (Base64url)
                auth   (str): 인증 시크릿 (Base64url)

    Responses:
        200: 구독 저장 성공
        400: 필드 누락 또는 잘못된 형식
        401: 토큰 없음 / 만료
    """
    # [보안] JWT에서 추출한 user_id만 사용 — 요청 body의 user_id는 무시
    user_id = request.current_user['id']

    body = request.get_json(silent=True)
    if not body:
        return jsonify({'message': '요청 데이터가 없습니다.'}), 400

    sub = body.get('subscription')
    if not isinstance(sub, dict):
        return jsonify({'message': 'subscription 필드가 필요합니다.'}), 400

    endpoint = sub.get('endpoint')
    keys     = sub.get('keys') or {}
    p256dh   = keys.get('p256dh')
    auth     = keys.get('auth')

    if not endpoint or not p256dh or not auth:
        return jsonify({
            'message': '구독 정보가 올바르지 않습니다. (endpoint, p256dh, auth 필수)'
        }), 400

    # endpoint가 문자열인지, 길이 제한 초과 방지
    if not isinstance(endpoint, str) or len(endpoint) > 2048:
        return jsonify({'message': '잘못된 endpoint 형식입니다.'}), 400

    _store.save_subscription(user_id, endpoint, p256dh, auth)

    return jsonify({'message': '푸시 구독이 저장되었습니다.'}), 200


# ── POST /api/notifications/toggle ───────────────────────────────────────────

@notif_bp.route('/api/notifications/toggle', methods=['POST'])
@token_required
def toggle():
    """카테고리별 알림을 켜거나 끈다 (In-Memory 업데이트).

    Rate Limit: 동일 사용자가 60초 안에 10회 초과 요청 시 429 반환.
    전제 조건:  해당 요일의 정원이 확정된 상태(is_*_confirmed == True)여야 한다.
                확정 전(False)에는 설정 변경을 거부하여 알림 시스템의 일관성을 유지한다.

    Request Headers:
        Authorization: Bearer <JWT>

    Request Body (JSON):
        category (str):  NOTIF_CATEGORIES 중 하나 (예: "WED_REGULAR", "FRI_GUEST")
        enabled  (bool): true(알림 켜기) / false(알림 끄기)

    Responses:
        200: 설정 변경 성공  { message, category, enabled }
        400: 필드 누락 / 잘못된 형식
        401: 토큰 없음 / 만료
        409: 해당 요일 정원 미확정 (변경 거부)
        429: Rate limit 초과
    """
    user_id = request.current_user['id']

    # ① Rate limit 검사 (In-Memory, DB I/O 없음)
    if not _store.check_rate_limit(user_id, max_requests=10, window_seconds=60.0):
        return jsonify({'message': '잠시 후 다시 시도해주세요.'}), 429

    body = request.get_json(silent=True)
    if not body:
        return jsonify({'message': '요청 데이터가 없습니다.'}), 400

    category = body.get('category')
    enabled  = body.get('enabled')

    # ② 입력값 검증
    if category not in _store.NOTIF_CATEGORIES:
        return jsonify({'message': 'category 값이 올바르지 않습니다.'}), 400

    if not isinstance(enabled, bool):
        return jsonify({'message': 'enabled는 true 또는 false (boolean)이어야 합니다.'}), 400

    # ③ 요일별 확정 상태 검사 (모듈 참조로 최신값 읽기)
    #    정원이 확정되지 않은 상태(False)에서는 변경 거부
    is_wed    = category.startswith('WED_')
    confirmed = _store.is_wed_confirmed if is_wed else _store.is_fri_confirmed
    if not confirmed:
        day_label = '수요일' if is_wed else '금요일'
        return jsonify({
            'message': f'{day_label} 정원이 아직 확정되지 않았습니다. 확정 후 설정할 수 있습니다.'
        }), 409

    # ④ In-Memory 업데이트 (DB I/O 없음)
    _store.set_user_pref(user_id, category, enabled)

    action = '활성화' if enabled else '비활성화'
    return jsonify({
        'message':  f'알림이 {action}되었습니다.',
        'category': category,
        'enabled':  enabled,
    }), 200


# ── GET /api/notifications/status ────────────────────────────────────────────

@notif_bp.route('/api/notifications/status', methods=['GET'])
@token_required
def status():
    """수/금 정원 확정 상태와 본인의 알림 설정을 한 번에 반환한다.

    프론트엔드 초기 렌더링 시 1회 호출하여 UI 상태를 동기화하는 데 사용한다.
    모든 데이터를 In-Memory에서 읽으므로 DB I/O가 발생하지 않는다.

    Request Headers:
        Authorization: Bearer <JWT>

    Responses:
        200:
            wed_confirmed (bool): 수요일 정원 확정 여부
            fri_confirmed (bool): 금요일 정원 확정 여부
            prefs (object):
                wed (bool): 본인 수요일 알림 설정
                fri (bool): 본인 금요일 알림 설정
        401: 토큰 없음 / 만료
    """
    user_id = request.current_user['id']

    # 모든 값이 In-Memory — DB I/O 없음
    prefs = _store.get_user_prefs(user_id)

    return jsonify({
        'wed_confirmed': _store.is_wed_confirmed,
        'fri_confirmed': _store.is_fri_confirmed,
        'prefs':         prefs,   # {"wed": bool, "fri": bool}
    }), 200
