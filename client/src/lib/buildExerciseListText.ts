import type { BoardEntry } from '@/hooks/useScheduleSystem';
import type { Capacity } from '@/types';

type DayType = '수' | '금';

// 이번 주기의 수요일 또는 금요일 날짜 계산
// 주간 리셋 기준: 토요일(6) 00:00 KST
// 토요일 이전(일~금)이고 targetDay가 이미 지났으면 이번 주(과거) 날짜 반환
function getSessionDate(dayType: DayType): Date {
  const today = new Date();
  const targetDay = dayType === '수' ? 3 : 5; // 0=Sun … 3=Wed, 5=Fri
  const currentDay = today.getDay();
  let daysUntil = (targetDay - currentDay + 7) % 7;

  // 토요일(6) 리셋 전이고 targetDay가 이미 지난 경우 → 이번 주 날짜 사용
  // (예: 금요일에 수요일 명단 → 이번 주 수요일)
  if (daysUntil !== 0 && currentDay !== 6 && currentDay > targetDay) {
    daysUntil -= 7;
  }

  const result = new Date(today);
  result.setDate(today.getDate() + daysUntil);
  return result;
}

// 영어 이름 판별 (알파벳으로 시작하는 경우)
function isEnglishName(name: string): boolean {
  return /^[A-Za-z]/.test(name);
}

// 2글자 한국어 이름은 공백 1칸 추가 (세로 정렬)
function formatName(name: string): string {
  if (!isEnglishName(name) && name.length === 2) {
    return name + ' ';
  }
  return name;
}

// 배열을 chunkSize 개씩 나눠 줄바꿈으로 연결
function chunkJoin(names: string[], chunkSize: number): string {
  const lines: string[] = [];
  for (let i = 0; i < names.length; i += chunkSize) {
    lines.push(names.slice(i, i + chunkSize).join(' '));
  }
  return lines.join('\n');
}

const CATEGORY_KEYS: Record<DayType, { regular: string; guest: string; leftover: string }> = {
  수: { regular: 'WED_REGULAR', guest: 'WED_GUEST', leftover: 'WED_LEFTOVER' },
  금: { regular: 'FRI_REGULAR', guest: 'FRI_GUEST', leftover: 'FRI_LEFTOVER' },
};

// 하드코딩된 임원진 텍스트
const EXECUTIVE_TEXT = `김세진 김정림 김태우 박승우 정시윤
최혜민`;

export function buildExerciseListText(
  dayType: DayType,
  allApplications: Record<string, BoardEntry[]>,
  capacities: Capacity,
): string {
  const sessionDate = getSessionDate(dayType);
  const month = sessionDate.getMonth() + 1;
  const day = sessionDate.getDate();
  const dayLabel = dayType === '수' ? '수요일' : '금요일';

  const cap = capacities[dayType];
  const { regular: regularKey, guest: guestKey, leftover: leftoverKey } = CATEGORY_KEYS[dayType];

  const regularEntries = allApplications[regularKey] ?? [];
  const guestEntries = allApplications[guestKey] ?? [];
  const leftoverEntries = allApplications[leftoverKey] ?? [];

  // ── 1. 운동 명단 ─────────────────────────────────────────────────────────────
  // 초록색 표시 기준: index < 정원(운동)
  const regularCapacity = cap?.details?.운동 ?? 0;
  const greenRegular = regularEntries.slice(0, regularCapacity);

  // 한국어 이름 가나다순 → 영어 이름 마지막
  const koreanRegular = greenRegular.filter((e) => !isEnglishName(e.name));
  const englishRegular = greenRegular.filter((e) => isEnglishName(e.name));
  koreanRegular.sort((a, b) => a.name.localeCompare(b.name, 'ko'));
  englishRegular.sort((a, b) => a.name.localeCompare(b.name, 'en'));

  const regularNames = [...koreanRegular, ...englishRegular].map((e) => formatName(e.name));
  const regularBlock = chunkJoin(regularNames, 5);

  // ── 2. 게스트 명단 ───────────────────────────────────────────────────────────
  // 초록색 표시 기준: index < (limit + special_count)
  const guestCap = cap?.details?.게스트;
  const guestCapacity = guestCap != null ? guestCap.limit + guestCap.special_count : 0;
  const greenGuests = guestEntries.slice(0, guestCapacity);

  // ob → 교류전 → 나머지 순으로 분리 후 각각 가나다순 정렬
  const obGuests = greenGuests.filter((e) => e.guest_name?.includes('(ob)'));
  const gyoryuGuests = greenGuests.filter((e) => e.guest_name?.includes('(교류전)'));
  const regularGuests = greenGuests.filter(
    (e) => !e.guest_name?.includes('(ob)') && !e.guest_name?.includes('(교류전)'),
  );

  obGuests.sort((a, b) => (a.guest_name ?? '').localeCompare(b.guest_name ?? '', 'ko'));
  gyoryuGuests.sort((a, b) => (a.guest_name ?? '').localeCompare(b.guest_name ?? '', 'ko'));
  regularGuests.sort((a, b) => (a.guest_name ?? '').localeCompare(b.guest_name ?? '', 'ko'));

  const guestNames = [
    ...obGuests.map((e) => e.guest_name ?? ''),
    ...gyoryuGuests.map((e) => e.guest_name ?? ''),
    ...regularGuests.map((e) => e.guest_name ?? ''),
  ].filter(Boolean);
  const guestBlock = chunkJoin(guestNames, 5);

  // ── 3. 잔여석 명단 ───────────────────────────────────────────────────────────
  // 초록색 표시 기준: index < 정원(잔여석)
  // 참여인원 컬럼(guest_name) 사용 (신청자 컬럼 아님)
  const leftoverCapacity = cap?.details?.잔여석 ?? 0;
  const greenLeftover = leftoverEntries.slice(0, leftoverCapacity).filter((e) => e.guest_name);

  greenLeftover.sort((a, b) => (a.guest_name ?? '').localeCompare(b.guest_name ?? '', 'ko'));
  const leftoverNames = greenLeftover.map((e) => formatName(e.guest_name ?? ''));
  const leftoverBlock = chunkJoin(leftoverNames, 5);

  // ── 텍스트 조합 ─────────────────────────────────────────────────────────────
  const lines: string[] = [];

  lines.push(`📌 ${month}/${day} ${dayLabel} 정기운동`);
  lines.push('');
  if (regularBlock) lines.push(regularBlock);

  lines.push('');
  lines.push('📍임원진');
  lines.push(EXECUTIVE_TEXT);

  if (guestBlock) {
    lines.push('');
    lines.push('📍게스트');
    lines.push(guestBlock);
  }

  if (leftoverBlock) {
    lines.push('');
    lines.push('➕ 잔여석');
    lines.push(leftoverBlock);
  }

  return lines.join('\n');
}
