// useScheduleSystem.ts
import { useCallback } from 'react';

// ── Constants ──────
export const Category = {
  WED_REGULAR: 'WED_REGULAR',
  WED_GUEST: 'WED_GUEST',
  WED_LEFTOVER: 'WED_LEFTOVER',
  WED_LESSON: 'WED_LESSON',
  FRI_REGULAR: 'FRI_REGULAR',
  FRI_GUEST: 'FRI_GUEST',
  FRI_LEFTOVER: 'FRI_LEFTOVER',
} as const;
export type Category = typeof Category[keyof typeof Category];

export const Status = {
  BEFORE_OPEN: 'BEFORE_OPEN',
  OPEN: 'OPEN',
  CANCEL_ONLY: 'CANCEL_ONLY',
  CLOSED: 'CLOSED',
} as const;
export type Status = typeof Status[keyof typeof Status];

// ── Types ──────────────────────────────────────────────
export interface BoardEntry {
  user_id: string;
  name: string;
  type: string;
  timestamp: number;
  guest_name?: string;
}

interface ApplyOptions {
  guestName?: string;
}

export interface ApiResult {
  success: boolean;
  error?: string;
  data?: Record<string, unknown>;
}

// ── 공통 헬퍼: Authorization 헤더 ─────────────────────
function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('smash_token') ?? '';
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ── 백엔드 응답 → 프론트 Status 매핑 ─────────────────
const BACKEND_STATUS_MAP: Record<string, Status> = {
  BEFORE_OPEN: Status.BEFORE_OPEN,
  OPEN: Status.OPEN,
  CANCEL_ONLY: Status.CANCEL_ONLY,
  CLOSED: Status.CLOSED,
};

function toFrontendStatus(raw: string): Status {
  return BACKEND_STATUS_MAP[raw] ?? Status.CLOSED;
}

// ── API 헬퍼 (App.tsx에서 쓸 수 있도록 export 추가!) ─────
export async function fetchBoardData(category: Category): Promise<{
  status: Status;
  applications: BoardEntry[];
}> {
  const response = await fetch(`/api/board-data?category=${category}`);
  if (!response.ok) {
    throw new Error(`board-data 조회 실패: ${response.status}`);
  }
  const data = await response.json();
  return {
    status: toFrontendStatus(data.status),
    applications: data.applications ?? [],
  };
}

// ── Hook ───────────────────────────────────────────────
export function useScheduleSystem(category: Category) {
  // ⭐️ 상태(State) 및 폴링(useEffect) 로직 전면 제거

  const apply = useCallback(async (options?: ApplyOptions): Promise<ApiResult> => {
    try {
      const body: Record<string, string> = { category };
      if (options?.guestName) body.guest_name = options.guestName;

      const response = await fetch('/api/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        credentials: 'same-origin',
        body: JSON.stringify(body),
      });

      const data = await response.json();
      if (!response.ok) return { success: false, error: data.error ?? '신청에 실패했습니다.', data };

      return { success: true, data };
    } catch (err) {
      return { success: false, error: err instanceof Error ? err.message : '네트워크 오류' };
    }
  }, [category]);

  const cancel = useCallback(async (): Promise<ApiResult> => {
    try {
      const response = await fetch('/api/cancel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        credentials: 'same-origin',
        body: JSON.stringify({ category }),
      });

      const data = await response.json();
      if (!response.ok) return { success: false, error: data.error ?? '취소에 실패했습니다.', data };

      return { success: true, data };
    } catch (err) {
      return { success: false, error: err instanceof Error ? err.message : '네트워크 오류' };
    }
  }, [category]);

  const adminApply = useCallback(async (targetUserId: string, targetGuestName?: string): Promise<ApiResult> => {
    try {
      const body: Record<string, string> = { category, target_user_id: targetUserId };
      if (targetGuestName) body.target_guest_name = targetGuestName;

      const response = await fetch('/api/admin/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        credentials: 'same-origin',
        body: JSON.stringify(body),
      });

      const data = await response.json();
      if (!response.ok) return { success: false, error: data.error ?? data.message ?? '대리 신청에 실패했습니다.', data };

      return { success: true, data };
    } catch (err) {
      return { success: false, error: err instanceof Error ? err.message : '네트워크 오류' };
    }
  }, [category]);

  const adminCancel = useCallback(async (targetUserId: string): Promise<ApiResult> => {
    try {
      const response = await fetch('/api/admin/cancel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        credentials: 'same-origin',
        body: JSON.stringify({ category, target_user_id: targetUserId }),
      });

      const data = await response.json();
      if (!response.ok) return { success: false, error: data.error ?? data.message ?? '대리 취소에 실패했습니다.', data };

      return { success: true, data };
    } catch (err) {
      return { success: false, error: err instanceof Error ? err.message : '네트워크 오류' };
    }
  }, [category]);

  return { apply, cancel, adminApply, adminCancel };
}