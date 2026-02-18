import { X, Lock, Copy, Calendar, RefreshCw, LogOut, CheckCircle } from 'lucide-react';
import { useState } from 'react';
import type { User, Capacity } from '@/types';
import { PasswordChangeModal } from './PasswordChangeModal';
import { CapacitySettingModal } from './CapacitySettingModal';
import { AnnouncementCopyModal } from './AnnouncementCopyModal';
import { ChangesCopyModal } from './ChangesCopyModal';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  user: User | null;
  setUser: (user: User | null) => void;
  capacities: Capacity;
  onCapacitiesChange: (capacities: Capacity) => void;
}

export function Sidebar({
  isOpen,
  onClose,
  user,
  setUser,
  capacities,
  onCapacitiesChange,
}: SidebarProps) {
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [loginId, setLoginId] = useState('');
  const [loginPwd, setLoginPwd] = useState('');
  const [loginError, setLoginError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [showCapacityModal, setShowCapacityModal] = useState(false);
  const [showAnnouncementModal, setShowAnnouncementModal] = useState(false);
  const [showChangesModal, setShowChangesModal] = useState(false);
  const [currentDayForModal, setCurrentDayForModal] = useState<'수' | '금'>('수');

  const handleLogin = () => {
    setShowLoginModal(true);
    setLoginError('');
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!loginId || !loginPwd) return;

    setIsLoading(true);
    setLoginError('');

    try {
      const res = await fetch('/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: loginId, password: loginPwd }),
      });

      const data = await res.json();

      if (res.ok) {
        const userData: User = {
          id: data.user_id,
          name: data.user_name,
          role: data.role,
          token: data.token,
        };
        localStorage.setItem('smash_token', data.token);
        localStorage.setItem('smash_user', JSON.stringify(userData));
        setUser(userData);
        setLoginId('');
        setLoginPwd('');
        setShowLoginModal(false);
      } else {
        setLoginError(data.message || '로그인에 실패했습니다.');
      }
    } catch {
      setLoginError('서버에 연결할 수 없습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('smash_token');
    localStorage.removeItem('smash_user');
    setUser(null);
  };

  const handleScheduleAdjustment = () => {
    alert('이번주 오픈/마감 조정 페이지로 이동합니다.');
  };

  const handleUpdate = async () => {
    if (!('serviceWorker' in navigator)) {
      alert('이 환경은 Service Worker를 지원하지 않습니다.\n하드 새로고침으로 업데이트하세요.');
      return;
    }
    try {
      const registrations = await navigator.serviceWorker.getRegistrations();
      if (registrations.length === 0) {
        alert('등록된 Service Worker가 없습니다.\n하드 새로고침으로 업데이트하세요.');
        return;
      }
      await Promise.all(registrations.map(reg => reg.update()));
      const waitingReg = registrations.find(reg => reg.waiting);
      if (waitingReg) {
        const confirmed = window.confirm('새 버전이 있습니다. 지금 업데이트하시겠습니까?\n(페이지가 새로고침됩니다)');
        if (confirmed) {
          waitingReg.waiting!.postMessage({ type: 'SKIP_WAITING' });
          waitingReg.addEventListener('statechange', () => {
            if (waitingReg.active) window.location.reload();
          });
        }
      } else {
        alert('이미 최신 버전입니다.');
      }
    } catch (error) {
      console.error('[업데이트] 확인 실패:', error);
      alert('업데이트 확인 중 오류가 발생했습니다.');
    }
  };

  /**
   * Hard Refresh: 배포된 최신 코드를 확실히 불러오기 위한 3단계 프로세스
   * 1. Cache API 전체 삭제
   * 2. Service Worker 등록 해제
   * 3. href 재할당으로 강제 네비게이션 (브라우저 캐시 무시)
   */
  const handleHardRefresh = async () => {
    try {
      // 1. Cache API 전체 삭제 (Service Worker 캐시)
      if ('caches' in window) {
        const cacheNames = await caches.keys();
        await Promise.all(cacheNames.map(name => caches.delete(name)));
        console.log('[Hard Refresh] Cache API 삭제 완료:', cacheNames);
      }
      // 2. Service Worker 등록 해제
      if ('serviceWorker' in navigator) {
        const registrations = await navigator.serviceWorker.getRegistrations();
        await Promise.all(registrations.map(reg => reg.unregister()));
        console.log('[Hard Refresh] Service Worker 해제 완료');
      }
    } finally {
      // 3. 강제 재탐색 — reload()가 아닌 href 할당으로 "navigate" 요청
      window.location.href = window.location.origin + window.location.pathname;
    }
  };

  return (
    <>
      {/* Login Modal */}
      {showLoginModal && (
        <div className="fixed inset-0 bg-black/60 z-[60] flex items-center justify-center p-4">
          <div className="bg-white rounded-lg p-6 w-full max-w-sm shadow-2xl">
            <h3 className="text-lg font-bold text-gray-900 mb-4">로그인</h3>
            <form onSubmit={handleLoginSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">아이디</label>
                <input
                  type="text"
                  value={loginId}
                  onChange={(e) => setLoginId(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-500"
                  placeholder="아이디 입력"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">비밀번호</label>
                <input
                  type="password"
                  value={loginPwd}
                  onChange={(e) => setLoginPwd(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-500"
                  placeholder="비밀번호 입력"
                  required
                />
              </div>
              {loginError && (
                <p className="text-sm text-red-600">{loginError}</p>
              )}
              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setShowLoginModal(false);
                    setLoginId('');
                    setLoginPwd('');
                    setLoginError('');
                  }}
                  className="flex-1 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors font-medium"
                >
                  취소
                </button>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="flex-1 px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-800 transition-colors font-medium disabled:opacity-50"
                >
                  {isLoading ? '로그인 중...' : '로그인'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Password Change Modal */}
      <PasswordChangeModal
        isOpen={showPasswordModal}
        onClose={() => setShowPasswordModal(false)}
      />

      {/* Capacity Setting Modal */}
      <CapacitySettingModal
        isOpen={showCapacityModal}
        currentCapacities={capacities}
        onSave={onCapacitiesChange}
        onClose={() => setShowCapacityModal(false)}
      />

      {/* Announcement Copy Modal */}
      <AnnouncementCopyModal
        isOpen={showAnnouncementModal}
        onClose={() => setShowAnnouncementModal(false)}
        currentDay={currentDayForModal}
        setCurrentDay={setCurrentDayForModal}
      />

      {/* Changes Copy Modal */}
      <ChangesCopyModal
        isOpen={showChangesModal}
        onClose={() => setShowChangesModal(false)}
        currentDay={currentDayForModal}
        setCurrentDay={setCurrentDayForModal}
      />

      {/* Overlay */}
      <div
        className={`fixed inset-0 bg-black/50 z-40 transition-opacity duration-300 ${
          isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
        }`}
        onClick={onClose}
      />

      {/* Sidebar */}
      <div
        className={`fixed top-0 left-0 h-full w-80 bg-gray-50 z-50 transform transition-transform duration-300 ease-out ${
          isOpen ? 'translate-x-0 shadow-2xl' : '-translate-x-full'
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-300 pt-[max(16px,env(safe-area-inset-top))]">
          {user ? (
            <div className="flex flex-col">
              <span className="font-bold text-lg text-gray-900">{user.name}</span>
              <span className="text-xs text-gray-500 font-normal">{user.role}</span>
            </div>
          ) : (
            <button
              onClick={handleLogin}
              className="font-bold text-lg text-gray-900 hover:text-gray-700 transition-colors"
            >
              로그인
            </button>
          )}
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-200 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-700" />
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto h-[calc(100%-64px)] p-4 flex flex-col">
          <div className="flex-1">
            {/* 일반 섹션 */}
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-gray-600 mb-3 px-2">일반</h3>
              <div className="space-y-2">
                {/* 새로고침 (Hard Refresh) */}
                <button
                  onClick={handleHardRefresh}
                  className="w-full flex items-center gap-3 p-3 bg-white rounded-lg border border-gray-300 hover:bg-gray-100 transition-colors"
                >
                  <RefreshCw className="w-5 h-5 text-gray-700" />
                  <span className="text-sm text-gray-900">새로고침</span>
                </button>

                {/* 비밀번호 변경 */}
                <button
                  onClick={() => setShowPasswordModal(true)}
                  className="w-full flex items-center gap-3 p-3 bg-white rounded-lg border border-gray-300 hover:bg-gray-100 transition-colors"
                >
                  <Lock className="w-5 h-5 text-gray-700" />
                  <span className="text-sm text-gray-900">비밀번호 변경</span>
                </button>
              </div>
            </div>

            {/* 임원진 섹션 */}
            <div>
              <h3 className="text-sm font-semibold text-gray-600 mb-3 px-2">임원진</h3>
              <div className="space-y-2">
                {/* 운동정원 확정 */}
                <button
                  onClick={() => setShowCapacityModal(true)}
                  className="w-full flex items-center gap-3 p-3 bg-white rounded-lg border border-gray-300 hover:bg-gray-100 transition-colors"
                >
                  <CheckCircle className="w-5 h-5 text-gray-700" />
                  <span className="text-sm text-gray-900">운동정원 확정</span>
                </button>

                {/* 공지용 명단 복사 */}
                <button
                  onClick={() => setShowAnnouncementModal(true)}
                  className="w-full flex items-center gap-3 p-3 bg-white rounded-lg border border-gray-300 hover:bg-gray-100 transition-colors"
                >
                  <Copy className="w-5 h-5 text-gray-700" />
                  <span className="text-sm text-gray-900">공지용 명단 복사</span>
                </button>

                {/* 변경사항 복사 */}
                <button
                  onClick={() => setShowChangesModal(true)}
                  className="w-full flex items-center gap-3 p-3 bg-white rounded-lg border border-gray-300 hover:bg-gray-100 transition-colors"
                >
                  <Copy className="w-5 h-5 text-gray-700" />
                  <span className="text-sm text-gray-900">변경사항 복사</span>
                </button>

                {/* 이번주 오픈/마감 조정 */}
                <button
                  onClick={handleScheduleAdjustment}
                  className="w-full flex items-center gap-3 p-3 bg-white rounded-lg border border-gray-300 hover:bg-gray-100 transition-colors"
                >
                  <Calendar className="w-5 h-5 text-gray-700" />
                  <span className="text-sm text-gray-900">이번주 오픈/마감 조정</span>
                </button>

                {/* 업데이트 */}
                <button
                  onClick={handleUpdate}
                  className="w-full flex items-center gap-3 p-3 bg-white rounded-lg border border-gray-300 hover:bg-gray-100 transition-colors"
                >
                  <RefreshCw className="w-5 h-5 text-gray-700" />
                  <span className="text-sm text-gray-900">업데이트</span>
                </button>
              </div>
            </div>
          </div>

          {/* Logout Button */}
          {user && (
            <button
              onClick={handleLogout}
              className="mb-6 w-full flex items-center justify-center gap-2 p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-200 rounded-lg transition-colors"
            >
              <LogOut className="w-4 h-4" />
              <span className="text-sm">로그아웃</span>
            </button>
          )}
        </div>
      </div>
    </>
  );
}
