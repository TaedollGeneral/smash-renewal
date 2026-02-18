// useScheduleSystem.ts — scheduler_logic.py와 동일한 시간 규칙을 가진 프론트엔드 훅
import { useState, useEffect, useCallback } from 'react';

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

interface Transition {
  time: number; // ms timestamp
  status: Status;
}

export interface ScheduleState {
  status: Status;
  nextChangeText: string;
  isActive: boolean;
}

// ── KST 유틸리티 ───────────────────────────────────────

const KST_OFFSET_MS = 9 * 60 * 60 * 1000;

function getKSTNow(): Date {
  const now = new Date();
  const utcMs = now.getTime() + now.getTimezoneOffset() * 60 * 1000;
  return new Date(utcMs + KST_OFFSET_MS);
}

// ── 순수 로직 (scheduler_logic.py 미러) ────────────────

function getWeekStart(now: Date): Date {
  const daysSinceSaturday = (now.getDay() - 6 + 7) % 7;
  const result = new Date(now);
  result.setDate(result.getDate() - daysSinceSaturday);
  result.setHours(0, 0, 0, 0);
  return result;
}

const HOUR = 60 * 60 * 1000;
const MINUTE = 60 * 1000;
const DAY = 24 * HOUR;

function getTransitions(category: Category, weekStart: Date): Transition[] {
  const sat = weekStart.getTime();
  const transitions: Transition[] = [
    { time: sat, status: Status.BEFORE_OPEN },
  ];

  switch (category) {
    case Category.WED_REGULAR:
      transitions.push({ time: sat + 22 * HOUR, status: Status.OPEN });
      transitions.push({ time: sat + DAY + 10 * HOUR, status: Status.CANCEL_ONLY });
      transitions.push({ time: sat + 4 * DAY, status: Status.CLOSED });
      break;

    case Category.WED_GUEST:
      transitions.push({ time: sat + 22 * HOUR + MINUTE, status: Status.OPEN });
      transitions.push({ time: sat + 4 * DAY + 18 * HOUR, status: Status.CLOSED });
      break;

    case Category.WED_LEFTOVER:
      transitions.push({ time: sat + DAY + 22 * HOUR + MINUTE, status: Status.OPEN });
      transitions.push({ time: sat + 4 * DAY + 18 * HOUR, status: Status.CLOSED });
      break;

    case Category.WED_LESSON:
      transitions.push({ time: sat + DAY + 22 * HOUR, status: Status.OPEN });
      transitions.push({ time: sat + 4 * DAY + 18 * HOUR, status: Status.CLOSED });
      break;

    case Category.FRI_REGULAR:
      transitions.push({ time: sat + 22 * HOUR, status: Status.OPEN });
      transitions.push({ time: sat + DAY + 10 * HOUR, status: Status.CANCEL_ONLY });
      transitions.push({ time: sat + 6 * DAY, status: Status.CLOSED });
      break;

    case Category.FRI_GUEST:
      transitions.push({ time: sat + 22 * HOUR + MINUTE, status: Status.OPEN });
      transitions.push({ time: sat + 6 * DAY + 17 * HOUR, status: Status.CLOSED });
      break;

    case Category.FRI_LEFTOVER:
      transitions.push({ time: sat + DAY + 22 * HOUR + MINUTE, status: Status.OPEN });
      transitions.push({ time: sat + 6 * DAY + 17 * HOUR, status: Status.CLOSED });
      break;
  }

  return transitions;
}

function getCurrentStatus(category: Category, now: Date): Status {
  const weekStart = getWeekStart(now);
  const transitions = getTransitions(category, weekStart);
  const nowMs = now.getTime();

  let current: Status = Status.CLOSED;
  for (const t of transitions) {
    if (nowMs >= t.time) {
      current = t.status;
    } else {
      break;
    }
  }
  return current;
}

function getNextChange(category: Category, now: Date): { time: number; status: Status } {
  const weekStart = getWeekStart(now);
  const transitions = getTransitions(category, weekStart);
  const nowMs = now.getTime();

  for (const t of transitions) {
    if (nowMs < t.time) {
      return { time: t.time, status: t.status };
    }
  }

  return {
    time: weekStart.getTime() + 7 * DAY,
    status: Status.BEFORE_OPEN,
  };
}

// ── 포맷팅 ─────────────────────────────────────────────

const STATUS_LABEL: Record<Status, string> = {
  [Status.BEFORE_OPEN]: '오픈까지',
  [Status.OPEN]: '마감까지',
  [Status.CANCEL_ONLY]: '취소 마감까지',
  [Status.CLOSED]: '오픈까지',
};

function formatTimeLeft(diffMs: number): string {
  if (diffMs <= 0) return '00:00:00';

  const totalSeconds = Math.floor(diffMs / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  const hh = String(hours).padStart(2, '0');
  const mm = String(minutes).padStart(2, '0');
  const ss = String(seconds).padStart(2, '0');

  return `${hh}:${mm}:${ss}`;
}

// ── Hook ───────────────────────────────────────────────

export function useScheduleSystem(category: Category): ScheduleState {
  const computeState = useCallback((): ScheduleState => {
    const now = getKSTNow();
    const status = getCurrentStatus(category, now);
    const next = getNextChange(category, now);

    const diffMs = next.time - now.getTime();
    const timeLeft = formatTimeLeft(diffMs);
    const label = STATUS_LABEL[status];

    return {
      status,
      nextChangeText: `${label} ${timeLeft} 남음`,
      isActive: status === Status.OPEN || status === Status.CANCEL_ONLY,
    };
  }, [category]);

  const [state, setState] = useState<ScheduleState>(computeState);

  useEffect(() => {
    const interval = setInterval(() => {
      setState(computeState());
    }, 1000);

    setState(computeState());

    return () => clearInterval(interval);
  }, [computeState]);

  return state;
}
