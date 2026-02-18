import { useState } from 'react';
import { X } from 'lucide-react';

interface AdminActionModalProps {
  isOpen: boolean;
  onClose: () => void;
  category: string;
  dayType: '수' | '금';
}

export function AdminActionModal({ isOpen, onClose, category, dayType }: AdminActionModalProps) {
  const [userId, setUserId] = useState('');

  if (!isOpen) return null;

  const handleApply = () => {
    if (!userId.trim()) {
      alert('대상 ID를 입력해주세요.');
      return;
    }
    // 대리 신청 로직
    alert(`${userId}님의 ${dayType}요일 ${category} 신청이 완료되었습니다.`);
    setUserId('');
    onClose();
  };

  const handleCancel = () => {
    if (!userId.trim()) {
      alert('대상 ID를 입력해주세요.');
      return;
    }
    // 대리 취소 로직
    alert(`${userId}님의 ${dayType}요일 ${category} 신청이 취소되었습니다.`);
    setUserId('');
    onClose();
  };

  const handleClose = () => {
    setUserId('');
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/60 z-[60] flex items-center justify-center p-4">
      <div className="bg-white rounded-lg p-6 w-full max-w-md shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-gray-900">대리 신청/취소</h3>
          <button
            onClick={handleClose}
            className="p-1 hover:bg-gray-100 rounded transition-colors"
          >
            <X className="w-5 h-5 text-gray-700" />
          </button>
        </div>

        <p className="text-sm text-gray-600 mb-4">
          {dayType}요일 {category} 대리 신청 또는 취소할 회원의 ID를 입력하세요.
        </p>

        {/* Input */}
        <div className="mb-6">
          <input
            type="text"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-500"
            placeholder="대상 ID 입력"
          />
        </div>

        {/* Buttons */}
        <div className="flex gap-2">
          <button
            onClick={handleCancel}
            className="flex-1 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors font-medium"
          >
            대리 취소
          </button>
          <button
            onClick={handleApply}
            className="flex-1 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors font-medium"
          >
            대리 신청
          </button>
        </div>
      </div>
    </div>
  );
}
