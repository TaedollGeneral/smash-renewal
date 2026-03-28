# rate_limiter.py — 인메모리 슬라이딩 윈도우 Rate Limiter
#
# 매크로/도배 방지를 위해 IP 또는 User ID 기반으로 요청 횟수를 제한한다.
# Python 내장 모듈만 사용하여 1 GB 메모리 환경에 적합하다.

import os
import threading
import time
from functools import wraps

import jwt as _jwt
from flask import request, jsonify

_lock = threading.Lock()
_requests: dict[str, list[float]] = {}

# 오래된 키를 정리하는 주기 (요청 수 기준)
_CLEANUP_EVERY = 200
_request_count = 0

# cleanup 시 사용할 최대 윈도우 — 모든 엔드포인트 window(최대 60s)보다 크게 잡아
# 서로 다른 window를 가진 엔드포인트 기록이 청소 타이밍에 따라 조기 삭제되지 않도록 한다.
_CLEANUP_WINDOW = 120

# ── 글로벌 요청 제한 ──────────────────────────────────────────────────────────
# 미인증(IP 기반): NAT 뒤 다수 사용자가 공유하므로 상한을 넉넉하게 설정
# 인증(User ID 기반): 엔드포인트별 rate_limit이 주 방어선이므로 여기서는 안전망 수준만
_GLOBAL_MAX_PER_IP   = 300      # IP당 분당 최대 요청 수 (미인증, DDoS 방어용)
_GLOBAL_MAX_PER_USER = 180      # User ID당 분당 최대 요청 수 (인증, 안전망)
_GLOBAL_WINDOW = 60             # 윈도우 크기 (초)
_ip_requests: dict[str, list[float]] = {}
_ip_lock = threading.Lock()

# Rate limiter 키 총 개수 상한 (메모리 폭증 방어)
_MAX_KEYS = 5000


def _get_real_ip() -> str:
    """Node.js 프록시가 전달한 X-Forwarded-For 헤더에서 실제 클라이언트 IP를 추출한다.

    보안 설계:
      - Gunicorn은 127.0.0.1(Node.js)에서만 접근 가능 (bind = "127.0.0.1:5000")
      - Node.js가 X-Forwarded-For를 req.ip로 덮어쓰므로 클라이언트 조작 불가
      - 추가 방어: request.remote_addr이 127.0.0.1(프록시)인 경우에만 X-Forwarded-For 신뢰
        → 만약 Flask가 직접 외부에 노출되면 IP 스푸핑 차단
    """
    # Node.js 프록시를 거쳐온 요청만 X-Forwarded-For를 신뢰
    remote = request.remote_addr or "0.0.0.0"
    if remote in ("127.0.0.1", "::1"):
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return remote


def _get_global_key() -> tuple[str, int]:
    """글로벌 Rate Limit 키와 허용 상한을 반환한다.

    JWT가 유효하면 (uid:{user_id}, _GLOBAL_MAX_PER_USER) 반환 — NAT 환경에서
    여러 사용자가 같은 IP를 공유하더라도 각자의 한도로 독립 제한한다.
    JWT 없음 / 디코딩 실패 시 (ip:{real_ip}, _GLOBAL_MAX_PER_IP) 폴백.

    토큰 만료·서명 검증은 @token_required가 담당하므로 여기서는 user_id 추출만 수행한다.
    """
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header.split(' ', 1)[1]
        try:
            secret = os.environ.get('SECRET_KEY', '')
            if secret:
                payload = _jwt.decode(token, secret, algorithms=["HS256"])
                user_id = payload.get('id')
                if user_id:
                    return f"uid:{user_id}", _GLOBAL_MAX_PER_USER
        except Exception:
            pass
    return f"ip:{_get_real_ip()}", _GLOBAL_MAX_PER_IP


def _cleanup() -> None:
    """윈도우를 벗어난 오래된 요청 기록을 전체 정리한다.

    _CLEANUP_WINDOW(120s)를 기준으로 전체 _requests를 청소한다.
    개별 엔드포인트의 window_seconds와 무관하게 항상 동일한 기준을 사용하여,
    window가 긴 엔드포인트(예: 로그인 30s, 비밀번호 변경 60s)의 기록이
    window가 짧은 엔드포인트(예: apply 10s)의 cleanup 타이밍에 조기 삭제되지 않는다.
    """
    now = time.time()
    expired_keys = []
    for key, timestamps in _requests.items():
        _requests[key] = [t for t in timestamps if now - t < _CLEANUP_WINDOW]
        if not _requests[key]:
            expired_keys.append(key)
    for key in expired_keys:
        del _requests[key]


def check_global_ip_limit() -> bool:
    """글로벌 요청 수 검사. 제한 초과 시 True를 반환한다.

    - 인증 요청(JWT 있음): User ID 기준으로 제한 — NAT 공유 IP 오차단 방지
    - 미인증 요청(JWT 없음): IP 기준으로 제한 — DDoS/봇 방어
    """
    key, max_requests = _get_global_key()
    now = time.time()

    with _ip_lock:
        if key not in _ip_requests:
            # 키 수 상한 체크 (메모리 방어)
            if len(_ip_requests) >= _MAX_KEYS:
                cutoff = now - _GLOBAL_WINDOW
                expired = [k for k, v in _ip_requests.items() if not v or v[-1] < cutoff]
                for k in expired:
                    del _ip_requests[k]
            _ip_requests[key] = []

        _ip_requests[key] = [t for t in _ip_requests[key] if now - t < _GLOBAL_WINDOW]

        if len(_ip_requests[key]) >= max_requests:
            return True  # 차단

        _ip_requests[key].append(now)

    return False  # 통과


def rate_limit(max_requests: int = 5, window_seconds: int = 10):
    """슬라이딩 윈도우 방식의 Rate Limiter 데코레이터.

    Args:
        max_requests: 윈도우 내 최대 허용 요청 수
        window_seconds: 슬라이딩 윈도우 크기 (초)

    키 결정 우선순위:
        1) JWT 디코딩 후 설정된 request.current_user['id'] (User ID 기반)
        2) X-Forwarded-For → request.remote_addr (IP 기반, 토큰 없는 경우)

    Note:
        @token_required 보다 뒤에(안쪽에) 배치하면 User ID 기반,
        앞에(바깥쪽에) 배치하면 IP 기반으로 동작한다.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            global _request_count

            # 키 결정: 인증된 사용자면 user_id, 아니면 실제 클라이언트 IP
            current_user = getattr(request, "current_user", None)
            if current_user and current_user.get("id"):
                key = f"uid:{current_user['id']}"
            else:
                key = f"ip:{_get_real_ip()}"

            now = time.time()

            with _lock:
                # 주기적 정리
                _request_count += 1
                if _request_count >= _CLEANUP_EVERY:
                    _cleanup()
                    _request_count = 0

                # 키 수 상한 체크 (메모리 방어)
                if key not in _requests and len(_requests) >= _MAX_KEYS:
                    cutoff = now - window_seconds
                    expired = [k for k, v in _requests.items() if not v or v[-1] < cutoff]
                    for k in expired:
                        del _requests[k]

                if key not in _requests:
                    _requests[key] = []

                # 윈도우 밖 기록 제거
                _requests[key] = [
                    t for t in _requests[key] if now - t < window_seconds
                ]

                if len(_requests[key]) >= max_requests:
                    return jsonify({
                        "error": "요청이 너무 많습니다. 잠시 후 다시 시도해주세요."
                    }), 429

                _requests[key].append(now)

            return f(*args, **kwargs)
        return wrapper
    return decorator
