# gunicorn.conf.py — Gunicorn 프로덕션 설정 (GEN: 일반 트래픽 전용)
#
# 실행: gunicorn -c gunicorn.conf.py app:app
#
# 인스턴스별 워커 수는 .env 프로파일로 제어된다:
#   t3.small  (평시):     GUNICORN_WORKERS=2, GUNICORN_THREADS=4 → 8 슬롯
#   c6i.xlarge (피크타임): GUNICORN_WORKERS=3, GUNICORN_THREADS=4 → 12 슬롯
#
# configure.sh 가 .env를 교체하고 PM2를 재시작하면 자동 적용된다.

import os
from dotenv import load_dotenv
load_dotenv()  # .env → 환경변수 로드 (gunicorn은 Flask보다 먼저 실행되므로 직접 로드)

# ── 워커 설정 ────────────────────────────────────────────────────────────────────
workers      = int(os.environ.get("GUNICORN_WORKERS", "2"))   # 기본값: t3.small 기준
threads      = int(os.environ.get("GUNICORN_THREADS", "4"))
worker_class = "gthread"     # 스레드 기반 워커 (I/O 바운드에 적합)

# ── 타임아웃 ─────────────────────────────────────────────────────────────────────
timeout = 30                 # 워커가 30초 내 응답 못하면 재시작 (bcrypt 최악 케이스 커버)
graceful_timeout = 10        # 재시작 시 진행 중 요청 마무리 대기 시간
keepalive = 2                # Keep-Alive 연결 유지 시간 (Node.js 프록시 뒤이므로 짧게)

# ── 메모리 누수 방어 ─────────────────────────────────────────────────────────────
max_requests = 1000          # 워커당 1000건 처리 후 자동 재시작 (메모리 누수 누적 방지)
max_requests_jitter = 100    # 0~100 랜덤 분산으로 워커 동시 재시작 방지

# ── 바인딩 ───────────────────────────────────────────────────────────────────────
bind = "127.0.0.1:5000"      # Node.js 프록시에서만 접근 (외부 직접 접속 차단)

# ── 프록시 헤더 ──────────────────────────────────────────────────────────────────
forwarded_allow_ips = "127.0.0.1"   # Node.js 프록시만 X-Forwarded-For 신뢰
proxy_protocol = False

# ── 로깅 ─────────────────────────────────────────────────────────────────────────
accesslog = "-"              # stdout 출력 (PM2 로그 수집)
loglevel = "warning"         # 일반 운영: warning 이상만 출력

# ── 프로세스 ─────────────────────────────────────────────────────────────────────
preload_app = True           # 앱을 미리 로드하여 워커 간 메모리 공유 (Copy-on-Write)
                             # → 2 워커 기준 ~20-30 MB 절약


# ── post_fork: 워커별 데몬 스레드 시작 ─────────────────────────────────────────
# preload_app=True 시 app.py 모듈은 fork() 전 마스터에서 한 번만 로드된다.
# POSIX fork()는 스레드를 자식 프로세스에 복사하지 않으므로,
# 데몬 스레드(주간 리셋 스케줄러, 푸시 발송 워커)는 각 워커에서 새로 시작해야 한다.
#
# 단, 주간 리셋 스케줄러(weekly-reset)는 워커 1개에서만 실행한다.
# 2개 워커가 동시에 리셋하면 로그 중복 · 이중 처리 위험이 있으므로
# worker.nr == 0 (첫 번째 워커)에서만 시작한다.
def post_fork(server, worker):
    from notifications.sender import start_push_worker

    # 푸시 워커: 모든 워커에서 시작 (자기 프로세스 큐 소비)
    start_push_worker()

    # 주간 리셋 스케줄러: 워커 0에서만 시작 (중복 실행 방지)
    if worker.nr == 0:
        from time_control.time_handler import KST
        from time_control.scheduler_logic import start_reset_scheduler
        start_reset_scheduler(KST)
