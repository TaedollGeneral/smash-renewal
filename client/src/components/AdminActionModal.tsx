import { useState, useEffect } from 'react';
import { X, UserPlus, UserMinus } from 'lucide-react';
import type { BoardType } from '@/types';

interface AdminActionModalProps {
  isOpen: boolean;
  onClose: () => void;
  /** 모든 카테고리 (운동 | 게스트 | 잔여석 | 레슨) */
  category: BoardType;
  dayType: string;
  /** 어떤 버튼을 눌러 열었는지 — '신청'이면 추가, '취소'이면 삭제 */
  actionType: '신청' | '취소';
  /**
   * 확인 시 호출되는 콜백.
   * - 게스트/잔여석 신청: (targetUserId, guestName) — 이름은 게시판 표시용
   * - 그 외 신청 및 모든 취소: (targetUserId) — 이름은 백엔드 DB 조회
   */
  onSubmit: (targetUserId: string, guestName?: string) => void;
}

export function AdminActionModal({
  isOpen,
  onClose,
  category,
  dayType,
  actionType,
  onSubmit,
}: AdminActionModalProps) {
  const [userId, setUserId] = useState('');
  const [guestName, setGuestName] = useState('');

  // 열릴 때마다 인풋 초기화
  useEffect(() => {
    if (isOpen) {
      setUserId('');
      setGuestName('');
    }
  }, [isOpen]);

  if (!isOpen) return null;

  /**
   * 이름 입력란을 추가로 보여줄 조건:
   * '게스트' 또는 '잔여석' 카테고리이고 '신청'일 때만 2개 인풋 표시.
   * 그 외(다른 카테고리 신청, 모든 취소)는 1개 인풋(ID만).
   */
  const showNameInput =
    (category === '게스트' || category === '잔여석') && actionType === '신청';

  const isAdd = actionType === '신청';
  const actionLabel = isAdd ? '추가' : '삭제';
  const actionKr = isAdd ? '신청' : '취소';
  const Icon = isAdd ? UserPlus : UserMinus;
  const btnColor = isAdd
    ? 'bg-[#1C5D99] hover:bg-[#174e82] active:bg-[#123f6b] text-white'
    : 'bg-red-500 hover:bg-red-600 active:bg-red-700 text-white';
  const ringColor = isAdd ? 'focus:ring-[#1C5D99]' : 'focus:ring-red-400';

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!userId.trim()) {
      alert('대상자 ID를 입력해주세요.');
      return;
    }
    if (showNameInput && !guestName.trim()) {
      alert('게시판에 표시될 이름을 입력해주세요.');
      return;
    }
    onSubmit(userId.trim(), showNameInput ? guestName.trim() : undefined);
    setUserId('');
    setGuestName('');
    onClose();
  };

  const handleClose = () => {
    setUserId('');
    setGuestName('');
    onClose();
  };

  return (
    <div
      className="fixed inset-0 bg-black/60 z-[60] flex items-center justify-center p-4"
      onClick={(e) => { if (e.target === e.currentTarget) handleClose(); }}
    >
      <div className="bg-white rounded-xl w-full max-w-sm shadow-2xl overflow-hidden">
        {/* Header */}
        <div
          className={`flex items-center justify-between px-5 py-4 ${
            isAdd ? 'bg-[#1C5D99]' : 'bg-red-500'
          }`}
        >
          <div className="flex items-center gap-2">
            <Icon className="w-5 h-5 text-white" />
            <h3 className="text-base font-bold text-white">
              [관리자] {dayType} {category} {actionKr}
            </h3>
          </div>
          <button
            onClick={handleClose}
            className="p-1 hover:bg-white/20 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-white" />
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="px-5 py-5 space-y-4">
          <p className="text-sm text-gray-600 leading-relaxed">
            {isAdd
              ? showNameInput
                ? `대리 신청할 회원의 ID와 게시판에 표시될 이름을 입력하세요.`
                : `대리 신청할 회원의 ID를 입력하세요.`
              : `대리 취소할 회원의 ID를 입력하세요.`}
          </p>

          {/* 인풋 1: 대상자 ID (항상 표시) */}
          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">
              대상자 ID
            </label>
            <input
              type="text"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              className={`w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 ${ringColor} focus:border-transparent transition`}
              placeholder={`${actionLabel}할 회원 ID 입력`}
              autoFocus
              required
            />
          </div>

          {/* 인풋 2: 표시 이름 (게스트/잔여석 신청일 때만 표시) */}
          {showNameInput && (
            <div>
              <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">
                {category === '게스트' ? '게스트 이름' : '대리인 이름'}
              </label>
              <input
                type="text"
                value={guestName}
                onChange={(e) => setGuestName(e.target.value)}
                className={`w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 ${ringColor} focus:border-transparent transition`}
                placeholder="게시판에 표시될 이름 입력"
                required
              />
            </div>
          )}

          {/* Buttons */}
          <div className="flex gap-2 pt-1">
            <button
              type="button"
              onClick={handleClose}
              className="flex-1 px-4 py-2.5 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 active:bg-gray-300 transition-colors text-sm font-medium"
            >
              닫기
            </button>
            <button
              type="submit"
              className={`flex-1 px-4 py-2.5 rounded-lg transition-colors text-sm font-bold ${btnColor}`}
            >
              {actionLabel} 확인
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
