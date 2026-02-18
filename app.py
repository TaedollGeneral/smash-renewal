# /home/ubuntu/smash-renewal/app.py
import os
from flask import Flask
from smash_db.auth import auth_bp  # smash_db 폴더의 인증 로직 가져오기

app = Flask(__name__)

# [보안] 시크릿 키를 환경변수에서 읽음 (미설정 시 서버 시작 차단)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
if not app.config['SECRET_KEY']:
    raise RuntimeError("환경변수 SECRET_KEY가 설정되지 않았습니다. 서버를 시작할 수 없습니다.")

# --- [모듈 등록 구역] ---
# 앞으로 기능이 추가될 때마다 아래에 register_blueprint를 추가하면 됩니다.
app.register_blueprint(auth_bp)

from time_control.time_handler import time_bp  # 시간 상태 폴링 API
app.register_blueprint(time_bp)

from application_routes import application_bp  # 운동 신청/취소/현황 API
app.register_blueprint(application_bp)

if __name__ == '__main__':
    # 127.0.0.1로 설정하여 Nginx를 통해서만 접근 가능하도록 제한
    app.run(host='127.0.0.1', port=5000)
