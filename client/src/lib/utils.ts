import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// ── KST 타임스탬프 포맷팅 ─────────────────────────────

const KST_OFFSET_MS = 9 * 60 * 60 * 1000;
const DAY_LABELS = ['일', '월', '화', '수', '목', '금', '토'] as const;

/**
 * 밀리초(ms) 타임스탬프를 KST 기준 `요일 HH:mm:ss.cs` 형태로 변환한다.
 *
 * @param timestampMs - Unix 밀리초 타임스탬프 (예: 1716301234560)
 * @returns 포맷된 문자열 (예: "토 22:00:00.54")
 *
 * @example
 * formatTimestamp(1716301234560) // → "토 22:00:00.56"
 */
export function formatTimestamp(timestampMs: number): string {
  // UTC → KST 변환
  const kstDate = new Date(timestampMs + KST_OFFSET_MS);

  const day = DAY_LABELS[kstDate.getUTCDay()];
  const hh = String(kstDate.getUTCHours()).padStart(2, '0');
  const mm = String(kstDate.getUTCMinutes()).padStart(2, '0');
  const ss = String(kstDate.getUTCSeconds()).padStart(2, '0');
  // 밀리초 → 센티초(hundredths) 2자리
  const cs = String(Math.floor(kstDate.getUTCMilliseconds() / 10)).padStart(2, '0');

  return `${day} ${hh}:${mm}:${ss}.${cs}`;
}
