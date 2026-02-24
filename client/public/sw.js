// sw.js — Service Worker for SMASH PWA
//
// 역할:
//   1. push 이벤트: 백엔드(pywebpush)가 보낸 WebPush 메시지를 받아 알림으로 표시
//   2. notificationclick 이벤트: 알림 클릭 시 앱 탭을 포커스하거나 새 탭 열기
//   3. message 이벤트: Sidebar의 "업데이트" 기능에서 보내는 SKIP_WAITING 처리
//   4. install / activate: SW 수명주기 관리

const CACHE_NAME = 'smash-v1';

// ── 설치 ──────────────────────────────────────────────────────────────────────
self.addEventListener('install', (event) => {
  // 대기 없이 즉시 활성화 (새 SW가 바로 제어권을 가짐)
  self.skipWaiting();
});

// ── 활성화 ────────────────────────────────────────────────────────────────────
self.addEventListener('activate', (event) => {
  // 이미 열려 있는 모든 탭을 새 SW가 즉시 제어
  event.waitUntil(self.clients.claim());
});

// ── Push 수신 ─────────────────────────────────────────────────────────────────
// 백엔드 sender.py 의 payload 구조:
//   { "title": str, "body": str, "icon": str, "data": dict }
self.addEventListener('push', (event) => {
  let title = '알림';
  let options = {
    body: '',
    icon: '/android-chrome-192x192.png',
    badge: '/android-chrome-192x192.png',
    data: {},
  };

  if (event.data) {
    try {
      const payload = event.data.json();
      title = payload.title || title;
      options.body = payload.body || '';
      options.icon = payload.icon || options.icon;
      options.data = payload.data || {};
    } catch {
      // JSON 파싱 실패 시 텍스트를 본문으로 사용
      options.body = event.data.text();
    }
  }

  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

// ── 알림 클릭 ─────────────────────────────────────────────────────────────────
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  // data.url 이 있으면 해당 URL, 없으면 앱 루트로 이동
  const targetUrl = (event.notification.data && event.notification.data.url)
    ? event.notification.data.url
    : '/';

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      // 이미 열린 탭이 있으면 포커스
      for (const client of clientList) {
        const clientUrl = new URL(client.url);
        if (clientUrl.pathname === new URL(targetUrl, self.location.origin).pathname) {
          return client.focus();
        }
      }
      // 열린 탭이 없으면 새 탭 열기
      return self.clients.openWindow(targetUrl);
    })
  );
});

// ── 메시지 처리 (Sidebar 업데이트 기능) ──────────────────────────────────────
// Sidebar.tsx 에서 waitingReg.waiting.postMessage({ type: 'SKIP_WAITING' }) 호출 시 처리
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
