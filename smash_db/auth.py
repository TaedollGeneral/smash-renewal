# /home/ubuntu/smash-renewal/smash_db/auth.py
from flask import Blueprint, request, jsonify, current_app
from functools import wraps
import sqlite3
import bcrypt
import jwt
import datetime
import os

# 인증 전용 블루프린트 생성
auth_bp = Blueprint('auth', __name__)

# DB 파일 경로 (__file__ 기준 상대 경로로 안정적으로 해석)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'users.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def token_required(f):
    """JWT 토큰 검증 데코레이터 — 보호가 필요한 라우트에 @token_required를 붙여서 사용"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]

        if not token:
            return jsonify({'message': '토큰이 없습니다. 로그인이 필요합니다.'}), 401

        try:
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            request.current_user = {
                'id': payload['id'],
                'name': payload['name'],
                'role': payload['role']
            }
        except jwt.ExpiredSignatureError:
            return jsonify({'message': '토큰이 만료되었습니다. 다시 로그인해주세요.'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': '유효하지 않은 토큰입니다.'}), 401

        return f(*args, **kwargs)
    return decorated

@auth_bp.route('api/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({'message': '요청 데이터가 없습니다.'}), 400

    user_id = data.get('id')
    user_pw = data.get('password')

    if not user_id or not user_pw:
        return jsonify({'message': '아이디와 비밀번호를 입력해주세요.'}), 400

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE student_id = ?', (user_id,)).fetchone()
    conn.close()

    if user:
        # 비밀번호 검증
        if bcrypt.checkpw(user_pw.encode('utf-8'), user['password'].encode('utf-8')):
            token = jwt.encode({
                'id': user['student_id'],
                'name': user['name'],
                'role': user['role'],
                'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)
            }, current_app.config['SECRET_KEY'], algorithm="HS256")

            return jsonify({
                'message': '로그인 성공',
                'token': token,
                'user_id': user['student_id'],
                'user_name': user['name'],
                'role': user['role']
            }), 200

    return jsonify({'message': '아이디 또는 비밀번호가 올바르지 않습니다.'}), 401

# 사용 예시: 보호된 라우트
# @auth_bp.route('/api/protected', methods=['GET'])
# @token_required
# def protected_route():
#     user = request.current_user  # {'id': '...', 'name': '...', 'role': '...'}
#     return jsonify({'message': f'{user["name"]}님, 인증된 요청입니다.'})
