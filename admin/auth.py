# admin/auth.py — 임원진 전용 권한 검증 데코레이터
from flask import request, jsonify, current_app
from functools import wraps
import jwt


def admin_required(f):
    """JWT 토큰 검증 + 임원진(manager) 권한 검증 데코레이터.

    1) Authorization 헤더에서 Bearer 토큰 추출 → 없으면 401
    2) JWT 디코딩 → 만료·무효 시 401
    3) 토큰의 role 필드가 'manager'인지 확인 → 아니면 403
    4) request.current_user에 사용자 정보 세팅 후 핸들러 진입
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': '토큰이 없습니다. 로그인이 필요합니다.'}), 401

        token = auth_header.split(' ')[1]

        try:
            payload = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                algorithms=["HS256"],
            )
        except jwt.ExpiredSignatureError:
            return jsonify({'error': '토큰이 만료되었습니다. 다시 로그인해주세요.'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': '유효하지 않은 토큰입니다.'}), 401

        # 임원진 여부 검증 (JWT payload의 role 필드)
        if payload.get('role') != 'manager':
            return jsonify({'error': '관리자 권한이 필요합니다.'}), 403

        request.current_user = {
            'id': payload['id'],
            'name': payload['name'],
            'role': payload['role'],
        }

        return f(*args, **kwargs)
    return decorated
