// useScheduleSystem.ts
import { useCallback } from 'react';
import { fetchWithAuth } from '@/lib/fetchWithAuth';

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

// ── 토큰 유무 확인 헬퍼 ────────────────────────────────
function getToken(): string | null {
  return localStorage.getItem('smash_token');
}

// ── API 헬퍼 (App.tsx에서 쓸 수 있도록 export 추가!) ─────
export async function fetchBoardData(category: Category): Promise<{
  status: Status;
  applications: BoardEntry[];
}> {
  const token = getToken();
  if (!token) throw new Error('로그인이 필요합니다.');

  const response = await fetchWithAuth(`/api/board-data?category=${category}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    throw new Error(`board-data 조회 실패: ${response.status}`);
  }
  const data = await response.json();
  return {
    status: toFrontendStatus(data.status),
    applications: data.applications ?? [],
  };
}

export interface AllBoardData {
  applications: Record<string, BoardEntry[]>;
  userApplied: Record<string, boolean>;
  overloaded?: boolean;
}

/**
 * 전체 카테고리 현황을 1회 요청으로 가져온다.
 * 기존 7개 개별 요청(fetchBoardData × 7)을 대체하여 서버 부하를 ~85% 감소시킨다.
 * user_already_applied: 이번 주 해당 카테고리 신청 여부 (UNIQUE_APPLY_CATEGORIES만 true 가능)
 */
export async function fetchAllBoardData(): Promise<AllBoardData> {
  const token = getToken();
  if (!token) throw new Error('로그인이 필요합니다.');

  const response = await fetchWithAuth('/api/all-boards', {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    throw new Error(`all-boards 조회 실패: ${response.status}`);
  }
  const data = await response.json();

  // 서킷 브레이커: 과부하 시 서버가 {overloaded: true, message: "..."} 반환
  if (data.overloaded) {
    return { applications: {}, userApplied: {}, overloaded: true };
  }

  const typed = data as Record<string, { status: string; applications: BoardEntry[]; user_already_applied: boolean }>;
  const applications: Record<string, BoardEntry[]> = {};
  const userApplied: Record<string, boolean> = {};
  for (const [cat, value] of Object.entries(typed)) {
    applications[cat] = value.applications ?? [];
    userApplied[cat] = value.user_already_applied ?? false;
  }
  return { applications, userApplied };
}

// ── Hook ───────────────────────────────────────────────
export function useScheduleSystem(category: Category) {
  // ⭐️ 상태(State) 및 폴링(useEffect) 로직 전면 제거

  const apply = useCallback(async (options?: ApplyOptions): Promise<ApiResult> => {
    try {
      const body: Record<string, string> = { category };
      if (options?.guestName) body.guest_name = options.guestName;

      const response = await fetchWithAuth('/api/apply', {
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

  const cancel = useCallback(async (options?: { guestName?: string }): Promise<ApiResult> => {
    try {
      const body: Record<string, string> = { category };
      if (options?.guestName) body.guest_name = options.guestName;

      const response = await fetchWithAuth('/api/cancel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        credentials: 'same-origin',
        body: JSON.stringify(body),
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

      const response = await fetchWithAuth('/api/admin/apply', {
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

  const adminCancel = useCallback(async (targetUserId: string, targetGuestName?: string): Promise<ApiResult> => {
    try {
      const body: Record<string, string> = { category, target_user_id: targetUserId };
      if (targetGuestName) body.target_guest_name = targetGuestName;

      const response = await fetchWithAuth('/api/admin/cancel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        credentials: 'same-origin',
        body: JSON.stringify(body),
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