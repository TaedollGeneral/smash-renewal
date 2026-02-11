import { useState } from 'react';
import type { BoardType, ActionType } from '@/types';

interface ApplicationPanelProps {
  availablePanels: BoardType[];
}

export function ApplicationPanel({ availablePanels }: ApplicationPanelProps) {
  const [selectedBoard, setSelectedBoard] = useState<BoardType>(availablePanels[0]);
  const [action, setAction] = useState<ActionType>('신청');
  const [id, setId] = useState('');
  const [pwd, setPwd] = useState('');
  const [participants, setParticipants] = useState('');

  const handleSubmit = () => {
    console.log({
      board: selectedBoard,
      action,
      id,
      pwd,
      participants,
    });
    // 실제 신청/취소 로직 처리
    alert(`${action} 요청이 처리되었습니다.`);
  };

  const showParticipantsInput = selectedBoard === '게스트' || selectedBoard === '잔여석';

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-gray-50 rounded-t-3xl shadow-2xl z-50 border-t border-gray-300">
      <div className="p-2 sm:p-3 space-y-2">
        {/* First Row: Board Selection (Left) + Action Selection (Right) */}
        <div className="flex gap-2 justify-between">
          <select
            value={selectedBoard}
            onChange={(e) => setSelectedBoard(e.target.value as BoardType)}
            className="w-28 sm:w-32 px-2 sm:px-3 py-2 border border-gray-400 rounded-lg text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-gray-500 bg-white"
          >
            {availablePanels.map((panel) => (
              <option key={panel} value={panel}>
                {panel}
              </option>
            ))}
          </select>

          <div className="flex gap-1 bg-gray-200 rounded-lg p-1">
            <button
              onClick={() => setAction('신청')}
              className={`px-3 sm:px-4 py-1.5 rounded-md text-xs sm:text-sm font-medium transition-all whitespace-nowrap h-[38px] ${
                action === '신청'
                  ? 'bg-gray-700 text-white shadow-sm'
                  : 'text-gray-700 hover:text-gray-900'
              }`}
            >
              신청
            </button>
            <button
              onClick={() => setAction('취소')}
              className={`px-3 sm:px-4 py-1.5 rounded-md text-xs sm:text-sm font-medium transition-all whitespace-nowrap h-[38px] ${
                action === '취소'
                  ? 'bg-gray-700 text-white shadow-sm'
                  : 'text-gray-700 hover:text-gray-900'
              }`}
            >
              취소
            </button>
          </div>
        </div>

        {/* Second Row: ID, PWD, Participants (conditional), Submit Button */}
        <div className="flex gap-1.5 sm:gap-2">
          <div className="flex gap-1.5 sm:gap-2 flex-1">
            <input
              type="text"
              placeholder="ID"
              value={id}
              onChange={(e) => setId(e.target.value)}
              className={`${showParticipantsInput ? 'flex-1' : 'flex-[3]'} min-w-0 px-2 py-2 border border-gray-400 rounded-lg text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-gray-500`}
            />

            <input
              type="password"
              placeholder="PWD"
              value={pwd}
              onChange={(e) => setPwd(e.target.value)}
              className={`${showParticipantsInput ? 'flex-1' : 'flex-[3]'} min-w-0 px-2 py-2 border border-gray-400 rounded-lg text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-gray-500`}
            />

            {showParticipantsInput && (
              <input
                type="text"
                placeholder="인원"
                value={participants}
                onChange={(e) => setParticipants(e.target.value)}
                className="flex-1 px-2 py-2 border border-gray-400 rounded-lg text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-gray-500"
              />
            )}
          </div>

          <button
            onClick={handleSubmit}
            className="w-[130px] sm:w-[150px] bg-gray-700 text-white font-semibold rounded-lg hover:bg-gray-800 active:bg-gray-900 transition-colors text-xs sm:text-sm whitespace-nowrap h-[38px]"
          >
            확인
          </button>
        </div>
      </div>

      {/* Safe area for iOS PWA */}
      <div className="h-[env(safe-area-inset-bottom)]" />
    </div>
  );
}
