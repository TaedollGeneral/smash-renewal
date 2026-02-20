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


def rate_limit(max_requests: int = 5, window_seconds: int = 10):
    """슬라이딩 윈도우 방식의 Rate Limiter 데코레이터.

    Args:
        max_requests: 윈도우 내 최대 허용 요청 수
        window_seconds: 슬라이딩 윈도우 크기 (초)

    키 결정 우선순위:
        1) JWT 디코딩 후 설정된 request.current_user['id'] (User ID 기반)
        2) request.remote_addr (IP 기반, 토큰 없는 경우)

    Note:
        @token_required 보다 뒤에(안쪽에) 배치하면 User ID 기반,
        앞에(바깥쪽에) 배치하면 IP 기반으로 동작한다.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            global _request_count

            # 키 결정: 인증된 사용자면 user_id, 아니면 IP
            current_user = getattr(request, "current_user", None)
            if current_user and current_user.get("id"):
                key = f"uid:{current_user['id']}"
            else:
                key = f"ip:{request.remote_addr}"

            now = time.time()

            with _lock:
                # 주기적 정리
                _request_count += 1
                if _request_count >= _CLEANUP_EVERY:
                    _cleanup(window_seconds)
                    _request_count = 0

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
