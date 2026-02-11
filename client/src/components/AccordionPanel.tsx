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
}

export function AccordionPanel({ title, isExpanded, onToggle }: AccordionPanelProps) {
  const [countdown, setCountdown] = useState('23:59:59');

  useEffect(() => {
    // Mock countdown timer
    const interval = setInterval(() => {
      const now = new Date();
      const hours = String(23 - now.getHours()).padStart(2, '0');
      const minutes = String(59 - now.getMinutes()).padStart(2, '0');
      const seconds = String(59 - now.getSeconds()).padStart(2, '0');
      setCountdown(`${hours}:${minutes}:${seconds}`);
    }, 1000);

    return () => clearInterval(interval);
  }, []);

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
              <span className="text-[10px] text-gray-500">23:59까지</span>
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
            <BoardTable type={title} />
          </div>
        )}
      </div>
    </div>
  );
}
