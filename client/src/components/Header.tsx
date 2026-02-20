import { Menu } from 'lucide-react';
import type { DayType, User } from '@/types';

interface HeaderProps {
  currentDay: DayType;
  onDayChange: (day: DayType) => void;
  onMenuClick: () => void;
  user: User | null;
}

// 직전 토요일 기준 +4일(수요일), +6일(금요일) 계산
function getUpcomingWedFri(): { wed: Date; fri: Date } {
  const today = new Date();

  // 직전 토요일 구하기 (오늘이 토요일이면 오늘 사용)
  const daysBackToSat = (today.getDay() - 6 + 7) % 7;
  const sat = new Date(today);
  sat.setDate(today.getDate() - daysBackToSat);

  // 토요일 기준 +4일 = 수요일, +6일 = 금요일
  const wed = new Date(sat);
  wed.setDate(sat.getDate() + 4);

  const fri = new Date(sat);
  fri.setDate(sat.getDate() + 6);

  return { wed, fri };
}

function formatDate(date: Date): string {
  const m = date.getMonth() + 1;
  const d = date.getDate();
  const dayNames = ['일', '월', '화', '수', '목', '금', '토'];
  return `${m}/${d}(${dayNames[date.getDay()]})`;
}

export function Header({ currentDay, onDayChange, onMenuClick, user }: HeaderProps) {
  const { wed, fri } = getUpcomingWedFri();

  return (
    <header className="bg-[#1C5D99] shadow-md px-4 py-3 z-40 pt-[max(12px,env(safe-area-inset-top))]">
      <div className="flex items-center justify-between">
        {/* Left: Menu Icon */}
        <button
          onClick={onMenuClick}
          className="p-2 -ml-3 hover:bg-white/20 rounded-lg transition-colors"
        >
          <Menu className="w-6 h-6 text-white" />
        </button>

        {/* Center: Title + Dates */}
        <div className="flex-1 mx-1">
          <h1
            className="font-bold text-[16px] text-white"
            style={{
              textShadow: '0 0 8px rgba(0, 0, 0, 0.3)'
            }}
          >2026 SMASH</h1>
          <p className="text-[11px] text-white">
            {formatDate(wed)} &middot; {formatDate(fri)}
          </p>
        </div>

        {/* User Info (if logged in) */}
        {user && (
          <div className="flex flex-col items-end mr-3">
            <span className="text-sm font-bold text-white">{user.name}</span>
            <span className="text-xs text-white/90">{user.role}</span>
          </div>
        )}

        {/* Right: Day Switch */}
        <div className="relative flex items-center bg-white/20 rounded-lg p-0.5">
          <div
            className={`absolute w-10 h-10 bg-white rounded-md shadow-md transition-transform duration-300 ease-out ${currentDay === '수' ? 'translate-x-0' : 'translate-x-[42px]'
              }`}
          />
          <button
            onClick={() => onDayChange('수')}
            className={`relative z-10 w-10 h-10 rounded-md text-sm font-bold transition-colors duration-300 ${currentDay === '수' ? 'text-black' : 'text-white/80 hover:text-white'
              }`}
          >
            수
          </button>
          <button
            onClick={() => onDayChange('금')}
            className={`relative z-10 w-10 h-10 rounded-md text-sm font-bold transition-colors duration-300 ${currentDay === '금' ? 'text-black' : 'text-white/80 hover:text-white'
              }`}
          >
            금
          </button>
        </div>
      </div>
      {/* --- 양 끝이 둥근 하단 구분선 (색상 및 두께 유지) --- */}
      <div className="absolute bottom-0 left-0 right-0 px-4">
        {/* h-[1px]로 두께 유지, bg-[#2C6DB0]로 색상 유지, rounded-full로 끝부분 처리 */}
        <div className="h-[1px] w-full bg-[#2C6DB0] rounded-full" />
      </div>
    </header>
  );
}
