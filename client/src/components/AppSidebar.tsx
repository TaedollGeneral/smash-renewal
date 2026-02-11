import { X, Bell, BellOff, Lock, Copy, Settings, Calendar, RefreshCw } from 'lucide-react';
import { useState } from 'react';

interface AppSidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export function AppSidebar({ isOpen, onClose }: AppSidebarProps) {
  const [voteNotification, setVoteNotification] = useState(true);
  const [cancelNotification, setCancelNotification] = useState(true);

  const handlePasswordChange = () => {
    // 비밀번호 변경 로직
    alert('비밀번호 변경 페이지로 이동합니다.');
  };

  const handleCopyAnnouncement = () => {
    // 공지용 명단 복사
    alert('공지용 명단이 복사되었습니다.');
  };

  const handleCopyChanges = () => {
    // 변경사항 복사
    alert('변경사항이 복사되었습니다.');
  };

  const handleScheduleAdjustment = () => {
    // 오픈/마감 조정
    alert('이번주 오픈/마감 조정 페이지로 이동합니다.');
  };

  const handleSemesterSettings = () => {
    // 학기/주차 설정
    alert('학기/주차 설정 페이지로 이동합니다.');
  };

  const handleUpdate = () => {
    // 업데이트
    alert('업데이트를 시작합니다.');
  };

  return (
    <>
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
          <h2 className="font-bold text-lg text-gray-900">메뉴</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-200 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-700" />
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto h-[calc(100%-64px)] p-4">
          {/* 일반 섹션 */}
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-gray-600 mb-3 px-2">일반</h3>
            <div className="space-y-2">
              {/* 투표 알림 */}
              <div className="flex items-center justify-between p-3 bg-white rounded-lg border border-gray-300 hover:bg-gray-100 transition-colors">
                <div className="flex items-center gap-3">
                  {voteNotification ? (
                    <Bell className="w-5 h-5 text-gray-700" />
                  ) : (
                    <BellOff className="w-5 h-5 text-gray-500" />
                  )}
                  <span className="text-sm text-gray-900">투표 알림</span>
                </div>
                <button
                  onClick={() => setVoteNotification(!voteNotification)}
                  className={`relative w-12 h-6 rounded-full transition-colors ${
                    voteNotification ? 'bg-gray-700' : 'bg-gray-300'
                  }`}
                >
                  <div
                    className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow-md transition-transform ${
                      voteNotification ? 'translate-x-6' : 'translate-x-0.5'
                    }`}
                  />
                </button>
              </div>

              {/* 취소 알림 */}
              <div className="flex items-center justify-between p-3 bg-white rounded-lg border border-gray-300 hover:bg-gray-100 transition-colors">
                <div className="flex items-center gap-3">
                  {cancelNotification ? (
                    <Bell className="w-5 h-5 text-gray-700" />
                  ) : (
                    <BellOff className="w-5 h-5 text-gray-500" />
                  )}
                  <span className="text-sm text-gray-900">취소 알림</span>
                </div>
                <button
                  onClick={() => setCancelNotification(!cancelNotification)}
                  className={`relative w-12 h-6 rounded-full transition-colors ${
                    cancelNotification ? 'bg-gray-700' : 'bg-gray-300'
                  }`}
                >
                  <div
                    className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow-md transition-transform ${
                      cancelNotification ? 'translate-x-6' : 'translate-x-0.5'
                    }`}
                  />
                </button>
              </div>

              {/* 비밀번호 변경 */}
              <button
                onClick={handlePasswordChange}
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
              {/* 공지용 명단 복사 */}
              <button
                onClick={handleCopyAnnouncement}
                className="w-full flex items-center gap-3 p-3 bg-white rounded-lg border border-gray-300 hover:bg-gray-100 transition-colors"
              >
                <Copy className="w-5 h-5 text-gray-700" />
                <span className="text-sm text-gray-900">공지용 명단 복사</span>
              </button>

              {/* 변경사항 복사 */}
              <button
                onClick={handleCopyChanges}
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

              {/* 학기/주차 설정 */}
              <button
                onClick={handleSemesterSettings}
                className="w-full flex items-center gap-3 p-3 bg-white rounded-lg border border-gray-300 hover:bg-gray-100 transition-colors"
              >
                <Settings className="w-5 h-5 text-gray-700" />
                <span className="text-sm text-gray-900">학기/주차 설정</span>
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
      </div>
    </>
  );
}
