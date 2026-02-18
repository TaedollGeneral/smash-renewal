export type DayType = '수' | '금';

export type BoardType = '운동' | '잔여석' | '게스트' | '레슨';

export type ActionType = '신청' | '취소';

export type StatusType = 'before-open' | 'open' | 'cancel-period' | 'waiting';

export interface User {
  id: string;
  name: string;
  role: string;
  token: string;
}

export interface Capacity {
  수?: number;
  금?: number;
}

export interface CategoryState {
  status: StatusType;
  statusText: string;
  deadlineTimestamp: number; // Unix ms timestamp
}
