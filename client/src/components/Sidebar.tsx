import { X, RefreshCw, Lock, LogOut, LogIn, CheckCircle, Calendar, Clock, ScrollText, KeyRound } from 'lucide-react';
import { useState } from 'react';
import type { User, Capacity } from '@/types';
import { PasswordChangeModal } from './PasswordChangeModal';
import { CapacitySettingModal } from './CapacitySettingModal';
import { TimelinePanel } from './TimelinePanel';
import { GuestPolicyPanel } from './GuestPolicyPanel';
import { ForcePasswordResetModal } from './ForcePasswordResetModal';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  user: User | null;
  setUser: (user: User | null) => void;
  capacities: Capacity;
  onCapacitiesChange: (capacities: { 수?: number; 금?: number }) => void;
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
  const [showTimelinePanel, setShowTimelinePanel] = useState(false);
  const [showGuestPolicyPanel, setShowGuestPolicyPanel] = useState(false);
  const [showForcePasswordReset, setShowForcePasswordReset] = useState(false);

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
      const res = await fetch('api/login', {
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

  const isManager = user?.role === 'manager';

  const handleScheduleAdjustment = () => {
    if (!isManager) {
      window.confirm(`해당 메뉴는 임원진 전용입니다.`);
      return;
    }
    alert('이번주 오픈/마감 조정 페이지로 이동합니다.');
  };

  const handleUpdate = async () => {
    if (!isManager) {
      window.confirm(`해당 메뉴는 임원진 전용입니다.`);
      return;
    }
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
            <h3 className="text-lg font-bold text-[#4F6D7A] mb-4">로그인</h3>
            <form onSubmit={handleLoginSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-[#4F6D7A] mb-1">아이디</label>
                <input
                  type="text"
                  value={loginId}
                  onChange={(e) => setLoginId(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#C0D6DB]"
                  placeholder="아이디 입력"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#4F6D7A] mb-1">비밀번호</label>
                <input
                  type="password"
                  value={loginPwd}
                  onChange={(e) => setLoginPwd(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#C0D6DB]"
                  placeholder="비밀번호 입력"
                  required
                />
              </div>

              {/* 실수로 지워진 에러 메시지 출력 부분 복구 */}
              {loginError && (
                <div className="text-red-500 text-sm font-medium">
                  {loginError}
                </div>
              )}

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => { setShowLoginModal(false); setLoginId(''); setLoginPwd(''); }}
                  className="flex-1 px-4 py-2 bg-[#C0D6DB] text-[#4F6D7A] rounded-lg hover:bg-[#A8C4CA] transition-colors font-medium"
                >
                  취소
                </button>
                {/* 지워진 isLoading 상태 적용 (버튼 비활성화 및 텍스트 변경) */}
                <button
                  type="submit"
                  disabled={isLoading}
                  className="flex-1 px-4 py-2 bg-[#C0D6DB] text-[#4F6D7A] rounded-lg hover:bg-[#A8C4CA] transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
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

      {/* Timeline Panel */}
      <TimelinePanel
        isOpen={showTimelinePanel}
        onClose={() => setShowTimelinePanel(false)}
      />

      {/* Guest Policy Panel */}
      <GuestPolicyPanel
        isOpen={showGuestPolicyPanel}
        onClose={() => setShowGuestPolicyPanel(false)}
      />

      {/* Capacity Setting Modal */}
      <CapacitySettingModal
        isOpen={showCapacityModal}
        currentCapacities={{ 수: capacities.수?.total, 금: capacities.금?.total }}
        onSave={onCapacitiesChange}
        onClose={() => setShowCapacityModal(false)}
        user={user}
      />

      {/* Force Password Reset Modal */}
      <ForcePasswordResetModal
        isOpen={showForcePasswordReset}
        onClose={() => setShowForcePasswordReset(false)}
        user={user}
      />

      {/* Overlay */}
      <div
        className={`fixed inset-0 bg-black/50 z-40 transition-opacity duration-300 ${isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
          }`}
        onClick={onClose}
      />

      {/* Sidebar */}
      <div
        className={`fixed top-0 left-0 h-full w-80 bg-[#1C5D99] z-50 transform transition-transform duration-300 ease-out ${isOpen ? 'translate-x-0 shadow-2xl' : '-translate-x-full'
          }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-[#2C6DB0] pt-[max(16px,env(safe-area-inset-top))]">
          {user ? (
            <div className="flex flex-col">
              <span className="font-bold text-lg text-white">{user.name}</span>
              <span className="text-xs text-white/90 font-normal">{user.role}</span>
            </div>
          ) : (
            <button
              onClick={handleLogin}
              className="flex items-center gap-2.5 pl-1.5 pr-5 py-1.5 bg-white rounded-full hover:bg-white/95 active:scale-95 transition-all shadow-lg hover:shadow-xl"
            >
              <div className="w-8 h-8 rounded-full bg-[#1C5D99] flex items-center justify-center flex-shrink-0">
                <LogIn className="w-4 h-4 text-white" />
              </div>
              <span className="text-[#1C5D99] text-sm font-bold tracking-wide">로그인</span>
            </button>
          )}
          <button
            onClick={onClose}
            className="p-2 hover:bg-white/20 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-white" />
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto h-[calc(100%-72px)] pt-4 px-4 pb-10 flex flex-col gap-6">
          {/* 일반 섹션 */}
          <div>
            <h3 className="text-xs font-semibold text-white/60 uppercase tracking-wider mb-3 px-1">일반</h3>
            <div className="space-y-2">
              <button
                onClick={handleHardRefresh}
                className="w-full flex items-center gap-3 p-3 bg-white text-black rounded-lg hover:bg-white/90 transition-colors"
              >
                <RefreshCw className="w-5 h-5 flex-shrink-0" />
                <span className="text-sm font-semibold">새로고침</span>
              </button>
              <button
                onClick={() => setShowPasswordModal(true)}
                className="w-full flex items-center gap-3 p-3 bg-white text-black rounded-lg hover:bg-white/90 transition-colors"
              >
                <Lock className="w-5 h-5 flex-shrink-0" />
                <span className="text-sm font-semibold">비밀번호 변경</span>
              </button>
              <button
                onClick={() => setShowTimelinePanel(true)}
                className="w-full flex items-center gap-3 p-3 bg-white text-black rounded-lg hover:bg-white/90 transition-colors"
              >
                <Clock className="w-5 h-5 flex-shrink-0" />
                <span className="text-sm font-semibold">오픈 및 마감 타임라인</span>
              </button>
              <button
                onClick={() => setShowGuestPolicyPanel(true)}
                className="w-full flex items-center gap-3 p-3 bg-white text-black rounded-lg hover:bg-white/90 transition-colors"
              >
                <ScrollText className="w-5 h-5 flex-shrink-0" />
                <span className="text-sm font-semibold">운영 원칙 안내</span>
              </button>
            </div>
          </div>

          {/* 임원진 섹션 */}
          <div>
            <h3 className="text-xs font-semibold text-white/60 uppercase tracking-wider mb-3 px-1">임원진</h3>
            <div className="space-y-2">
              <button
                onClick={() => setShowCapacityModal(true)}
                className="w-full flex items-center gap-3 p-3 bg-white text-black rounded-lg hover:bg-white/90 transition-colors"
              >
                <CheckCircle className="w-5 h-5 flex-shrink-0" />
                <span className="text-sm font-semibold">운동정원 확정</span>
              </button>
              <button
                onClick={handleScheduleAdjustment}
                className="w-full flex items-center gap-3 p-3 bg-white text-black rounded-lg hover:bg-white/90 transition-colors"
              >
                <Calendar className="w-5 h-5 flex-shrink-0" />
                <span className="text-sm font-semibold">이번주 오픈/마감 조정</span>
              </button>
              <button
                onClick={() => setShowForcePasswordReset(true)}
                className="w-full flex items-center gap-3 p-3 bg-white text-black rounded-lg hover:bg-white/90 transition-colors"
              >
                <KeyRound className="w-5 h-5 flex-shrink-0" />
                <span className="text-sm font-semibold">임시 비밀번호 설정</span>
              </button>
              <button
                onClick={handleUpdate}
                className="w-full flex items-center gap-3 p-3 bg-white text-black rounded-lg hover:bg-white/90 transition-colors"
              >
                <RefreshCw className="w-5 h-5 flex-shrink-0" />
                <span className="text-sm font-semibold">업데이트</span>
              </button>
            </div>
          </div>

          {/* Spacer */}
          <div className="flex-1" />

          {/* Logout */}
          {user && (
            <button
              onClick={handleLogout}
              className="inline-flex items-center justify-center gap-2 p-3 text-white hover:text-white hover:bg-white/20 rounded-lg transition-colors"
            >
              <LogOut className="w-4 h-4" />
              <span className="text-sm font-semibold">로그아웃</span>
            </button>
          )}
        </div>
      </div>
    </>
  );
}
