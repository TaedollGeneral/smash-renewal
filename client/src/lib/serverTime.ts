// serverTime.ts — 서버-클라이언트 시계 오차 보정 모듈
//
// 문제: deadlineTimestamp는 서버 시간 기준 Unix ms이고,
//       Date.now()는 클라이언트(핸드폰) 시간 기준이다.
//       시계가 빠른 기기는 카운트다운이 일찍 0이 되고,
//       느린 기기는 늦게 0이 된다.
//
// 해결: /api/category-states 응답의 serverTime 필드로 오프셋을 계산하고,
//       카운트다운 계산에 Date.now() 대신 serverNow()를 사용한다.
//
// 정확도: RTT/2 ≈ ±25~100ms (NTP 방식)
//
// 사용법:
//   updateServerTimeOffset(data.serverTime);  // fetchCategoryStates 응답 수신 시
//   const remaining = deadlineTimestamp - serverNow();  // 카운트다운 계산 시

let _offset = 0; // ms. 양수: 서버가 클라이언트보다 빠름, 음수: 반대

/**
 * 서버 시각으로 오프셋을 갱신한다.
 * /api/category-states 응답의 serverTime(Unix ms)을 받아 계산한다.
 *
 * @param serverTimeMs - 서버의 현재 Unix ms
 */
export function updateServerTimeOffset(serverTimeMs: number): void {
  _offset = serverTimeMs - Date.now();
}

/**
 * 서버 기준 현재 시각 (Unix ms).
 * 카운트다운 계산 시 Date.now() 대신 이 함수를 사용한다.
 */
export function serverNow(): number {
  return Date.now() + _offset;
}
