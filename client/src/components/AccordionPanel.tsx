import { ChevronDown, Bell } from 'lucide-react';
import { useState, useEffect, useRef } from 'react';
import { BoardTable } from './BoardTable';
import type { BoardType, CategoryState } from '@/types';

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
  dayType: '수' | '금';
  capacity?: number; // 운동 정원 (서버 응답에서 수신)
  /**
   * 서버에서 받아온 카테고리 상태
   * deadlineTimestamp: 절대 시각(Unix ms) → 폴링과 무관하게 클라이언트가 연속 계산
   */
  categoryState: CategoryState;
  onCountdownZero?: () => void;
}

export function AccordionPanel({
  title,
  isExpanded,
  onToggle,
  dayType: _dayType,
  capacity,
  categoryState,
  onCountdownZero,
}: AccordionPanelProps) {
  const { status, statusText, deadlineTimestamp } = categoryState;

  // 카운트다운 상태: deadlineTimestamp - Date.now() 로 직접 계산
  const [remainingMilliseconds, setRemainingMilliseconds] = useState(() =>
    Math.max(0, deadlineTimestamp - Date.now())
  );

  // hasCalledZero를 ref로 관리 → useEffect deps에 포함시키지 않아도 됨
  const hasCalledZeroRef = useRef(false);
  // onCountdownZero를 ref로 래핑 → deadlineTimestamp가 같으면 타이머가 재시작되지 않음
  const onCountdownZeroRef = useRef(onCountdownZero);
  useEffect(() => {
    onCountdownZeroRef.current = onCountdownZero;
  }); // deps 없음 - 매 렌더 후 항상 최신 콜백으로 갱신

  const [notification1Enabled, setNotification1Enabled] = useState(false);
  const [notification2Enabled, setNotification2Enabled] = useState(false);
  const [showParticipantModal, setShowParticipantModal] = useState(false);
  const [participantName, setParticipantName] = useState('');

  // 상태에 따른 카운트다운 색상 결정
  const getCountdownColor = () => {
    switch (status) {
      case 'before-open': return 'text-gray-900';
      case 'open': return 'text-green-600';
      case 'cancel-period': return 'text-red-400';
      case 'waiting': return 'text-gray-900';
      default: return 'text-green-600';
    }
  };

  // 버튼 활성화 상태 결정
  const isApplyEnabled = status === 'open';
  const isCancelEnabled = status === 'open' || status === 'cancel-period';

  // 밀리초를 적절한 형식으로 변환
  const formatTime = (milliseconds: number) => {
    if (milliseconds <= 0) return '00:00:00';

    const totalSeconds = Math.floor(milliseconds / 1000);

    // 1분(60초) 미만일 때: MM:SS.mm (분:초.밀리초)
    if (totalSeconds < 60) {
      const s = totalSeconds % 60;
      const ms = Math.floor((milliseconds % 1000) / 10);
      return `00:${String(s).padStart(2, '0')}.${String(ms).padStart(2, '0')}`;
    }

    // 1분 이상일 때: HH:MM:SS (시:분:초)
    const h = Math.floor(totalSeconds / 3600);
    const m = Math.floor((totalSeconds % 3600) / 60);
    const s = totalSeconds % 60;
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  };

  /**
   * 카운트다운 타이머
   *
   * deadlineTimestamp(절대 시각) 기준으로 매 100ms마다 Date.now()와의 차이를 계산.
   * → 폴링으로 categoryState가 갱신되어도 deadlineTimestamp가 동일하면
   *   이 effect는 재실행되지 않으므로 타이머가 리셋/점프되지 않음.
   * → 서버가 실제로 마감 시간을 변경했을 때만 타이머가 새로 시작됨.
   */
  useEffect(() => {
    hasCalledZeroRef.current = false;

    // 즉시 초기값 반영 (effect 재실행 시 깜빡임 방지)
    const initial = Math.max(0, deadlineTimestamp - Date.now());
    setRemainingMilliseconds(initial);

    if (deadlineTimestamp <= 0) return;

    const intervalMs = 100;
    const interval = setInterval(() => {
      const remaining = Math.max(0, deadlineTimestamp - Date.now());
      setRemainingMilliseconds(remaining);

      if (remaining === 0 && !hasCalledZeroRef.current && onCountdownZeroRef.current) {
        hasCalledZeroRef.current = true;
        onCountdownZeroRef.current();
      }
    }, intervalMs);

    return () => clearInterval(interval);
  }, [deadlineTimestamp]); // onCountdownZero는 ref로 관리하므로 deps 불필요

  const handleApply = (e: React.MouseEvent) => {
    e.stopPropagation();
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
    e.stopPropagation();
    console.log(`${title} - 취소 실행`);
    alert(`${title} 취소가 완료되었습니다.`);
  };

  const handleNotification1Toggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    setNotification1Enabled(!notification1Enabled);
    console.log(`${title} - 알림1: ${!notification1Enabled ? '켜짐' : '꺼짐'}`);
  };

  const handleNotification2Toggle = (e: React.MouseEvent) => {
    e.stopPropagation();
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
          <ChevronDown
            className={`w-4 h-4 text-gray-600 transition-transform duration-200 flex-shrink-0 ${
              isExpanded ? 'rotate-180' : ''
            }`}
          />
          <span className="text-base">{boardIcons[title]}</span>
          <span className="font-semibold text-sm text-gray-900 whitespace-nowrap">
            {title}{capacity !== undefined && ` (${capacity})`}
          </span>
        </div>

        {/* Right: Notification + Countdown + Action Buttons */}
        <div className="flex items-center gap-1.5 ml-1">
          {/* Notification Buttons */}
          <div className="flex gap-0.5">
            <button onClick={handleNotification1Toggle} className="p-1 rounded-lg transition-colors relative">
              <Bell
                className={`w-4 h-4 ${
                  notification1Enabled ? 'text-blue-600 fill-blue-600' : 'text-blue-300 fill-blue-100'
                }`}
              />
              {!notification1Enabled && (
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                  <div className="w-5 h-[1.5px] bg-blue-300 -rotate-45" />
                </div>
              )}
            </button>
            <button onClick={handleNotification2Toggle} className="p-1 rounded-lg transition-colors relative">
              <Bell
                className={`w-4 h-4 ${
                  notification2Enabled ? 'text-red-600 fill-red-600' : 'text-red-300 fill-red-100'
                }`}
              />
              {!notification2Enabled && (
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                  <div className="w-5 h-[1.5px] bg-red-300 -rotate-45" />
                </div>
              )}
            </button>
          </div>

          {/* Divider */}
          <div className="w-px h-7 bg-gray-300" />

          {/* Countdown */}
          <div className="flex flex-col items-end ml-1.5">
            <span className="text-[8px] leading-tight text-gray-500">{statusText}</span>
            <span className={`text-sm font-bold tabular-nums leading-tight ${getCountdownColor()}`}>
              {formatTime(remainingMilliseconds)}
            </span>
          </div>

          {/* Divider */}
          <div className="w-px h-7 bg-gray-300" />

          {/* Action Buttons */}
          <div className="flex gap-1">
            <button
              onClick={handleCancel}
              disabled={!isCancelEnabled}
              className={`relative px-2.5 py-1.5 rounded-lg text-xs font-bold border shadow-sm overflow-hidden whitespace-nowrap transition-all ${
                isCancelEnabled
                  ? 'text-gray-800 border-gray-300 hover:bg-gray-200/50 active:bg-gray-200/70 cursor-pointer'
                  : 'text-gray-400 border-gray-200 cursor-not-allowed opacity-50'
              }`}
              style={
                isCancelEnabled
                  ? {
                      backgroundColor: 'rgba(156, 163, 175, 0.12)',
                      backgroundImage: `repeating-linear-gradient(45deg,transparent,transparent 2px,rgba(0,0,0,0.04) 2px,rgba(0,0,0,0.04) 2.5px),repeating-linear-gradient(-45deg,transparent,transparent 2px,rgba(0,0,0,0.04) 2px,rgba(0,0,0,0.04) 2.5px)`,
                    }
                  : { backgroundColor: 'rgba(229, 231, 235, 0.3)' }
              }
            >
              <span className="relative z-10">취소</span>
            </button>
            <button
              onClick={handleApply}
              disabled={!isApplyEnabled}
              className={`relative px-2.5 py-1.5 rounded-lg text-xs font-bold border shadow-sm overflow-hidden whitespace-nowrap transition-all ${
                isApplyEnabled
                  ? 'text-gray-800 border-gray-300 hover:bg-gray-200/50 active:bg-gray-200/70 cursor-pointer'
                  : 'text-gray-400 border-gray-200 cursor-not-allowed opacity-50'
              }`}
              style={
                isApplyEnabled
                  ? {
                      backgroundColor: 'rgba(156, 163, 175, 0.12)',
                      backgroundImage: `repeating-linear-gradient(45deg,transparent,transparent 2px,rgba(0,0,0,0.04) 2px,rgba(0,0,0,0.04) 2.5px),repeating-linear-gradient(-45deg,transparent,transparent 2px,rgba(0,0,0,0.04) 2px,rgba(0,0,0,0.04) 2.5px)`,
                    }
                  : { backgroundColor: 'rgba(229, 231, 235, 0.3)' }
              }
            >
              <span className="relative z-10">신청</span>
            </button>
          </div>
        </div>
      </button>

      {/* Accordion Content */}
      <div
        className={`accordion-content overflow-hidden transition-all duration-500 ease-in-out ${
          isExpanded ? 'max-h-[500px] opacity-100' : 'max-h-0 opacity-0'
        }`}
      >
        <div className="pb-4">
          <BoardTable type={title} />
        </div>
      </div>
    </div>
  );
}
