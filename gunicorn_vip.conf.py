# gunicorn_vip.conf.py — Gunicorn VIP 인스턴스 (POST /api/apply 전용)
#
# 실행: gunicorn -c gunicorn_vip.conf.py app:app
# 조건: VIP_ENABLED=true (c6i.xlarge 피크타임에만 PM2가 이 프로세스를 기동)
#
# 역할:
#   - POST /api/apply 요청만 수신 (Node.js server.js가 라우팅)
#   - 유효성 검증 → redis.lpush("apply_queue") → 즉시 200 OK 반환
#   - bcrypt/SQLite 직접 접근 없음 → timeout을 짧게 설정해도 안전
#
# 인스턴스별 수치:
#   c6i.xlarge (피크타임): GUNICORN_VIP_WORKERS=2, GUNICORN_VIP_THREADS=4 → 8 슬롯

import os
from dotenv import load_dotenv
load_dotenv()

# ── 워커 설정 ─────────────────────────────────────────────────────────────────
workers      = int(os.environ.get("GUNICORN_VIP_WORKERS", "2"))
threads      = int(os.environ.get("GUNICORN_VIP_THREADS", "4"))
worker_class = "gthread"

# ── 타임아웃 ──────────────────────────────────────────────────────────────────
# /api/apply는 Redis lpush 후 즉시 응답 (실제 처리 < 50ms).
# 타임아웃을 짧게 잡아 hung worker를 빠르게 재생성한다.
timeout          = 10
graceful_timeout = 5
keepalive        = 2

# ── 메모리 누수 방어 ──────────────────────────────────────────────────────────
# apply는 요청 처리가 가벼우므로 더 많은 요청을 처리하고 재시작한다.
max_requests        = 2000
max_requests_jitter = 200

# ── 바인딩 ────────────────────────────────────────────────────────────────────
bind = "127.0.0.1:5001"   # GEN 포트(5000)와 분리. Node.js에서만 접근 가능.

# ── 프록시 헤더 ───────────────────────────────────────────────────────────────
forwarded_allow_ips = "127.0.0.1"
proxy_protocol      = False

# ── 로깅 ──────────────────────────────────────────────────────────────────────
accesslog = "-"
loglevel  = "warning"

# ── 프로세스 ──────────────────────────────────────────────────────────────────
preload_app = True

# ── on_starting: 잔존 소켓 파일 정리 ─────────────────────────────────────────
# gunicorn.conf.py와 동일한 이유. GEN · VIP 모두 같은 CWD를 사용하므로
# 양쪽 모두 on_starting에서 *.ctl 파일을 정리한다.
def on_starting(server):
    import glob
    import os
    for f in glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), '*.ctl')):
        try:
            os.unlink(f)
        except OSError:
            pass


# ── post_fork: 워커별 데몬 스레드 시작 ────────────────────────────────────────
# VIP 인스턴스는 /api/apply만 처리하므로:
#   - 푸시 알림 워커: 시작 (알림 트리거는 apply 성공 후 발생 가능)
#   - 주간 리셋 스케줄러: 시작하지 않음 (GEN 인스턴스 worker 0이 담당, 중복 방지)
def post_fork(server, worker):
    from notifications.sender import start_push_worker
    start_push_worker()
