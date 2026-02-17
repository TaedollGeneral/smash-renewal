# /home/ubuntu/smash-renewal/app.py
from flask import Flask
from smash_db.auth import auth_bp  # smash-db 폴더의 인증 로직 가져오기

app = Flask(__name__)

# [보안] 시크릿 키는 메인에서 관리
app.config['SECRET_KEY'] = 'taedol_secret_key_1234'

# --- [모듈 등록 구역] ---
# 앞으로 기능이 추가될 때마다 아래에 register_blueprint를 추가하면 됩니다.
app.register_blueprint(auth_bp) 

if __name__ == '__main__':
    # 0.0.0.0으로 설정하여 외부 접속 허용
    app.run(host='0.0.0.0', port=5000)