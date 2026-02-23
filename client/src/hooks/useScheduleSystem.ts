// useScheduleSystem.ts — 백엔드 API 폴링 기반 스케줄 훅
import { useState, useEffect, useCallback, useRef } from 'react';

// ── Constants (enum 대체 — erasableSyntaxOnly 호환) ──────

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
  type: string;        // "member" | "guest" 등
  timestamp: number;   // Unix seconds (float)
  guest_name?: string; // 게스트/잔여석 신청 시 입력된 이름
}

export interface ScheduleState {
  status: Status;
  applications: BoardEntry[];
  isActive: boolean;
  isLoading: boolean;
  error: string | null;
}

/**
 * 일반 신청 옵션.
 * 게스트/잔여석 카테고리에서 본인 신청 시 게시판에 표시될 이름만 추가로 전달.
 * target_user_id 는 관리자 대리 전용이므로 여기서 제거됨.
 */
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

// ── API 헬퍼 ──────────────────────────────────────────

async function fetchBoardData(category: Category): Promise<{
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

const POLL_INTERVAL = 2000; // 2초

export function useScheduleSystem(category: Category) {
  const [state, setState] = useState<ScheduleState>({
    status: Status.CLOSED,
    applications: [],
    isActive: false,
    isLoading: true,
    error: null,
  });

  // 언마운트 후 setState 호출 방지
  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  // ── 폴링 (GET /api/board-data) ──────────────────────
  const poll = useCallback(async () => {
    try {
      const { status, applications } = await fetchBoardData(category);
      if (!mountedRef.current) return;
      setState({
        status,
        applications,
        isActive: status === Status.OPEN || status === Status.CANCEL_ONLY,
        isLoading: false,
        error: null,
      });
    } catch (err) {
      if (!mountedRef.current) return;
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: err instanceof Error ? err.message : '알 수 없는 오류',
      }));
    }
  }, [category]);

  useEffect(() => {
    // 마운트 즉시 1회 호출 + 2초 인터벌
    poll();
    const id = setInterval(poll, POLL_INTERVAL);
    return () => clearInterval(id);
  }, [poll]);

  // ── apply (POST /apply) ─────────────────────────────
  // 일반 회원 본인 신청 전용.
  // Body: { category, guest_name? }  — target_user_id 는 관리자 전용 엔드포인트로 분리.
  const apply = useCallback(
    async (options?: ApplyOptions): Promise<ApiResult> => {
      try {
        const body: Record<string, string> = { category };
        if (options?.guestName) {
          body.guest_name = options.guestName;
        }

        const response = await fetch('/api/apply', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...authHeaders() },
          credentials: 'same-origin',
          body: JSON.stringify(body),
        });

        const data = await response.json();
        if (!response.ok) {
          return { success: false, error: data.error ?? '신청에 실패했습니다.', data };
        }

        await poll();
        return { success: true, data };
      } catch (err) {
        return { success: false, error: err instanceof Error ? err.message : '네트워크 오류' };
      }
    },
    [category, poll],
  );

  // ── cancel (POST /cancel) ───────────────────────────
  // 일반 회원 본인 취소 전용.
  // Body: { category }  — 취소 대상은 백엔드가 토큰으로 식별.
  const cancel = useCallback(
    async (): Promise<ApiResult> => {
      try {
        const response = await fetch('/api/cancel', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...authHeaders() },
          credentials: 'same-origin',
          body: JSON.stringify({ category }),
        });

        const data = await response.json();
        if (!response.ok) {
          return { success: false, error: data.error ?? '취소에 실패했습니다.', data };
        }

        await poll();
        return { success: true, data };
      } catch (err) {
        return { success: false, error: err instanceof Error ? err.message : '네트워크 오류' };
      }
    },
    [category, poll],
  );

  // ── adminApply (POST /admin/apply) ──────────────────
  // 관리자 대리 신청 전용.
  // Body: { category, target_user_id, target_guest_name? }
  //   - target_guest_name 은 게스트/잔여석 신청 시 두 번째 인풋에서 받은 값만 포함.
  const adminApply = useCallback(
    async (targetUserId: string, targetGuestName?: string): Promise<ApiResult> => {
      try {
        const body: Record<string, string> = { category, target_user_id: targetUserId };
        if (targetGuestName) {
          body.target_guest_name = targetGuestName;
        }

        const response = await fetch('/api/admin/apply', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...authHeaders() },
          credentials: 'same-origin',
          body: JSON.stringify(body),
        });

        const data = await response.json();
        if (!response.ok) {
          return { success: false, error: data.error ?? data.message ?? '대리 신청에 실패했습니다.', data };
        }

        await poll();
        return { success: true, data };
      } catch (err) {
        return { success: false, error: err instanceof Error ? err.message : '네트워크 오류' };
      }
    },
    [category, poll],
  );

  // ── adminCancel (POST /admin/cancel) ────────────────
  // 관리자 대리 취소 전용.
  // Body: { category, target_user_id }
  //   - 이름 조회는 백엔드 DB에서 처리하므로 프론트엔드는 ID만 전달.
  const adminCancel = useCallback(
    async (targetUserId: string): Promise<ApiResult> => {
      try {
        const response = await fetch('/api/admin/cancel', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...authHeaders() },
          credentials: 'same-origin',
          body: JSON.stringify({ category, target_user_id: targetUserId }),
        });

        const data = await response.json();
        if (!response.ok) {
          return { success: false, error: data.error ?? data.message ?? '대리 취소에 실패했습니다.', data };
        }

        await poll();
        return { success: true, data };
      } catch (err) {
        return { success: false, error: err instanceof Error ? err.message : '네트워크 오류' };
      }
    },
    [category, poll],
  );

  return { ...state, apply, cancel, adminApply, adminCancel };
}
