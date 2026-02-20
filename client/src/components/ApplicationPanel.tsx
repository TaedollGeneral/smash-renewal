import { useState } from 'react';
import type { BoardType, ActionType, DayType, User } from '@/types';
import { Category } from '@/hooks/useScheduleSystem';
import { AdminActionModal } from './AdminActionModal';

interface ApplicationPanelProps {
  availablePanels: BoardType[];
  dayType: DayType;
  user: User | null;
}

// ── (dayType, boardType) → Category 매핑 ─────────────────────

const CATEGORY_MAP: Record<string, Category> = {
  '수_운동':   Category.WED_REGULAR,
  '수_게스트': Category.WED_GUEST,
  '수_잔여석': Category.WED_LEFTOVER,
  '수_레슨':   Category.WED_LESSON,
  '금_운동':   Category.FRI_REGULAR,
  '금_게스트': Category.FRI_GUEST,
  '금_잔여석': Category.FRI_LEFTOVER,
};

function toCategoryKey(dayType: DayType, boardType: BoardType): Category {
  return CATEGORY_MAP[`${dayType}_${boardType}`] ?? Category.WED_REGULAR;
}

// ── useScheduleSystem과 동일한 API 호출 헬퍼 ─────────────────

async function callApi(
  endpoint: '/apply' | '/cancel',
  category: Category,
  options?: { target_user_id?: string; guest_name?: string },
): Promise<{ success: boolean; error?: string }> {
  try {
    const body: Record<string, string> = { category };
    if (options?.target_user_id) body.target_user_id = options.target_user_id;
    if (options?.guest_name) body.guest_name = options.guest_name;

    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify(body),
    });
    const data = await res.json();

    if (!res.ok) {
      return { success: false, error: data.error ?? '요청에 실패했습니다.' };
    }
    return { success: true };
  } catch (err) {
    return {
      success: false,
      error: err instanceof Error ? err.message : '네트워크 오류',
    };
  }
}

// ── Component ─────────────────────────────────────────────────

export function ApplicationPanel({ availablePanels, dayType, user }: ApplicationPanelProps) {
  const [selectedBoard, setSelectedBoard] = useState<BoardType>(availablePanels[0]);
  const [action, setAction] = useState<ActionType>('신청');
  const [participants, setParticipants] = useState('');
  const [showAdminModal, setShowAdminModal] = useState(false);

  const isManager = user?.role === 'manager';
  const isWedOrFri = dayType === '수' || dayType === '금';
  const showParticipantsInput = selectedBoard === '게스트' || selectedBoard === '잔여석';

  // ── 확인 버튼 클릭 ─────────────────────────────────────────

  const handleSubmit = async () => {
    // 매니저 + 수/금 → 대리 모달 열기
    if (isManager && isWedOrFri) {
      setShowAdminModal(true);
      return;
    }

    // 일반 회원 또는 기타 요일 매니저 → 본인 기준 바로 API 호출
    const category = toCategoryKey(dayType, selectedBoard);
    const endpoint = action === '신청' ? '/apply' : '/cancel';
    const options: { guest_name?: string } = {};
    if (showParticipantsInput && participants.trim()) {
      options.guest_name = participants.trim();
    }

    const result = await callApi(endpoint, category, options);
    if (result.success) {
      alert(`${action} 요청이 처리되었습니다.`);
      setParticipants('');
    } else {
      alert(`${action} 실패: ${result.error}`);
    }
  };

  // ── AdminActionModal 콜백: 대리 신청/취소 API 호출 ─────────

  const handleAdminSubmit = async (targetUserId: string) => {
    const category = toCategoryKey(dayType, selectedBoard);
    const endpoint = action === '신청' ? '/apply' : '/cancel';
    const options: { target_user_id: string; guest_name?: string } = {
      target_user_id: targetUserId,
    };
    if (showParticipantsInput && participants.trim()) {
      options.guest_name = participants.trim();
    }

    const result = await callApi(endpoint, category, options);
    if (result.success) {
      alert(`[관리자] ${targetUserId}님의 ${dayType}요일 ${selectedBoard} ${action} 요청이 처리되었습니다.`);
      setParticipants('');
    } else {
      alert(`${action} 실패: ${result.error}`);
    }
  };

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-gray-50 rounded-t-3xl shadow-2xl z-50 border-t border-gray-300">
      {/* 매니저 대리 신청/취소 모달 (수/금 전용) */}
      {isManager && isWedOrFri && (
        <AdminActionModal
          isOpen={showAdminModal}
          onClose={() => setShowAdminModal(false)}
          category={selectedBoard}
          dayType={dayType}
          actionType={action}
          onSubmit={handleAdminSubmit}
        />
      )}

      <div className="p-3 sm:p-4">
        {/* Single Row: Board Selection + Action Buttons + Participants (conditional) + Submit Button */}
        <div className="flex gap-2 items-center">
          <select
            value={selectedBoard}
            onChange={(e) => setSelectedBoard(e.target.value as BoardType)}
            className="w-24 sm:w-28 px-2 sm:px-3 py-2 border border-gray-400 rounded-lg text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-gray-500 bg-white"
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

          {showParticipantsInput && (
            <input
              type="text"
              placeholder="인원"
              value={participants}
              onChange={(e) => setParticipants(e.target.value)}
              className="w-16 sm:w-20 px-2 py-2 border border-gray-400 rounded-lg text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-gray-500"
            />
          )}

          <button
            onClick={handleSubmit}
            className="ml-auto px-6 sm:px-8 bg-gray-700 text-white font-semibold rounded-lg hover:bg-gray-800 active:bg-gray-900 transition-colors text-xs sm:text-sm whitespace-nowrap h-[38px]"
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
