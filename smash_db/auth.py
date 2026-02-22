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

def verify_password(student_id: str, current_password: str) -> bool:
    """입력받은 현재 비밀번호 평문과 DB에 저장된 해시값을 비교하여 일치 여부를 반환한다.

    Args:
        student_id: 검증 대상 사용자의 학번.
        current_password: 사용자가 입력한 현재 비밀번호 평문.

    Returns:
        비밀번호가 일치하면 True, 사용자가 없거나 불일치하면 False.
    """
    conn = get_db_connection()
    user = conn.execute(
        'SELECT password FROM users WHERE student_id = ?', (student_id,)
    ).fetchone()
    conn.close()

    if user is None:
        return False

    return bcrypt.checkpw(
        current_password.encode('utf-8'),
        user['password'].encode('utf-8')
    )


def update_password(student_id: str, new_password: str) -> bool:
    """새 비밀번호를 bcrypt로 해시하여 DB의 해당 사용자 레코드를 갱신한다.

    기존 회원가입(init_db.py)과 동일한 알고리즘(bcrypt + gensalt)을 사용하며
    평문은 절대 저장하지 않는다.

    Args:
        student_id: 비밀번호를 변경할 사용자의 학번.
        new_password: 새 비밀번호 평문.

    Returns:
        실제로 레코드가 갱신되면 True, 해당 사용자가 없으면 False.
    """
    hashed_pw = bcrypt.hashpw(
        new_password.encode('utf-8'), bcrypt.gensalt()
    ).decode('utf-8')

    conn = get_db_connection()
    cursor = conn.execute(
        'UPDATE users SET password = ? WHERE student_id = ?',
        (hashed_pw, student_id)
    )
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()

    return updated


@auth_bp.route('/api/login', methods=['POST'])
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