export type DayType = '수' | '금';

export type BoardType = '운동' | '잔여석' | '게스트' | '레슨';

export type ActionType = '신청' | '취소';

export interface User {
  name: string;
  role: string;
}
