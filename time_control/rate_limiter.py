# rate_limiter.py — 인메모리 슬라이딩 윈도우 Rate Limiter
#
# 매크로/도배 방지를 위해 IP 또는 User ID 기반으로 요청 횟수를 제한한다.
# Python 내장 모듈만 사용하여 1 GB 메모리 환경에 적합하다.

import threading
import time
from functools import wraps

from flask import request, jsonify

_lock = threading.Lock()
_requests: dict[str, list[float]] = {}

# 오래된 키를 정리하는 주기 (요청 수 기준)
_CLEANUP_EVERY = 200
_request_count = 0

# ── 글로벌 IP 차단 (분당 요청 수 초과 시 일시 차단) ─────────────────────────────
_GLOBAL_MAX_PER_IP = 120        # IP당 분당 최대 요청 수
_GLOBAL_WINDOW = 60             # 윈도우 크기 (초)
_ip_requests: dict[str, list[float]] = {}
_ip_lock = threading.Lock()

# Rate limiter 키 총 개수 상한 (메모리 폭증 방어)
_MAX_KEYS = 5000


def _get_real_ip() -> str:
    """Node.js 프록시가 전달한 X-Forwarded-For 헤더에서 실제 클라이언트 IP를 추출한다.

    gunicorn.conf.py의 forwarded_allow_ips = "127.0.0.1" 설정으로
    신뢰할 수 있는 프록시(Node.js)에서만 이 헤더를 수용한다.
    헤더 스푸핑 방지: Node.js가 항상 자체적으로 X-Forwarded-For를 덮어쓰므로
    클라이언트가 직접 이 헤더를 조작해도 무시된다.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # "client_ip, proxy1, proxy2" 형식 → 첫 번째가 실제 클라이언트
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "0.0.0.0"


def _cleanup(window: float) -> None:
    """윈도우를 벗어난 오래된 요청 기록을 전체 정리한다."""
    now = time.time()
    expired_keys = []
    for key, timestamps in _requests.items():
        _requests[key] = [t for t in timestamps if now - t < window]
        if not _requests[key]:
            expired_keys.append(key)
    for key in expired_keys:
        del _requests[key]


def check_global_ip_limit() -> bool:
    """IP 기반 글로벌 요청 수 검사. 제한 초과 시 True를 반환한다.

    모든 엔드포인트에 앞서 호출하여 특정 IP의 비정상적 대량 요청을 차단한다.
    """
    ip = _get_real_ip()
    now = time.time()

    with _ip_lock:
        if ip not in _ip_requests:
            # 키 수 상한 체크 (메모리 방어)
            if len(_ip_requests) >= _MAX_KEYS:
                # 가장 오래된 항목부터 정리
                cutoff = now - _GLOBAL_WINDOW
                expired = [k for k, v in _ip_requests.items() if not v or v[-1] < cutoff]
                for k in expired:
                    del _ip_requests[k]
            _ip_requests[ip] = []

        _ip_requests[ip] = [t for t in _ip_requests[ip] if now - t < _GLOBAL_WINDOW]

        if len(_ip_requests[ip]) >= _GLOBAL_MAX_PER_IP:
            return True  # 차단

        _ip_requests[ip].append(now)

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
                    _cleanup(window_seconds)
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
