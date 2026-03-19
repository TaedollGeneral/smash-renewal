/**
 * fetchWithAuth — 401 응답 시 자동 로그아웃 래퍼
 *
 * 서버에서 401(Unauthorized)을 반환하면 'auth:logout' 커스텀 이벤트를 dispatch한다.
 * App.tsx에서 이 이벤트를 수신하여 localStorage 초기화 + setUser(null)를 처리한다.
 *
 * 사용법: 기존 fetch()와 동일한 시그니처로 대체하기만 하면 됨.
 * 반환값: 원본 Response 객체 그대로 반환 (호출부에서 .ok, .json() 등 동일하게 사용 가능)
 */
export async function fetchWithAuth(
  url: string | URL | Request,
  options?: RequestInit,
): Promise<Response> {
  const response = await fetch(url, options);
  if (response.status === 401) {
    window.dispatchEvent(new CustomEvent('auth:logout'));
  }
  return response;
}
