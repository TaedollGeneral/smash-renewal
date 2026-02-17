import { ChevronDown, Bell } from 'lucide-react';
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
  const [notification1Enabled, setNotification1Enabled] = useState(false);
  const [notification2Enabled, setNotification2Enabled] = useState(false);
  const [showParticipantModal, setShowParticipantModal] = useState(false);
  const [participantName, setParticipantName] = useState('');

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

  const handleApply = (e: React.MouseEvent) => {
    e.stopPropagation(); // 아코디언 토글 방지

    // 게스트와 잔여석은 참여인원 입력 모달 표시
    if (title === '게스트' || title === '잔여석') {
      setShowParticipantModal(true);
    } else {
      console.log(`${title} - 신청 실행`);
      alert(`${title} 신청이 완료되었습니다.`);
    }
  };

  const handleParticipantSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (participantName.trim()) {
      console.log(`${title} - 신청 실행 (참여인원: ${participantName})`);
      alert(`${title} 신청이 완료되었습니다.\n참여인원: ${participantName}`);
      setParticipantName('');
      setShowParticipantModal(false);
    }
  };

  const handleCancel = (e: React.MouseEvent) => {
    e.stopPropagation(); // 아코디언 토글 방지
    console.log(`${title} - 취소 실행`);
    alert(`${title} 취소가 완료되었습니다.`);
  };

  const handleNotification1Toggle = (e: React.MouseEvent) => {
    e.stopPropagation(); // 아코디언 토글 방지
    setNotification1Enabled(!notification1Enabled);
    console.log(`${title} - 알림1: ${!notification1Enabled ? '켜짐' : '꺼짐'}`);
  };

  const handleNotification2Toggle = (e: React.MouseEvent) => {
    e.stopPropagation(); // 아코디언 토글 방지
    setNotification2Enabled(!notification2Enabled);
    console.log(`${title} - 알림2: ${!notification2Enabled ? '켜짐' : '꺼짐'}`);
  };

  return (
    <div className="border-b border-gray-300 bg-gray-50">
      {/* Participant Modal */}
      {showParticipantModal && (
        <div className="fixed inset-0 bg-black/60 z-[60] flex items-center justify-center p-4">
          <div className="bg-white rounded-lg p-6 w-full max-w-sm shadow-2xl">
            <h3 className="text-lg font-bold text-gray-900 mb-4">운동참여인원 입력</h3>
            <form onSubmit={handleParticipantSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  참여인원 이름
                </label>
                <input
                  type="text"
                  value={participantName}
                  onChange={(e) => setParticipantName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-500"
                  placeholder="이름 입력"
                  autoFocus
                  required
                />
              </div>
              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setShowParticipantModal(false);
                    setParticipantName('');
                  }}
                  className="flex-1 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors font-medium"
                >
                  취소
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-800 transition-colors font-medium"
                >
                  확인
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Accordion Header */}
      <button
        onClick={onToggle}
        className="w-full px-2 py-2.5 flex items-center justify-between hover:bg-gray-100 transition-colors"
      >
        {/* Left: Chevron + Icon + Title */}
        <div className="flex items-center gap-1.5 min-w-0 flex-shrink-0">
          {/* Chevron Icon */}
          <ChevronDown
            className={`w-4 h-4 text-gray-600 transition-transform duration-200 flex-shrink-0 ${
              isExpanded ? 'rotate-180' : ''
            }`}
          />
          <span className="text-base">{boardIcons[title]}</span>
          <span className="font-semibold text-sm text-gray-900 whitespace-nowrap">{title}</span>
        </div>

        {/* Right: Notification + Countdown + Action Buttons */}
        <div className="flex items-center gap-1.5 ml-1">
          {/* Notification Buttons */}
          <div className="flex gap-0.5">
            <button
              onClick={handleNotification1Toggle}
              className="p-1 rounded-lg transition-colors"
            >
              <Bell
                className={`w-4 h-4 ${
                  notification1Enabled
                    ? 'text-blue-600 fill-blue-600'
                    : 'text-blue-300 fill-blue-100'
                }`}
              />
            </button>
            <button
              onClick={handleNotification2Toggle}
              className="p-1 rounded-lg transition-colors"
            >
              <Bell
                className={`w-4 h-4 ${
                  notification2Enabled
                    ? 'text-red-600 fill-red-600'
                    : 'text-red-300 fill-red-100'
                }`}
              />
            </button>
          </div>

          {/* Divider */}
          <div className="w-px h-7 bg-gray-300" />

          {/* Countdown */}
          <div className="flex flex-col items-end ml-1.5">
            <span className="text-[9px] text-gray-500 leading-tight">23:59까지</span>
            <span className="text-sm font-bold text-gray-900 tabular-nums leading-tight">
              {countdown}
            </span>
          </div>

          {/* Divider */}
          <div className="w-px h-7 bg-gray-300" />

          {/* Action Buttons */}
          <div className="flex gap-1">
            <button
              onClick={handleApply}
              className="relative px-2.5 py-1.5 rounded-lg text-xs font-bold text-gray-800 border border-gray-300 hover:bg-gray-200/50 active:bg-gray-200/70 transition-colors shadow-sm overflow-hidden whitespace-nowrap"
              style={{
                backgroundColor: 'rgba(156, 163, 175, 0.12)',
                backgroundImage: `repeating-linear-gradient(
                  45deg,
                  transparent,
                  transparent 2px,
                  rgba(0, 0, 0, 0.04) 2px,
                  rgba(0, 0, 0, 0.04) 2.5px
                ),
                repeating-linear-gradient(
                  -45deg,
                  transparent,
                  transparent 2px,
                  rgba(0, 0, 0, 0.04) 2px,
                  rgba(0, 0, 0, 0.04) 2.5px
                )`
              }}
            >
              <span className="relative z-10">신청</span>
            </button>
            <button
              onClick={handleCancel}
              className="relative px-2.5 py-1.5 rounded-lg text-xs font-bold text-gray-800 border border-gray-300 hover:bg-gray-200/50 active:bg-gray-200/70 transition-colors shadow-sm overflow-hidden whitespace-nowrap"
              style={{
                backgroundColor: 'rgba(156, 163, 175, 0.12)',
                backgroundImage: `repeating-linear-gradient(
                  45deg,
                  transparent,
                  transparent 2px,
                  rgba(0, 0, 0, 0.04) 2px,
                  rgba(0, 0, 0, 0.04) 2.5px
                ),
                repeating-linear-gradient(
                  -45deg,
                  transparent,
                  transparent 2px,
                  rgba(0, 0, 0, 0.04) 2px,
                  rgba(0, 0, 0, 0.04) 2.5px
                )`
              }}
            >
              <span className="relative z-10">취소</span>
            </button>
          </div>
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
