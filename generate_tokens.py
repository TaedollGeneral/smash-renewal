import sqlite3
import jwt
import datetime
import os
from app import app  # 서버의 진짜 설정을 그대로 가져옵니다!

DB_PATH = "smash_db/users.db"

print("1️⃣ DB에 테스트 유저 50명을 심는 중...")
conn = sqlite3.connect(DB_PATH)
for i in range(1, 51):
    user_id = f"test{i}"
    try:
        # DB에 진짜 유저 데이터 생성 (token_version = 1)
        conn.execute("INSERT INTO users (student_id, password, name, role, token_version) VALUES (?, ?, ?, ?, ?)",
                     (user_id, "dummy", f"테스터{i}", "user", 1))
    except sqlite3.OperationalError as e:
        print(f"DB 오류: {e}")
        break
    except sqlite3.IntegrityError:
        pass  # 이미 만들어진 유저면 패스

conn.commit()
conn.close()

print("2️⃣ 100% 진짜 토큰 발급 완료!\n")
print("TEST_TOKENS = [")
# Flask 앱의 찐 시크릿 키를 그대로 꺼내서 씁니다.
with app.app_context():
    secret = app.config['SECRET_KEY']
    for i in range(1, 51):
        token = jwt.encode({
            'id': f"test{i}",
            'name': f"테스터{i}",
            'role': 'user',
            'ver': 1,  # auth.py가 요구하는 필수 버전 정보
            'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)
        }, secret, algorithm="HS256")
        print(f'    "{token}",')
print("]")