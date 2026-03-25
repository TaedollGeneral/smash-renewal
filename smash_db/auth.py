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

# 로그인 브루트포스 방지용 rate limiter (auth 전용, IP 기반)
from time_control.rate_limiter import rate_limit

# ── bcrypt CPU 세마포어 ───────────────────────────────────────────────────────
# bcrypt는 CPU-intensive 연산(~300ms)이므로 동시 실행 수를 제한하여
# 피크타임에 모든 스레드가 bcrypt에 점유당하는 것을 방지한다.
# BCRYPT_SEMAPHORE=2 (c6i.xlarge 피크), =1 (t3.small 평시) — configure.sh가 설정
import threading as _threading
_bcrypt_sem = _threading.Semaphore(int(os.environ.get("BCRYPT_SEMAPHORE", "1")))

# DB 파일 경로 (__file__ 기준 상대 경로로 안정적으로 해석)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'users.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)  # Gunicorn timeout(30s)보다 낮게: lock 시 JSON 500 반환 보장
    conn.row_factory = sqlite3.Row
    return conn


def migrate_token_version_column():
    """users 테이블에 token_version 컬럼이 없으면 추가한다.

    서버 시작 시 1회 호출 (app.py). 이미 존재하면 아무 일도 하지 않는다.
    DEFAULT 1로 추가하므로 기존 회원 모두 버전 1을 갖게 된다.
    """
    conn = get_db_connection()
    try:
        conn.execute(
            "ALTER TABLE users ADD COLUMN token_version INTEGER NOT NULL DEFAULT 1"
        )
        conn.commit()
    except sqlite3.OperationalError:
        pass  # 이미 컬럼이 존재하는 경우 — 정상
    finally:
        conn.close()


def _get_token_version(student_id: str) -> int | None:
    """DB에서 해당 사용자의 현재 token_version을 반환한다."""
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT token_version FROM users WHERE student_id = ?", (student_id,)
        ).fetchone()
        return row["token_version"] if row else None
    finally:
        conn.close()


def token_required(f):
    """JWT 토큰 검증 데코레이터 — 보호가 필요한 라우트에 @token_required를 붙여서 사용.

    검증 순서:
      1) Authorization 헤더에서 Bearer 토큰 추출
      2) JWT 서명·만료 검증
      3) 토큰의 ver(token_version)과 DB의 현재 token_version 비교
         → 불일치 시 비밀번호 변경 등으로 무효화된 토큰으로 간주하고 401 반환
    """
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
        except jwt.ExpiredSignatureError:
            return jsonify({'message': '토큰이 만료되었습니다. 다시 로그인해주세요.'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': '유효하지 않은 토큰입니다.'}), 401

        # 토큰 버전 검증: 비밀번호 변경 후 구 토큰 즉시 차단
        user_id = payload.get('id')
        current_ver = _get_token_version(user_id)
        if current_ver is None:
            return jsonify({'message': '세션이 만료되었습니다. 다시 로그인해주세요.'}), 401

        token_ver = payload.get('ver')
        if token_ver is None:
            # ver 필드 없는 구 토큰: 아직 비밀번호 변경이 없는 경우(token_version=1)만 허용
            if current_ver != 1:
                return jsonify({'message': '세션이 만료되었습니다. 다시 로그인해주세요.'}), 401
        elif token_ver != current_ver:
            return jsonify({'message': '세션이 만료되었습니다. 다시 로그인해주세요.'}), 401

        request.current_user = {
            'id': payload['id'],
            'name': payload['name'],
            'role': payload['role']
        }

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

    with _bcrypt_sem:
        return bcrypt.checkpw(
            current_password.encode('utf-8'),
            user['password'].encode('utf-8')
        )


def _validate_password(password: str) -> str | None:
    """비밀번호 정책 검증. 위반 시 오류 메시지를 반환, 통과 시 None."""
    if len(password) < 8:
        return '새 비밀번호는 8자 이상이어야 합니다.'
    if len(password) > 72:
        return '비밀번호는 72자 이하여야 합니다.'  # bcrypt 제한
    has_letter = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)
    if not (has_letter and has_digit):
        return '비밀번호는 영문자와 숫자를 모두 포함해야 합니다.'
    return None


def update_password(student_id: str, new_password: str) -> bool:
    """새 비밀번호를 bcrypt로 해시하여 DB를 갱신하고, token_version을 +1 증가시킨다.

    token_version 증가로 기존에 발급된 모든 JWT(다른 기기 포함)가 즉시 무효화된다.
    """
    with _bcrypt_sem:
        hashed_pw = bcrypt.hashpw(
            new_password.encode('utf-8'), bcrypt.gensalt()
        ).decode('utf-8')

    conn = get_db_connection()
    cursor = conn.execute(
        'UPDATE users SET password = ?, token_version = token_version + 1 WHERE student_id = ?',
        (hashed_pw, student_id)
    )
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()

    return updated


@auth_bp.route('/api/login', methods=['POST'])
@rate_limit(max_requests=5, window_seconds=30)
def login():
    data = request.get_json()
    if not data:
        return jsonify({'message': '요청 데이터가 없습니다.'}), 400

    user_id = data.get('id')
    user_pw = data.get('password')

    if not user_id or not user_pw:
        return jsonify({'message': '아이디와 비밀번호를 입력해주세요.'}), 400

    # [보안] 입력 길이 제한 — 비정상적으로 긴 문자열로 인한 CPU 낭비 방지
    if len(user_id) > 50 or len(user_pw) > 72:
        return jsonify({'message': '아이디 또는 비밀번호가 올바르지 않습니다.'}), 401

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE student_id = ?', (user_id,)).fetchone()

    if user:
        with _bcrypt_sem:
            pw_match = bcrypt.checkpw(user_pw.encode('utf-8'), user['password'].encode('utf-8'))
        if pw_match:
            # 새 로그인 시 token_version 증가 → 기존 기기의 토큰 즉시 무효화 (중복 로그인 방지)
            conn.execute(
                'UPDATE users SET token_version = token_version + 1 WHERE student_id = ?',
                (user['student_id'],)
            )
            conn.commit()
            new_version = conn.execute(
                'SELECT token_version FROM users WHERE student_id = ?', (user['student_id'],)
            ).fetchone()['token_version']
            token = jwt.encode({
                'id': user['student_id'],
                'name': user['name'],
                'role': user['role'],
                'ver': new_version,  # 토큰 버전: 로그인/비밀번호 변경 시 무효화에 사용
                'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=2880)  # 4개월
            }, current_app.config['SECRET_KEY'], algorithm="HS256")

            conn.close()
            return jsonify({
                'message': '로그인 성공',
                'token': token,
                'user_id': user['student_id'],
                'user_name': user['name'],
                'role': user['role']
            }), 200

    conn.close()
    return jsonify({'message': '아이디 또는 비밀번호가 올바르지 않습니다.'}), 401

@auth_bp.route('/api/force-reset-password', methods=['POST'])
@token_required
@rate_limit(max_requests=5, window_seconds=60)
def force_reset_password():
    """매니저 전용: 대상 회원의 비밀번호를 강제로 변경한다.

    현재 비밀번호 검증 대신 요청자의 role이 'manager'인지 확인한다.
    비밀번호 변경 후 대상 회원의 token_version이 증가하여
    해당 회원의 모든 기존 토큰이 즉시 무효화된다.

    Request Headers:
        Authorization: Bearer <JWT>  (manager 권한 필요)

    Request Body (JSON):
        target_id    (str): 비밀번호를 변경할 대상 회원의 학번
        new_password (str): 설정할 새 비밀번호 평문

    Responses:
        200: 비밀번호 변경 성공
        400: 필수 필드 누락 / 유효성 검사 실패
        403: 매니저 권한이 아닌 경우
        404: 대상 회원이 존재하지 않는 경우
        500: DB 갱신 실패
    """
    # 매니저 권한 검증
    if request.current_user.get('role') != 'manager':
        return jsonify({'message': '임원진만 사용할 수 있는 기능입니다.'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'message': '요청 데이터가 없습니다.'}), 400

    target_id = data.get('target_id')
    new_password = data.get('new_password')

    if not target_id or not new_password:
        return jsonify({'message': 'target_id와 new_password를 모두 입력해주세요.'}), 400

    pw_error = _validate_password(new_password)
    if pw_error:
        return jsonify({'message': pw_error}), 400

    # 대상 회원 존재 여부 확인
    conn = get_db_connection()
    target_user = conn.execute(
        'SELECT student_id FROM users WHERE student_id = ?', (target_id,)
    ).fetchone()
    conn.close()

    if target_user is None:
        return jsonify({'message': '해당 회원을 찾을 수 없습니다.'}), 404

    # update_password 재사용: 해시 갱신 + token_version 증가 (기존 토큰 즉시 무효화)
    if not update_password(target_id, new_password):
        return jsonify({'message': '비밀번호 변경에 실패했습니다.'}), 500

    return jsonify({'message': f'{target_id} 회원의 비밀번호가 성공적으로 변경되었습니다.'}), 200


@auth_bp.route('/api/change-password', methods=['POST'])
@token_required
@rate_limit(max_requests=3, window_seconds=60)
def change_password():
    """현재 비밀번호 검증 후 새 비밀번호로 갱신한다.

    Request Headers:
        Authorization: Bearer <JWT>

    Request Body (JSON):
        current_password (str): 현재 비밀번호 평문
        new_password     (str): 변경할 새 비밀번호 평문

    Responses:
        200: 비밀번호 변경 성공
        400: 필수 필드 누락
        401: 현재 비밀번호 불일치
        500: DB 갱신 실패 (예: 사용자 레코드 없음)
    """
    data = request.get_json()
    if not data:
        return jsonify({'message': '요청 데이터가 없습니다.'}), 400

    current_password = data.get('current_password')
    new_password = data.get('new_password')

    if not current_password or not new_password:
        return jsonify({'message': 'current_password와 new_password를 모두 입력해주세요.'}), 400

    pw_error = _validate_password(new_password)
    if pw_error:
        return jsonify({'message': pw_error}), 400

    student_id = request.current_user['id']

    if not verify_password(student_id, current_password):
        return jsonify({'message': '현재 비밀번호가 올바르지 않습니다.'}), 401

    if not update_password(student_id, new_password):
        return jsonify({'message': '비밀번호 변경에 실패했습니다.'}), 500

    return jsonify({'message': '비밀번호가 성공적으로 변경되었습니다.'}), 200


# 사용 예시: 보호된 라우트
# @auth_bp.route('/api/protected', methods=['GET'])
# @token_required
# def protected_route():
#     user = request.current_user  # {'id': '...', 'name': '...', 'role': '...'}
#     return jsonify({'message': f'{user["name"]}님, 인증된 요청입니다.'})