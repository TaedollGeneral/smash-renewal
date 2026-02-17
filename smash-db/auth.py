# /home/ubuntu/smash-renewal/smash-db/auth.py
from flask import Blueprint, request, jsonify, current_app
import sqlite3
import bcrypt
import jwt
import datetime
import os

# 인증 전용 블루프린트 생성
auth_bp = Blueprint('auth', __name__)

# DB 파일 경로 (app.py 실행 위치 기준)
DB_PATH = os.path.join(os.getcwd(), 'smash-db', 'users.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
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
            # [수정] 토큰에 'name'을 포함하여 발급 (stateless 설계 반영)
            token = jwt.encode({
                'id': user['student_id'],
                'name': user['name'],
                'role': user['role'],
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
            }, current_app.config['SECRET_KEY'], algorithm="HS256")

            return jsonify({
                'message': '로그인 성공',
                'token': token,
                'user_name': user['name'],
                'role': user['role']
            }), 200

    return jsonify({'message': '아이디 또는 비밀번호가 올바르지 않습니다.'}), 401