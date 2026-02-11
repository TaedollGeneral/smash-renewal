import { ChevronDown } from 'lucide-react';
import { useState, useEffect } from 'react';
import { BoardTable } from './BoardTable';
import type { BoardType } from '@/types';

// 각 게시판 타입에 맞는 이모티콘
const boardIcons: Record<BoardType, string> = {
  '운동': '🏸',
  '게스트': '👥',
  '레슨': '🎓',
  '잔여석': '🪑',
};

interface AccordionPanelProps {
  title: BoardType;
  isExpanded: boolean;
  onToggle: () => void;
  deadline: string; // HH:MM:SS format
  data: any[]; // eslint-disable-line @typescript-eslint/no-explicit-any
}

export function AccordionPanel({ title, deadline, isExpanded, onToggle, data }: AccordionPanelProps) {
  const [countdown, setCountdown] = useState(deadline);

  // deadline에서 "HH:MM" 형식 추출하여 표시용으로 사용
  const deadlineDisplay = deadline.substring(0, 5);

  useEffect(() => {
    const calculateCountdown = () => {
      const now = new Date();
      const [dH, dM, dS] = deadline.split(':').map(Number);
      const target = new Date(now);
      target.setHours(dH, dM, dS, 0);

      const diff = target.getTime() - now.getTime();
      if (diff <= 0) {
        return '00:00:00';
      }

      const totalSeconds = Math.floor(diff / 1000);
      const hours = String(Math.floor(totalSeconds / 3600)).padStart(2, '0');
      const minutes = String(Math.floor((totalSeconds % 3600) / 60)).padStart(2, '0');
      const seconds = String(totalSeconds % 60).padStart(2, '0');
      return `${hours}:${minutes}:${seconds}`;
    };

    setCountdown(calculateCountdown());
    const interval = setInterval(() => {
      setCountdown(calculateCountdown());
    }, 1000);

    return () => clearInterval(interval);
  }, [deadline]);

  return (
    <div className="border-b border-gray-300 bg-gray-50">
      {/* Accordion Header */}
      <button
        onClick={onToggle}
        className="w-full px-2 py-2.5 flex items-center justify-between hover:bg-gray-100 transition-colors"
      >
        {/* Left: Icon + Title */}
        <div className="flex items-center gap-2">
          <span className="text-lg">{boardIcons[title]}</span>
          <span className="font-semibold text-sm text-gray-900">{title}</span>
        </div>

        {/* Right: Countdown and Icon */}
        <div className="flex items-center gap-2">
          {/* Divider and Countdown */}
          <div className="flex items-center gap-2">
            <div className="w-px h-8 bg-gray-300" />
            <div className="flex flex-col items-end">
              <span className="text-[10px] text-gray-500">{deadlineDisplay}까지</span>
              <span className="text-base font-bold text-gray-900 tabular-nums">
                {countdown}
              </span>
            </div>
          </div>

          {/* Chevron Icon */}
          <ChevronDown
            className={`w-4 h-4 text-gray-600 transition-transform duration-200 ${
              isExpanded ? 'rotate-180' : ''
            }`}
          />
        </div>
      </button>

      {/* Accordion Content */}
      <div
        className={`accordion-content overflow-hidden transition-all duration-300 ${
          isExpanded ? 'max-h-[500px]' : 'max-h-0'
        }`}
      >
        {isExpanded && (
          <div className="pb-4">
            <BoardTable type={title} data={data} />
          </div>
        )}
      </div>
    </div>
  );
}
