import { Menu } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { DayType } from '@/types';

interface HeaderProps {
  semester: string;
  week: string;
  currentDay: DayType;
  onDayChange: (day: DayType) => void;
  onMenuClick: () => void;
}

const DAYS: DayType[] = ['수', '금'];

export function Header({
  semester,
  week,
  currentDay,
  onDayChange,
  onMenuClick,
}: HeaderProps) {
  return (
    <header className="sticky top-0 z-30 bg-white border-b shadow-sm">
      <div className="flex items-center justify-between px-4 h-14">
        <Button
          variant="ghost"
          size="icon"
          onClick={onMenuClick}
          aria-label="메뉴 열기"
        >
          <Menu className="size-5" />
        </Button>

        <h1 className="text-base font-medium">
          {semester}학기 {week}주차
        </h1>

        <div className="flex gap-1 rounded-lg bg-muted p-1">
          {DAYS.map((day) => (
            <button
              key={day}
              onClick={() => onDayChange(day)}
              className={cn(
                'px-3 py-1 rounded-md text-sm font-medium transition-colors',
                currentDay === day
                  ? 'bg-primary text-primary-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground',
              )}
            >
              {day}
            </button>
          ))}
        </div>
      </div>
    </header>
  );
}
