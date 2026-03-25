#!/usr/bin/env bash
# configure.sh — 인스턴스 타입 감지 → .env 프로파일 전환 → PM2 재시작
#
# 사용법:
#   ./configure.sh          # CPU 수 자동 감지 후 적용
#   ./configure.sh small    # t3.small 프로파일 강제 적용
#   ./configure.sh xlarge   # c6i.xlarge 프로파일 강제 적용
#
# 피크타임 시작 전: ./configure.sh xlarge
# 피크타임 종료 후: ./configure.sh small

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"
ENV_SMALL="${SCRIPT_DIR}/.env.small"
ENV_XLARGE="${SCRIPT_DIR}/.env.xlarge"

# ── 프로파일 결정 ──────────────────────────────────────────────────────────────
if [[ "${1:-auto}" == "small" ]]; then
    PROFILE="small"
elif [[ "${1:-auto}" == "xlarge" ]]; then
    PROFILE="xlarge"
else
    # 자동 감지: CPU 코어 수 기준
    CPU_COUNT=$(nproc)
    if [[ "${CPU_COUNT}" -ge 4 ]]; then
        PROFILE="xlarge"
    else
        PROFILE="small"
    fi
    echo "[configure] CPU ${CPU_COUNT}코어 감지 → 프로파일: ${PROFILE}"
fi

# ── .env 파일에 프로파일 값 반영 ───────────────────────────────────────────────
# 전략: 기존 .env 파일의 SECRET_KEY 등 중요 값은 유지하면서
#        프로파일에 정의된 키만 추가/덮어씁니다.
PROFILE_FILE="${SCRIPT_DIR}/.env.${PROFILE}"

if [[ ! -f "${PROFILE_FILE}" ]]; then
    echo "[configure] ERROR: 프로파일 파일 없음: ${PROFILE_FILE}" >&2
    exit 1
fi

# .env 파일이 없으면 빈 파일 생성
touch "${ENV_FILE}"

echo "[configure] .env에 ${PROFILE} 프로파일 적용 중..."

# 프로파일 파일의 각 KEY=VALUE 줄을 .env에 반영 (주석/빈 줄 무시)
while IFS= read -r line; do
    # 주석(#) 및 빈 줄 건너뜀
    [[ -z "${line}" || "${line}" =~ ^[[:space:]]*# ]] && continue

    KEY="${line%%=*}"
    [[ -z "${KEY}" ]] && continue

    # .env에 해당 키가 이미 있으면 교체, 없으면 추가
    if grep -q "^${KEY}=" "${ENV_FILE}" 2>/dev/null; then
        # macOS(BSD sed)와 GNU sed 모두 호환
        sed -i.bak "s|^${KEY}=.*|${line}|" "${ENV_FILE}" && rm -f "${ENV_FILE}.bak"
    else
        echo "${line}" >> "${ENV_FILE}"
    fi
done < "${PROFILE_FILE}"

echo "[configure] .env 업데이트 완료:"
grep -E "^(GUNICORN_|BCRYPT_|VIP_|FLASK_VIP_)" "${ENV_FILE}" | sed 's/^/  /'

# ── PM2 재시작 ────────────────────────────────────────────────────────────────
if command -v pm2 &>/dev/null; then
    echo "[configure] PM2 재시작 중..."

    VIP_ENABLED=$(grep "^VIP_ENABLED=" "${ENV_FILE}" | cut -d= -f2 | tr -d '[:space:]')

    if [[ "${VIP_ENABLED}" == "true" ]]; then
        # 피크타임: VIP 인스턴스 포함 전체 재시작
        pm2 reload ecosystem.config.js --update-env
        echo "[configure] PM2 전체 재시작 완료 (VIP 인스턴스 포함)"
    else
        # 평시: VIP 인스턴스 제외하고 재시작
        pm2 reload ecosystem.config.js --update-env
        # VIP 프로세스가 실행 중이라면 중지
        pm2 stop gunicorn-vip 2>/dev/null && echo "[configure] gunicorn-vip 중지" || true
        echo "[configure] PM2 재시작 완료 (VIP 인스턴스 중지됨)"
    fi
else
    echo "[configure] WARNING: pm2가 설치되어 있지 않습니다. 서버를 수동으로 재시작하세요."
fi

echo "[configure] 완료 — 현재 프로파일: ${PROFILE}"
