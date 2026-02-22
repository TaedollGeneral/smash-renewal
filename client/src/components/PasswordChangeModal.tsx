import { useState } from 'react';
import { createPortal } from 'react-dom';
import { X, Lock } from 'lucide-react';

interface PasswordChangeModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function PasswordChangeModal({ isOpen, onClose }: PasswordChangeModalProps) {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  if (!isOpen) return null;

  const resetForm = () => {
    setCurrentPassword('');
    setNewPassword('');
    setConfirmPassword('');
    setError('');
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // 현재 비밀번호와 새 비밀번호 동일 여부 검사
    if (currentPassword === newPassword) {
      setError('새 비밀번호는 기존 비밀번호와 다르게 설정해야 합니다.');
      return;
    }

    // 새 비밀번호 확인 일치 검사
    if (newPassword !== confirmPassword) {
      setError('새 비밀번호와 새 비밀번호 확인이 일치하지 않습니다.');
      return;
    }

    const token = localStorage.getItem('smash_token');
    if (!token) {
      setError('로그인이 필요합니다.');
      return;
    }

    setIsLoading(true);
    try {
      const res = await fetch('/api/change-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });

      const data = await res.json();

      if (res.ok) {
        // 성공: 모달 닫기 → 세션 클리어 → 로그인 화면으로 강제 이동
        onClose();
        localStorage.removeItem('smash_token');
        localStorage.removeItem('smash_user');
        window.location.href = window.location.origin + window.location.pathname;
      } else {
        setError(data.message || '비밀번호 변경에 실패했습니다.');
      }
    } catch {
      setError('서버에 연결할 수 없습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  return createPortal(
    <div
      className="fixed inset-0 bg-black/60 z-[60] flex items-center justify-center p-4"
      onClick={(e) => { if (e.target === e.currentTarget) handleClose(); }}
    >
      <div className="bg-white rounded-xl w-full max-w-sm shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 bg-[#1C5D99]">
          <div className="flex items-center gap-2">
            <Lock className="w-5 h-5 text-white" />
            <h3 className="text-base font-bold text-white">비밀번호 변경</h3>
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
          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">
              현재 비밀번호
            </label>
            <input
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#1C5D99] focus:border-transparent transition"
              placeholder="현재 비밀번호 입력"
              autoFocus
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">
              새 비밀번호
            </label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#1C5D99] focus:border-transparent transition"
              placeholder="새 비밀번호 입력"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">
              새 비밀번호 확인
            </label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#1C5D99] focus:border-transparent transition"
              placeholder="새 비밀번호 다시 입력"
              required
            />
          </div>

          {/* 인라인 에러 메시지 */}
          {error && (
            <div className="text-red-600 text-sm font-medium bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {error}
            </div>
          )}

          {/* Buttons */}
          <div className="flex gap-2 pt-1">
            <button
              type="button"
              onClick={handleClose}
              className="flex-1 px-4 py-2.5 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 active:bg-gray-300 transition-colors text-sm font-medium"
            >
              취소
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 px-4 py-2.5 bg-[#1C5D99] hover:bg-[#174e82] active:bg-[#123f6b] text-white rounded-lg transition-colors text-sm font-bold disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? '변경 중...' : '변경 확인'}
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body
  );
}
