import { Menu } from 'lucide-react';
import type { DayType, User } from '@/types';

interface HeaderProps {
  currentDay: DayType;
  onDayChange: (day: DayType) => void;
  onMenuClick: () => void;
  user: User | null;
}

export function Header({ currentDay, onDayChange, onMenuClick, user }: HeaderProps) {
  return (
    <header className="bg-gray-50 shadow-md px-4 py-3 z-40 pt-[max(12px,env(safe-area-inset-top))] border-b border-gray-300">
      <div className="flex items-center justify-between">
        {/* Left: Menu Icon */}
        <button
          onClick={onMenuClick}
          className="p-2 -ml-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <Menu className="w-6 h-6 text-gray-700" />
        </button>

        {/* Center: Title */}
        <div className="flex-1 mx-4">
          <h1 className="font-bold text-lg text-gray-900">2026 SMASH</h1>
        </div>

        {/* User Info (if logged in) */}
        {user && (
          <div className="flex flex-col items-end mr-3">
            <span className="text-sm font-bold text-gray-900">{user.name}</span>
            <span className="text-xs text-gray-500">{user.role}</span>
          </div>
        )}

        {/* Right: Day Switch */}
        <div className="relative flex items-center bg-gray-200 rounded-lg p-0.5">
          {/* Sliding Background */}
          <div
            className={`absolute w-10 h-10 bg-gray-700 rounded-md shadow-md transition-transform duration-300 ease-out ${
              currentDay === '수' ? 'translate-x-0' : 'translate-x-[42px]'
            }`}
          />

          <button
            onClick={() => onDayChange('수')}
            className={`relative z-10 w-10 h-10 rounded-md text-sm font-bold transition-colors duration-300 ${
              currentDay === '수'
                ? 'text-white'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            수
          </button>
          <button
            onClick={() => onDayChange('금')}
            className={`relative z-10 w-10 h-10 rounded-md text-sm font-bold transition-colors duration-300 ${
              currentDay === '금'
                ? 'text-white'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            금
          </button>
        </div>
      </div>
    </header>
  );
}
