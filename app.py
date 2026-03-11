# /home/ubuntu/smash-renewal/app.py
import os
from flask import Flask

from dotenv import load_dotenv
load_dotenv()  # .env 파일을 OS 환경변수로 로드

app = Flask(__name__)

# [보안] 시크릿 키를 환경변수에서 읽음 (미설정 시 서버 시작 차단)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
if not app.config['SECRET_KEY']:
    raise RuntimeError("환경변수 SECRET_KEY가 설정되지 않았습니다. 서버를 시작할 수 없습니다.")

# [보안] 요청 Body 크기 제한 — 대용량 JSON 폭탄으로 인한 메모리 고갈 방지
# 일반 신청/로그인 JSON은 1 KB 미만이므로 1 MB면 충분
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  # 1 MB

# --- [글로벌 IP Rate Limit] ---
# 모든 엔드포인트 진입 전에 IP당 분당 요청 수를 검사한다.
# 비정상적으로 많은 요청을 보내는 IP를 조기에 차단하여 서버 리소스를 보호한다.
from time_control.rate_limiter import check_global_ip_limit
from flask import jsonify as _jsonify

@app.before_request
def _global_ip_guard():
    if check_global_ip_limit():
        return _jsonify({"error": "요청이 너무 많습니다. 잠시 후 다시 시도해주세요."}), 429

# --- [API 전역 에러 핸들러] ---
# Flask 기본 에러 핸들러는 HTML을 반환하지만, /api/ 경로에서는 클라이언트가
# JSON을 기대하므로 미처리 예외 발생 시 JSON 형태의 500 응답을 반환한다.
from flask import request as _request

@app.errorhandler(500)
def _handle_500(e):
    return _jsonify({"error": "서버 내부 오류가 발생했습니다."}), 500

@app.errorhandler(Exception)
def _handle_exception(e):
    return _jsonify({"error": "서버 내부 오류가 발생했습니다."}), 500

# --- [모듈 등록 구역] ---
from smash_db.auth import auth_bp, migrate_token_version_column
app.register_blueprint(auth_bp)

from time_control.time_handler import time_bp, KST  # 시간 상태 폴링 API
app.register_blueprint(time_bp)

from application_routes import application_bp  # 운동 신청/취소/현황 API
app.register_blueprint(application_bp)

from admin.capacity.routes import capacity_bp  # 임원진 정원 확정 API
app.register_blueprint(capacity_bp)

from notifications.routes import notif_bp       # 푸시 알림 API
app.register_blueprint(notif_bp)

# --- [인메모리 초기화] ---
# DB 마이그레이션: token_version 컬럼 추가 (없는 경우만)
migrate_token_version_column()

# 정원 캐시: DB → 메모리 적재 (서버 부팅 시 1회)
from admin.capacity.store import init_cache as init_capacity_cache
init_capacity_cache()

# 게시판: SQLite applications 테이블 초기화 + 레거시 백업 마이그레이션
from time_control.board_store import ensure_table, load_from_backup

ensure_table()         # applications 테이블 생성 (없을 때만)
load_from_backup()     # board_backup.json → SQLite 일회성 마이그레이션

# 푸시 알림: SQLite 테이블 초기화
from notifications.store import init_db as init_push_db
init_push_db()

# 백그라운드 데몬 스레드 (주간 리셋 스케줄러 + 푸시 발송 워커)
# ──────────────────────────────────────────────────────────────────────────────
# preload_app=True (gunicorn.conf.py) 환경에서는 이 모듈이 fork() 전 마스터에서 로드되며,
# POSIX fork()는 스레드를 자식 프로세스에 복사하지 않는다.
# → Gunicorn: gunicorn.conf.py의 post_fork 훅에서 워커별로 시작
# → 개발 서버: if __name__ == '__main__' 에서 직접 시작

if __name__ == '__main__':
    # 개발 환경 전용 — 로컬 테스트 시에만 사용
    from time_control.scheduler_logic import start_reset_scheduler
    from notifications.sender import start_push_worker
    start_reset_scheduler(KST)
    start_push_worker()
    app.run(host='127.0.0.1', port=5000, debug=True)
