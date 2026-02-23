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

export interface GuestCapacity {
  limit: number;
  special_count: number;
}

export interface CapacityDetails {
  운동: number;
  게스트: GuestCapacity;
  잔여석: number;
}

export interface CapacityDay {
  total: number;
  details: CapacityDetails;
}

export interface Capacity {
  수: CapacityDay | null;
  금: CapacityDay | null;
}

export interface CategoryState {
  status: StatusType;
  statusText: string;
  deadlineTimestamp: number; // Unix ms timestamp
}

// /api/notifications/status 응답 형태
export interface NotifStatus {
  wed_confirmed: boolean;  // 수요일 정원 확정 여부
  fri_confirmed: boolean;  // 금요일 정원 확정 여부
  prefs: {
    wed: boolean;          // 본인 수요일 알림 설정
    fri: boolean;          // 본인 금요일 알림 설정
  };
}
