// hooks/usePushNotifications.ts — WebPush 구독 등록 훅
//
// 설계 원칙:
//   - 모든 실패는 console.warn으로 조용히 처리 (UX 방해 없음)
//   - UPSERT 방식이므로 매 로그인/페이지 로드 시 호출 가능 (멱등성 보장)
//   - VAPID 공개 키는 백엔드 /api/vapid-public-key에서 동적으로 조회
//     → 프론트엔드 환경변수(VITE_*) 불필요, 배포 설정 단순화
//   - 이미 granted 상태라면 권한 팝업 없이 바로 subscribe

import { useCallback } from 'react';

/**
 * Base64url 문자열 → Uint8Array 변환
 * PushManager.subscribe()의 applicationServerKey 형식 요구에 맞춤.
 */
function urlBase64ToUint8Array(base64String: string): Uint8Array<ArrayBuffer> {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = atob(base64);
  const output = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; i++) {
    output[i] = rawData.charCodeAt(i);
  }
  return output;
}

export function usePushNotifications() {
  /**
   * PWA 알림 권한을 요청하고 구독 정보를 백엔드에 등록한다.
   *
   * 호출 시점:
   *   - 로그인 성공 직후 (Sidebar → App.tsx의 user 상태 변화 감지)
   *   - 페이지 로드 시 (이미 로그인된 경우, 재구독은 UPSERT로 중복 무시)
   *
   * 실패 조건 (모두 조용히 처리):
   *   - 브라우저가 Notification / PushManager API를 지원하지 않는 경우
   *   - 사용자가 알림 권한을 거부한 경우
   *   - VAPID 공개 키 미설정 (개발 환경 등)
   *   - 네트워크 에러
   */
  const registerPush = useCallback(async (token: string): Promise<void> => {
    // ① 브라우저 지원 여부 확인
    if (
      !('Notification' in window) ||
      !('serviceWorker' in navigator) ||
      !('PushManager' in window)
    ) {
      console.log('[Push] 이 브라우저는 WebPush를 지원하지 않습니다.');
      return;
    }

    // ② 이미 거부된 경우: 재요청해도 의미 없으므로 즉시 종료
    if (Notification.permission === 'denied') {
      console.log('[Push] 알림 권한이 거부된 상태입니다.');
      return;
    }

    try {
      // ③ 알림 권한 요청 (이미 granted이면 팝업 없이 즉시 반환)
      const permission = await Notification.requestPermission();
      if (permission !== 'granted') {
        console.log('[Push] 알림 권한 미허용:', permission);
        return;
      }

      // ④ Service Worker 준비 대기
      const registration = await navigator.serviceWorker.ready;

      // ⑤ VAPID 공개 키 조회 (백엔드에서 동적으로 가져오기)
      const keyRes = await fetch('/api/vapid-public-key');
      if (!keyRes.ok) {
        console.warn('[Push] VAPID 공개 키 조회 실패 (status:', keyRes.status, ')');
        return;
      }
      const { publicKey }: { publicKey: string } = await keyRes.json();
      if (!publicKey) {
        console.warn('[Push] VAPID_PUBLIC_KEY 환경변수가 설정되지 않았습니다.');
        return;
      }

      // ⑥ PushManager 구독
      //    이미 구독 중이면 기존 구독 객체를 반환 (새 구독 생성 X)
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(publicKey),
      });

      // ⑦ 구독 정보를 백엔드에 저장 (UPSERT — 중복 호출 무해)
      const res = await fetch('/api/notifications/subscribe', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ subscription }),
      });

      if (res.ok) {
        console.log('[Push] 구독 등록 완료');
      } else {
        console.warn('[Push] 구독 저장 실패 (status:', res.status, ')');
      }
    } catch (err) {
      // 구독 실패는 기능상 치명적이지 않으므로 조용히 처리
      console.warn('[Push] 구독 등록 중 오류 (무시):', err);
    }
  }, []); // 외부 의존성 없음 — 안정적인 참조 보장

  return { registerPush };
}
