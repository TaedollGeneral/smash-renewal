# notifications/sender.py — 비동기 WebPush 발송 워커
#
# 설계 원칙:
#   - 알림 발송은 HTTP 응답 흐름과 완전히 분리된 백그라운드 스레드에서 처리
#   - queue.Queue를 통해 발송 요청을 버퍼링 → 응답 지연 없음
#   - requests.Session()으로 커넥션 풀을 재사용 → 소켓 오버헤드 최소화
#   - pywebpush.webpush()에 requests_session을 주입하여 VAPID 서명,
#     페이로드 암호화, HTTP 전송을 단일 호출로 처리
#   - 410 Gone 응답 → 만료된 구독을 SQLite에서 자동 삭제

import json
import logging
import os
import queue
import threading
from typing import Any
from urllib.parse import urlparse

import requests
from pywebpush import WebPusher, WebPushException
from http.cookiejar import DefaultCookiePolicy

logger = logging.getLogger(__name__)

# ── VAPID 설정 ────────────────────────────────────────────────────────────────
# .env 또는 시스템 환경변수에서 읽는다.
#
# 키 생성 방법 (최초 1회):
#   from py_vapid import Vapid
#   vapid = Vapid()
#   vapid.generate_keys()
#   print("VAPID_PRIVATE_KEY:", vapid.private_pem().decode())
#   print("VAPID_PUBLIC_KEY:",  vapid.public_key.public_bytes(...))
#
# 또는 CLI:
#   vapid --gen --applicationServerKey
#
# 환경변수:
#   VAPID_PRIVATE_KEY — PEM 형식 또는 Base64url raw 32-byte private key
#   VAPID_PUBLIC_KEY  — Base64url uncompressed 65-byte public key (프론트용)
#   VAPID_EMAIL       — mailto: 클레임 이메일 (예: admin@example.com)

VAPID_PRIVATE_KEY: str = os.environ.get("VAPID_PRIVATE_KEY", "")
VAPID_CLAIMS: dict[str, str] = {
    "sub": f"mailto:{os.environ.get('VAPID_EMAIL', 'admin@localhost')}"
}

# ── 발송 큐 ───────────────────────────────────────────────────────────────────
# 큐 항목 구조:
# {
#   "user_id":  str,       — 만료 구독 삭제에 사용 (JWT 추출값)
#   "endpoint": str,       — Push 서비스 URL
#   "p256dh":   str,       — 브라우저 공개 키 (Base64url)
#   "auth":     str,       — 인증 시크릿 (Base64url)
#   "payload": {
#       "title": str,
#       "body":  str,
#       "icon":  str,
#       "data":  dict,
#   }
# }
_push_queue: queue.Queue = queue.Queue()

# ── requests.Session (커넥션 풀 재사용) ───────────────────────────────────────
# 워커 스레드 단독 접근 → 별도 Lock 불필요
# pywebpush.webpush()의 requests_session 파라미터로 주입하여 커넥션을 재사용한다.

def _create_session() -> requests.Session:
    session = requests.Session()
    
    # [핵심] 푸시 알림에는 쿠키가 필요 없으므로, 모든 쿠키 저장을 무시하는 정책 적용
    session.cookies.set_policy(DefaultCookiePolicy(set_cookie=False))
    
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=4,
        pool_maxsize=10,
        max_retries=1,
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

_session: requests.Session = _create_session()

# HTTPAdapter: 1GB 서버 환경에 맞게 pool_connections/pool_maxsize 보수적으로 설정
_adapter = requests.adapters.HTTPAdapter(
    pool_connections=4,
    pool_maxsize=10,
    max_retries=1,          # 네트워크 에러 시 1회 자동 재시도
)
_session.mount("https://", _adapter)
_session.mount("http://", _adapter)


# ── 공개 API ──────────────────────────────────────────────────────────────────

def enqueue_push(
    user_id: str,
    endpoint: str,
    p256dh: str,
    auth: str,
    title: str,
    body: str,
    icon: str = "/icons/icon-192x192.png",
    extra_data: dict[str, Any] | None = None,
) -> None:
    """WebPush 발송 작업을 큐에 추가한다 (Non-blocking, 즉시 반환).

    실제 발송은 백그라운드 push-worker 스레드에서 비동기로 처리된다.
    HTTP 응답 흐름에서 호출해도 응답 지연이 발생하지 않는다.

    Args:
        user_id:    JWT에서 추출한 학번 (만료 구독 삭제 추적에 사용)
        endpoint:   Push 서비스 엔드포인트 URL
        p256dh:     브라우저 공개 키 (Base64url)
        auth:       인증 시크릿 (Base64url)
        title:      알림 제목
        body:       알림 본문
        icon:       알림 아이콘 URL 경로 (기본값: /icons/icon-192x192.png)
        extra_data: Service Worker의 notificationclick 이벤트에서 사용할 추가 데이터
    """
    _push_queue.put({
        "user_id":  user_id,
        "endpoint": endpoint,
        "p256dh":   p256dh,
        "auth":     auth,
        "payload": {
            "title": title,
            "body":  body,
            "icon":  icon,
            "data":  extra_data or {},
        },
    })


def enqueue_push_to_user(
    user_id: str,
    title: str,
    body: str,
    icon: str = "/icons/icon-192x192.png",
    extra_data: dict[str, Any] | None = None,
) -> None:
    """특정 사용자의 모든 구독 기기로 푸시를 큐잉한다.

    SQLite에서 해당 user_id의 구독 목록을 1회 조회한 뒤,
    각 구독을 enqueue_push()로 큐에 추가한다.

    Args:
        user_id:    JWT에서 추출한 학번
        title:      알림 제목
        body:       알림 본문
        icon:       알림 아이콘 경로
        extra_data: 추가 데이터
    """
    from notifications.store import get_subscriptions_by_user
    for sub in get_subscriptions_by_user(user_id):
        enqueue_push(
            user_id=user_id,
            endpoint=sub["endpoint"],
            p256dh=sub["p256dh"],
            auth=sub["auth"],
            title=title,
            body=body,
            icon=icon,
            extra_data=extra_data,
        )


def enqueue_push_to_all(
    title: str,
    body: str,
    icon: str = "/icons/icon-192x192.png",
    extra_data: dict[str, Any] | None = None,
) -> None:
    """push_subscriptions 테이블의 모든 구독자에게 푸시를 큐잉한다.

    정원 확정처럼 구독 여부와 관계없이 등록된 모든 기기로 알림을 보낼 때 사용.

    처리 흐름:
      1) SQLite에서 모든 구독 정보를 1회 조회 (전체 SELECT)
      2) 각 구독을 enqueue_push()로 큐에 추가 (실제 발송은 워커 스레드)

    Args:
        title:      알림 제목
        body:       알림 본문
        icon:       알림 아이콘 경로
        extra_data: Service Worker에 전달할 추가 데이터
    """
    from notifications.store import get_all_subscriptions
    for sub in get_all_subscriptions():
        enqueue_push(
            user_id=sub["user_id"],
            endpoint=sub["endpoint"],
            p256dh=sub["p256dh"],
            auth=sub["auth"],
            title=title,
            body=body,
            icon=icon,
            extra_data=extra_data,
        )


def enqueue_push_to_category_subscribers(
    category: str,
    title: str,
    body: str,
    icon: str = "/icons/icon-192x192.png",
    extra_data: dict[str, Any] | None = None,
) -> None:
    """특정 카테고리 알림 구독자 전원에게 푸시를 큐잉한다.

    처리 흐름:
      1) In-memory category_subscribers에서 대상 user_id 목록 추출 (DB I/O 없음)
      2) 각 사용자의 구독을 SQLite에서 조회 (user_id당 1회 DB I/O)
      3) 큐에 추가 (실제 발송은 워커 스레드에서 처리)

    Args:
        category:   NOTIF_CATEGORIES 중 하나 (예: "WED_REGULAR", "FRI_GUEST")
        title:      알림 제목
        body:       알림 본문
        icon:       알림 아이콘 경로
        extra_data: 추가 데이터
    """
    from notifications.store import get_subscribers_for_category
    for uid in get_subscribers_for_category(category):
        enqueue_push_to_user(uid, title, body, icon, extra_data)


# ── 내부 발송 로직 ────────────────────────────────────────────────────────────

def _build_vapid_claims(endpoint: str) -> dict[str, str]:
    """엔드포인트 origin을 audience로 포함한 VAPID claims를 반환한다."""
    parsed = urlparse(endpoint)
    audience = f"{parsed.scheme}://{parsed.netloc}"
    return {**VAPID_CLAIMS, "aud": audience}


def _send_one(item: dict[str, Any]) -> None:
    """큐에서 꺼낸 항목 하나를 WebPush로 발송한다.

    동작:
      1) pywebpush.webpush()로 VAPID 서명 + 페이로드 암호화 + HTTP 전송
         → requests_session에 공유 Session을 주입하여 커넥션 재사용
      2) 410 Gone → 만료된 구독을 SQLite에서 자동 삭제
      3) VAPID 키 미설정 시 발송 skip (개발 환경 대비)
      4) 모든 예외를 캐치하여 워커 루프 중단을 방지
    """
    if not VAPID_PRIVATE_KEY:
        logger.warning("VAPID_PRIVATE_KEY 미설정 — 푸시 발송 skip")
        return

    user_id  = item["user_id"]
    endpoint = item["endpoint"]

    subscription_info = {
        "endpoint": endpoint,
        "keys": {
            "p256dh": item["p256dh"],
            "auth":   item["auth"],
        },
    }
    encoded_payload = json.dumps(item["payload"], ensure_ascii=False)

    try:
        # [정석적인 방법] WebPusher 객체를 직접 생성하면서 공유 Session 주입
        pusher = WebPusher(
            subscription_info=subscription_info,
            requests_session=_session
        )
        
        # 주입된 세션을 바탕으로 발송
        pusher.send(
            data=encoded_payload,
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims=_build_vapid_claims(endpoint),
            timeout=10
        )
    except WebPushException as exc:
        resp = getattr(exc, "response", None)
        status = getattr(resp, "status_code", None)
        if status == 410:
            # 브라우저가 구독을 취소했거나 만료 → DB에서 삭제
            logger.info("만료된 구독 삭제: user=%s endpoint=%.80s", user_id, endpoint)
            from notifications.store import delete_subscription
            delete_subscription(user_id, endpoint)
        else:
            logger.warning("WebPushException (status=%s): %s (user=%s)",
                           status, exc, user_id)
    except requests.exceptions.Timeout:
        logger.warning("WebPush 타임아웃: user=%s endpoint=%.80s", user_id, endpoint)
    except Exception as exc:  # noqa: BLE001
        logger.warning("WebPush 예외: %s (user=%s)", exc, user_id)


# ── 백그라운드 워커 ───────────────────────────────────────────────────────────

def _worker() -> None:
    """큐를 모니터링하며 발송 항목을 순차 처리하는 데몬 루프.

    Queue.get(timeout=1):
      - 큐가 비어 있으면 1초 대기 후 재시도 → CPU 점유 없이 유휴 상태 유지
      - 큐에 항목이 들어오면 즉시 깨어나 _send_one()을 호출
    예외 발생 시에도 루프가 종료되지 않아 워커가 지속적으로 실행된다.
    """
    logger.info("push-worker 데몬 스레드 시작")
    while True:
        try:
            item = _push_queue.get(timeout=1)
        except queue.Empty:
            continue

        try:
            _send_one(item)
        except Exception as exc:  # noqa: BLE001
            logger.exception("push-worker 처리 중 예기치 않은 예외: %s", exc)
        finally:
            _push_queue.task_done()


def start_push_worker() -> None:
    """WebPush 발송 백그라운드 데몬 스레드를 시작한다.

    daemon=True: 메인 프로세스 종료 시 스레드도 자동 종료된다.
    app.py의 초기화 블록에서 1회 호출해야 한다.
    """
    t = threading.Thread(target=_worker, daemon=True, name="push-worker")
    t.start()
    logger.info("push-worker 데몬 스레드 등록 완료")
