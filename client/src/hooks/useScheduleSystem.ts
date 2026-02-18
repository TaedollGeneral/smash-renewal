// useScheduleSystem.ts — scheduler_logic.py와 동일한 시간 규칙을 가진 프론트엔드 훅
import { useState, useEffect, useCallback } from 'react';

// ── Enums ──────────────────────────────────────────────

export enum Category {
  WED_REGULAR = 'WED_REGULAR',
  WED_GUEST = 'WED_GUEST',
  WED_LEFTOVER = 'WED_LEFTOVER',
  WED_LESSON = 'WED_LESSON',
  FRI_REGULAR = 'FRI_REGULAR',
  FRI_GUEST = 'FRI_GUEST',
  FRI_LEFTOVER = 'FRI_LEFTOVER',
}

export enum Status {
  BEFORE_OPEN = 'BEFORE_OPEN',
  OPEN = 'OPEN',
  CANCEL_ONLY = 'CANCEL_ONLY',
  CLOSED = 'CLOSED',
}

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

/**
 * 현재 시각의 KST Date 객체를 반환한다.
 * 브라우저 타임존과 무관하게 getHours()/getDay() 등이 KST 값을 반환하도록
 * UTC 기준으로 오프셋을 적용한 Date를 생성한다.
 */
function getKSTNow(): Date {
  const now = new Date();
  const utcMs = now.getTime() + now.getTimezoneOffset() * 60 * 1000;
  return new Date(utcMs + KST_OFFSET_MS);
}

// ── 순수 로직 (scheduler_logic.py 미러) ────────────────

/**
 * 가장 최근 토요일 00:00:00 (KST Date) 을 반환한다.
 * JS getDay(): Sun=0, Mon=1, … Sat=6
 */
function getWeekStart(now: Date): Date {
  const daysSinceSaturday = (now.getDay() - 6 + 7) % 7;
  const result = new Date(now);
  result.setDate(result.getDate() - daysSinceSaturday);
  result.setHours(0, 0, 0, 0);
  return result;
}

/** ms 단위 헬퍼 */
const HOUR = 60 * 60 * 1000;
const MINUTE = 60 * 1000;
const DAY = 24 * HOUR;

/**
 * 카테고리별 상태 전환 타임라인을 반환한다.
 * scheduler_logic.py의 _get_transitions와 동일한 규칙.
 *
 * 시간 규칙 (KST):
 * 토 00:00  ALL           -> BEFORE_OPEN
 * 토 22:00  수/금 운동     -> OPEN
 * 토 22:01  수/금 게스트    -> OPEN
 * 일 10:00  수/금 운동     -> CANCEL_ONLY
 * 일 22:00  수 레슨        -> OPEN
 * 일 22:01  수/금 잔여석    -> OPEN
 * 수 00:00  수 운동        -> CLOSED
 * 수 18:00  수 게스트/잔여/레슨 -> CLOSED
 * 금 00:00  금 운동        -> CLOSED
 * 금 17:00  금 게스트/잔여  -> CLOSED
 */
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

/** 현재 상태를 반환한다. */
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

/** 다음 상태 변경 시각(ms)과 변경될 상태를 반환한다. */
function getNextChange(category: Category, now: Date): { time: number; status: Status } {
  const weekStart = getWeekStart(now);
  const transitions = getTransitions(category, weekStart);
  const nowMs = now.getTime();

  for (const t of transitions) {
    if (nowMs < t.time) {
      return { time: t.time, status: t.status };
    }
  }

  // 이번 주 전환이 모두 지남 → 다음 주 토요일 00:00
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
    // targetTime - currentTime 방식으로 매초 갱신하여 타이머 오차 방지
    const interval = setInterval(() => {
      setState(computeState());
    }, 1000);

    // 카테고리 변경 시 즉시 갱신
    setState(computeState());

    return () => clearInterval(interval);
  }, [computeState]);

  return state;
}
