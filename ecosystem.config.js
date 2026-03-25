// ecosystem.config.js — PM2 프로세스 관리 설정
//
// 사용법:
//   pm2 start ecosystem.config.js          # 전체 시작
//   pm2 reload ecosystem.config.js --update-env  # 무중단 재시작 + .env 재로드
//   pm2 stop all                           # 전체 중지
//   pm2 logs                               # 전체 로그 스트리밍
//
// 인스턴스 전환:
//   ./configure.sh xlarge   # 피크타임: gunicorn-vip 추가 기동
//   ./configure.sh small    # 평시: gunicorn-vip 중지, 나머지 설정 축소
//
// 프로세스 구성:
//   node-server      : Node.js Express (정적 파일 + 리버스 프록시, port 3000)
//   gunicorn-general : Flask GEN 인스턴스 (로그인/GET/취소, port 5000)
//   gunicorn-vip     : Flask VIP 인스턴스 (/api/apply 전용, port 5001) ← 피크타임만
//   apply-worker     : Redis → SQLite 백그라운드 워커

'use strict';

const path = require('path');

// ── 경로 설정 ──────────────────────────────────────────────────────────────────
const APP_DIR    = __dirname;
// Python 가상환경 경로: 실제 환경에 맞게 수정하세요.
// 예) /home/ubuntu/smash-renewal/venv/bin/python
const PYTHON_BIN = process.env.PYTHON_BIN || path.join(APP_DIR, 'venv', 'bin', 'python');
const GUNICORN   = process.env.GUNICORN_BIN || path.join(APP_DIR, 'venv', 'bin', 'gunicorn');

module.exports = {
  apps: [
    // ── 1. Node.js 서버 (정적 파일 + 리버스 프록시) ──────────────────────────
    {
      name        : 'node-server',
      script      : path.join(APP_DIR, 'server.js'),
      instances   : 1,
      exec_mode   : 'fork',
      cwd         : APP_DIR,
      env_file    : path.join(APP_DIR, '.env'),   // .env 자동 로드
      watch       : false,
      // Node.js 메모리 누수 방어: 512 MB 초과 시 자동 재시작
      max_memory_restart: '512M',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
    },

    // ── 2. Gunicorn GEN (일반 트래픽: 로그인 / GET / 취소) ───────────────────
    {
      name        : 'gunicorn-general',
      script      : GUNICORN,
      args        : `-c ${path.join(APP_DIR, 'gunicorn.conf.py')} app:app`,
      interpreter : 'none',     // gunicorn은 직접 실행 (Python 인터프리터 불필요)
      cwd         : APP_DIR,
      env_file    : path.join(APP_DIR, '.env'),
      watch       : false,
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
    },

    // ── 3. Gunicorn VIP (/api/apply 전용, 피크타임에만 기동) ─────────────────
    // configure.sh가 VIP_ENABLED=false 시 pm2 stop gunicorn-vip 처리
    {
      name        : 'gunicorn-vip',
      script      : GUNICORN,
      args        : `-c ${path.join(APP_DIR, 'gunicorn_vip.conf.py')} app:app`,
      interpreter : 'none',
      cwd         : APP_DIR,
      env_file    : path.join(APP_DIR, '.env'),
      watch       : false,
      // 평시에는 자동 재시작 비활성화 (configure.sh가 명시적으로 start/stop 제어)
      autorestart : false,
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
    },

    // ── 4. Redis → SQLite 백그라운드 워커 ────────────────────────────────────
    {
      name        : 'apply-worker',
      script      : path.join(APP_DIR, 'worker.py'),
      interpreter : PYTHON_BIN,
      cwd         : APP_DIR,
      env_file    : path.join(APP_DIR, '.env'),
      watch       : false,
      // 워커가 예외로 종료되면 즉시 재시작 (큐 적재 유실 방지)
      autorestart : true,
      max_restarts: 20,
      min_uptime  : '5s',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
    },
  ],
};
