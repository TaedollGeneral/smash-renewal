# /home/ubuntu/smash-renewal/app.py
import os
from flask import Flask

from dotenv import load_dotenv   # 👈 1. 추가
load_dotenv()                    # 👈 2. 추가 (.env 파일을 OS 환경변수로 싹 밀어넣음)

from smash_db.auth import auth_bp

app = Flask(__name__)

# 이제 os.environ.get이 .env 파일 안의 값을 정상적으로 찾아냅니다!
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
if not app.config['SECRET_KEY']:
    raise RuntimeError("환경변수 SECRET_KEY가 설정되지 않았습니다. 서버를 시작할 수 없습니다.")
from smash_db.auth import auth_bp  # smash_db 폴더의 인증 로직 가져오기

app = Flask(__name__)

# [보안] 시크릿 키를 환경변수에서 읽음 (미설정 시 서버 시작 차단)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
if not app.config['SECRET_KEY']:
    raise RuntimeError("환경변수 SECRET_KEY가 설정되지 않았습니다. 서버를 시작할 수 없습니다.")

# --- [모듈 등록 구역] ---
# 앞으로 기능이 추가될 때마다 아래에 register_blueprint를 추가하면 됩니다.
app.register_blueprint(auth_bp)

from time_control.time_handler import time_bp, KST  # 시간 상태 폴링 API
app.register_blueprint(time_bp)

from application_routes import application_bp  # 운동 신청/취소/현황 API
app.register_blueprint(application_bp)

from admin.capacity.routes import capacity_bp  # 임원진 정원 확정 API
app.register_blueprint(capacity_bp)

# --- [인메모리 초기화] ---
# 정원 캐시: DB → 메모리 적재 (서버 부팅 시 1회)
from admin.capacity.store import init_cache as init_capacity_cache
init_capacity_cache()

# 게시판: 백업 복구 + 백그라운드 저장 + 주간 리셋 스케줄러
from time_control.board_store import load_from_backup, start_background_saver
from time_control.scheduler_logic import start_reset_scheduler

load_from_backup()
start_background_saver()
start_reset_scheduler(KST)

if __name__ == '__main__':
    # 127.0.0.1로 설정하여 Nginx를 통해서만 접근 가능하도록 제한
    app.run(host='127.0.0.1', port=5000)
