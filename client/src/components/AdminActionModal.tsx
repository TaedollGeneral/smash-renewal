import { useState, useEffect } from 'react';
import { X, UserPlus, UserMinus } from 'lucide-react';

interface AdminActionModalProps {
  isOpen: boolean;
  onClose: () => void;
  category: string;
  dayType: '수' | '금';
  /** 어떤 버튼을 눌러 열었는지 — '신청'이면 추가, '취소'이면 삭제 */
  actionType: '신청' | '취소';
  /** 확인 시 대상 ID와 이름을 전달하는 콜백 */
  onSubmit: (targetUserId: string, targetName: string) => void;
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
  const [userName, setUserName] = useState('');

  // 열릴 때마다 인풋 초기화
  useEffect(() => {
    if (isOpen) {
      setUserId('');
      setUserName('');
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const isAdd = actionType === '신청';
  const actionLabel = isAdd ? '추가' : '삭제';
  const actionKr    = isAdd ? '신청' : '취소';
  const Icon        = isAdd ? UserPlus : UserMinus;
  const btnColor    = isAdd
    ? 'bg-[#1C5D99] hover:bg-[#174e82] active:bg-[#123f6b] text-white'
    : 'bg-red-500 hover:bg-red-600 active:bg-red-700 text-white';

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!userId.trim()) {
      alert('투표자 ID를 입력해주세요.');
      return;
    }
    if (!userName.trim()) {
      alert('투표자 이름을 입력해주세요.');
      return;
    }
    onSubmit(userId.trim(), userName.trim());
    setUserId('');
    setUserName('');
    onClose();
  };

  const handleClose = () => {
    setUserId('');
    setUserName('');
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
              [관리자] {dayType}요일 {category} {actionKr}
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
              ? '투표에 추가할 회원의 ID를 입력하세요.'
              : '투표에서 삭제할 회원의 ID를 입력하세요.'}
          </p>

          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">
              투표자 ID
            </label>
            <input
              type="text"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#1C5D99] focus:border-transparent transition"
              placeholder={`${actionLabel}할 ID 입력`}
              autoFocus
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">
              투표자 이름
            </label>
            <input
              type="text"
              value={userName}
              onChange={(e) => setUserName(e.target.value)}
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#1C5D99] focus:border-transparent transition"
              placeholder="이름 입력"
              required
            />
          </div>

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
