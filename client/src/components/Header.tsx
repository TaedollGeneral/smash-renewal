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
    <header className="bg-[#EAEAEA] shadow-md px-4 py-3 z-40 pt-[max(12px,env(safe-area-inset-top))] border-b border-[#C8C8C8]">
      <div className="flex items-center justify-between">
        {/* Left: Menu Icon */}
        <button
          onClick={onMenuClick}
          className="p-2 -ml-2 hover:bg-[#C0D6DB]/40 rounded-lg transition-colors"
        >
          <Menu className="w-6 h-6 text-[#4F6D7A]" />
        </button>

        {/* Center: Title + Dates */}
        <div className="flex-1 mx-4">
          <h1 className="font-bold text-lg text-[#4F6D7A]">2026 SMASH</h1>
          <p className="text-sm text-[#4F6D7A]">
            {formatDate(wed)} &middot; {formatDate(fri)}
          </p>
        </div>

        {/* User Info (if logged in) */}
        {user && (
          <div className="flex flex-col items-end mr-3">
            <span className="text-sm font-bold text-[#4F6D7A]">{user.name}</span>
            <span className="text-xs text-[#4F6D7A]">{user.role}</span>
          </div>
        )}

        {/* Right: Day Switch */}
        <div className="relative flex items-center bg-[#C0D6DB]/40 rounded-lg p-0.5">
          <div
            className={`absolute w-10 h-10 bg-[#C0D6DB] rounded-md shadow-md transition-transform duration-300 ease-out ${
              currentDay === '수' ? 'translate-x-0' : 'translate-x-[42px]'
            }`}
          />
          <button
            onClick={() => onDayChange('수')}
            className={`relative z-10 w-10 h-10 rounded-md text-sm font-bold transition-colors duration-300 ${
              currentDay === '수' ? 'text-[#4F6D7A]' : 'text-[#4F6D7A]/60 hover:text-[#4F6D7A]'
            }`}
          >
            수
          </button>
          <button
            onClick={() => onDayChange('금')}
            className={`relative z-10 w-10 h-10 rounded-md text-sm font-bold transition-colors duration-300 ${
              currentDay === '금' ? 'text-[#4F6D7A]' : 'text-[#4F6D7A]/60 hover:text-[#4F6D7A]'
            }`}
          >
            금
          </button>
        </div>
      </div>
    </header>
  );
}
