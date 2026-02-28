import { ChevronDown, Bell } from 'lucide-react';
import { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { toast } from 'sonner';
import { BoardTable } from './BoardTable';
import { AdminActionModal } from './AdminActionModal';
import { CancelSelectionModal } from './CancelSelectionModal';
import type { CategoryState, GuestCapacity, User } from '@/types';
import { useScheduleSystem, Category, type BoardEntry } from '@/hooks/useScheduleSystem';

type BoardType = '운동' | '잔여석' | '게스트' | '레슨';
type DayType = '수' | '금';

// ── (dayType, boardType) → Category 매핑 ─────────────────────

const CATEGORY_MAP: Record<string, Category> = {
  '수_운동': Category.WED_REGULAR,
  '수_게스트': Category.WED_GUEST,
  '수_잔여석': Category.WED_LEFTOVER,
  '수_레슨': Category.WED_LESSON,
  '금_운동': Category.FRI_REGULAR,
  '금_게스트': Category.FRI_GUEST,
  '금_잔여석': Category.FRI_LEFTOVER,
};

interface AccordionPanelProps {
  title: BoardType;
  isExpanded: boolean;
  onToggle: () => void;
  dayType: DayType;
  user: User | null;
  capacity?: number | GuestCapacity; // 정원 정보 (서버 응답에서 수신)
  /**
   * 서버에서 받아온 카테고리 상태
   * deadlineTimestamp: 절대 시각(Unix ms) → 폴링과 무관하게 클라이언트가 연속 계산
   */
  categoryState: CategoryState;
  onCountdownZero?: () => void;
  // 부모로부터 데이터와 리프레시 함수를 받음
  allApplications: Record<string, BoardEntry[]>;
  onActionSuccess: () => void;
  // ── 알림 설정 (레슨 제외 모든 패널) ──────────────────────────────────────
  /** 해당 요일의 정원 확정 여부 (False면 토글 비활성, 클릭 시 안내 Toast) */
  notifConfirmed?: boolean;
  /** 카테고리별 알림 On/Off 상태 맵 (백엔드 /api/notifications/status prefs) */
  notifPrefs?: Record<string, boolean>;
  /** 토글 성공 시 부모 상태 업데이트 콜백 */
  onNotifToggle?: (category: string, enabled: boolean) => void;
}

export function AccordionPanel({
  title,
  isExpanded,
  onToggle,
  dayType,
  user,
  capacity,
  categoryState,
  onCountdownZero,
  allApplications,
  onActionSuccess,
  notifConfirmed = false,
  notifPrefs = {},
  onNotifToggle,
}: AccordionPanelProps) {
  const { status, statusText, deadlineTimestamp } = categoryState;

  // ── useScheduleSystem: 액션(apply/cancel) 전용 ────
  // 현재 패널의 카테고리 판별 후, 부모가 준 전체 데이터에서 내 데이터만 꺼내오기!
  const category = CATEGORY_MAP[`${dayType}_${title}`] ?? Category.WED_REGULAR;
  const applications = allApplications[category] || []; // 렌더링에 사용
  // 이 패널의 카테고리에 해당하는 알림 On/Off 상태 (부모에서 받은 prefs 맵에서 추출)
  const notifEnabled = notifPrefs[category as string] ?? false;

  const { apply, cancel, adminApply, adminCancel } = useScheduleSystem(category);

  // 카운트다운 상태: deadlineTimestamp - Date.now() 로 직접 계산
  const [remainingMilliseconds, setRemainingMilliseconds] = useState(() =>
    Math.max(0, deadlineTimestamp - Date.now())
  );

  const hasCalledZeroRef = useRef(false);
  const onCountdownZeroRef = useRef(onCountdownZero);

  useEffect(() => {
    onCountdownZeroRef.current = onCountdownZero;
  });

  // 중복 제출 방어막: API 호출 진행 중 상태
  const [isApplying, setIsApplying] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);

  const [showParticipantModal, setShowParticipantModal] = useState(false);
  const [participantName, setParticipantName] = useState('');

  // 관리자 대리 신청/취소 모달
  const [showAdminModal, setShowAdminModal] = useState(false);
  const [adminActionType, setAdminActionType] = useState<'신청' | '취소'>('신청');

  // 취소 항목 선택 모달
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [cancelParticipants, setCancelParticipants] = useState<string[]>([]);
  // 관리자 대리 취소 흐름에서 확정 시 사용할 targetUserId 보관
  const [pendingAdminCancelUserId, setPendingAdminCancelUserId] = useState<string | null>(null);

  const isManager = user?.role === 'manager';

  // 상태에 따른 카운트다운 색상 결정
  const getCountdownColor = () => {
    switch (status) {
      case 'before-open': return 'text-blue-700';
      case 'open': return 'text-green-600';
      case 'cancel-period': return 'text-red-600';
      case 'waiting': return 'text-gray-600';
      default: return 'text-green-600';
    }
  };

  // 버튼 활성화 상태 결정 (manager는 status에 무관하게 항상 활성화)
  // 일반 유저는 반드시 로그인 상태(user 존재)여야 활성화
  const isApplyEnabled = isManager || (!!user && status === 'open');
  const isCancelEnabled = isManager || (!!user && (status === 'open' || status === 'cancel-period'));

  // 밀리초를 적절한 형식으로 변환
  const formatTime = (milliseconds: number) => {
    if (milliseconds <= 0) return '00:00:00';

    const totalSeconds = Math.floor(milliseconds / 1000);

    if (totalSeconds < 60) {
      const s = totalSeconds % 60;
      const ms = Math.floor((milliseconds % 1000) / 10);
      return `00:${String(s).padStart(2, '0')}.${String(ms).padStart(2, '0')}`;
    }

    const h = Math.floor(totalSeconds / 3600);
    const m = Math.floor((totalSeconds % 3600) / 60);
    const s = totalSeconds % 60;
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  };

  /**
   * 카운트다운 타이머
   */
  useEffect(() => {
    hasCalledZeroRef.current = false;

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
  }, [deadlineTimestamp]);

  // ── 1. 신청 버튼 핸들러 ─────────────────────────────────────────
  const handleApply = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isManager) {
      setAdminActionType('신청');
      setShowAdminModal(true);
      return;
    }

    // [직전 상태 검증] API 호출 전 토큰 유효성 재확인
    const token = localStorage.getItem('smash_token');
    if (!token) {
      alert('로그인 세션이 만료되었습니다. 다시 로그인해 주세요.');
      return;
    }

    if (title === '게스트' || title === '잔여석') {
      setShowParticipantModal(true);
    } else {
      // [중복 제출 방어] API 요청 시작 즉시 버튼 비활성화
      setIsApplying(true);
      try {
        const result = await apply();
        if (result.success) {
          alert('신청이 완료되었습니다.');
          onActionSuccess(); // ⭐️ 리프레시!
        } else {
          alert(`신청 실패: ${result.error}`);
        }
      } finally {
        // 성공/실패 후 1초 쿨타임으로 연속 클릭 방어
        setTimeout(() => setIsApplying(false), 1000);
      }
    }
  };

  // ── 2. 모달 제출 (참여자 본인 게스트/잔여석 신청 전용) ──────────
  const handleParticipantSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!participantName.trim()) return;

    const result = await apply({ guestName: participantName.trim() });

    if (result.success) {
      alert(`${title} 신청이 완료되었습니다.`);
      onActionSuccess(); // ⭐️ 리프레시!
    } else {
      alert(`신청 실패: ${result.error}`);
    }
    setParticipantName('');
    setShowParticipantModal(false);
  };

  // ── 3. 관리자 대리 신청/취소 모달 제출 ──────────────────────────────
  const handleAdminSubmit = async (targetUserId: string, guestName?: string) => {
    if (adminActionType === '신청') {
      const result = await adminApply(targetUserId, guestName);
      if (result.success) {
        alert(`[관리자] ${targetUserId} 대리 신청이 완료되었습니다.`);
        onActionSuccess(); // ⭐️ 리프레시!
      } else {
        alert(`신청 실패: ${result.error}`);
      }
    } else {
      // 취소 모드
      if (title === '게스트' || title === '잔여석') {
        // applications에서 guest_name이 있는 항목들을 추출해 선택 모달로 연결.
        // user_id는 백엔드에서 제거되므로 게스트 항목 전체를 목록으로 제공하고,
        // 선택 확정 후 adminCancel(targetUserId, selectedName) 호출로 백엔드가 소유권 검증.
        const participants = applications
          .filter((e) => e.guest_name)
          .map((e) => e.guest_name!);
        setPendingAdminCancelUserId(targetUserId);
        setCancelParticipants(participants);
        setShowCancelModal(true);
      } else {
        const result = await adminCancel(targetUserId);
        if (result.success) {
          alert(`[관리자] ${targetUserId} 대리 취소가 완료되었습니다.`);
          onActionSuccess(); // ⭐️ 리프레시!
        } else {
          alert(`취소 실패: ${result.error}`);
        }
      }
    }
  };

  // ── 4. 취소 버튼 핸들러 ─────────────────────────────────────────
  const handleCancel = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isManager) {
      setAdminActionType('취소');
      setShowAdminModal(true);
      return;
    }

    // [직전 상태 검증] API 호출 전 토큰 유효성 재확인
    const token = localStorage.getItem('smash_token');
    if (!token) {
      alert('로그인 세션이 만료되었습니다. 다시 로그인해 주세요.');
      return;
    }

    if (title === '게스트' || title === '잔여석') {
      // 현재 보드에서 본인 이름으로 신청된 항목의 guest_name 목록 추출.
      // 보드 응답에서 user_id는 제거되므로 entry.name === user.name 으로 본인 항목 식별.
      const participants = applications
        .filter((e) => e.name === user?.name && e.guest_name)
        .map((e) => e.guest_name!);
      setPendingAdminCancelUserId(null);
      setCancelParticipants(participants);
      setShowCancelModal(true);
    } else {
      if (!window.confirm(`${dayType}요일 ${title}을(를) 취소하시겠습니까?`)) return;
      // [중복 제출 방어] API 요청 시작 즉시 버튼 비활성화
      setIsCancelling(true);
      try {
        const result = await cancel();
        if (result.success) {
          alert('취소가 완료되었습니다.');
          onActionSuccess(); // ⭐️ 리프레시!
        } else {
          alert(`취소 실패: ${result.error}`);
        }
      } finally {
        // 성공/실패 후 1초 쿨타임으로 연속 클릭 방어
        setTimeout(() => setIsCancelling(false), 1000);
      }
    }
  };

  // ── 5. 취소 선택 모달 확정 핸들러 ──────────────────────────────────
  const handleCancelConfirm = async (selectedName: string) => {
    if (pendingAdminCancelUserId !== null) {
      // 관리자 대리 취소
      const result = await adminCancel(pendingAdminCancelUserId, selectedName);
      if (result.success) {
        alert(`[관리자] ${pendingAdminCancelUserId} 대리 취소가 완료되었습니다.`);
        onActionSuccess();
      } else {
        alert(`취소 실패: ${result.error}`);
      }
      setPendingAdminCancelUserId(null);
    } else {
      // 일반 회원 본인 취소
      const result = await cancel({ guestName: selectedName });
      if (result.success) {
        alert('취소가 완료되었습니다.');
        onActionSuccess();
      } else {
        alert(`취소 실패: ${result.error}`);
      }
    }
  };

  // ── 6. 알림 토글 핸들러 (레슨 제외 모든 패널) ───────────────────
  // - 정원 미확정(notifConfirmed=false): Toast 안내 후 종료
  // - 정원 확정(notifConfirmed=true): API 호출 → 성공 시 부모 상태 업데이트
  const handleNotification1Toggle = async (e: React.MouseEvent) => {
    e.stopPropagation();

    if (!user) return;

    if (!notifConfirmed) {
      toast('아직 정원이 확정되지 않았습니다.');
      return;
    }

    const categoryStr = category as string;
    const newEnabled = !notifEnabled;

    try {
      const res = await fetch('/api/notifications/toggle', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${user.token}`,
        },
        body: JSON.stringify({ category: categoryStr, enabled: newEnabled }),
      });

      if (res.ok) {
        onNotifToggle?.(categoryStr, newEnabled);  // 부모 notifStatus.prefs 업데이트
      } else {
        const data = await res.json();
        toast(data.message ?? '알림 설정에 실패했습니다.');
      }
    } catch {
      toast('네트워크 오류가 발생했습니다.');
    }
  };

  // ⭐️ [해결 핵심 포인트] 파서 에러를 막기 위해 JSX 밖에서 클래스 미리 계산
  const contentHeightClass = title === '운동' ? 'max-h-[560px]' : 'max-h-[500px]';
  const accordionVisibilityClass = isExpanded ? `${contentHeightClass} opacity-100` : 'max-h-0 opacity-0';

  // ── 화면 렌더링 (JSX) ─────────────────────────────────────────
  return (
    <div className="group relative bg-white/60 backdrop-blur-md border border-white/70 shadow-[0_8px_32px_rgba(0,0,0,0.1)] rounded-sm overflow-hidden transition-all duration-300 hover:shadow-[0_8px_32px_rgba(255,255,255,0.1)]">
      {isManager && (
        <AdminActionModal
          isOpen={showAdminModal}
          onClose={() => setShowAdminModal(false)}
          category={title}
          dayType={dayType}
          actionType={adminActionType}
          onSubmit={handleAdminSubmit}
        />
      )}

      {/* 취소 항목 선택 모달 (createPortal은 CancelSelectionModal 내부에서 처리) */}
      <CancelSelectionModal
        isOpen={showCancelModal}
        onClose={() => setShowCancelModal(false)}
        category={title}
        dayType={dayType}
        participants={cancelParticipants}
        onConfirm={handleCancelConfirm}
      />

      {/* 참여자 모달 (게스트/잔여석 신청 전용) */}
      {showParticipantModal && createPortal(
        <div className="fixed inset-0 bg-black/60 z-[60] flex items-center justify-center p-4">
          <div className="bg-white rounded-lg p-6 w-full max-w-sm shadow-2xl">
            <h3 className="text-lg font-bold text-gray-900 mb-4">
              운동참여인원 입력
            </h3>
            <form onSubmit={handleParticipantSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  참여인원 이름
                </label>
                <input
                  type="text"
                  value={participantName}
                  onChange={(e) => setParticipantName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1C5D99]"
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
                  className="flex-1 px-4 py-2 bg-[#C0D6DB] text-[#4F6D7A] rounded-lg hover:bg-[#A8C4CA] transition-colors font-medium"
                >
                  취소
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-[#C0D6DB] text-[#4F6D7A] rounded-lg hover:bg-[#A8C4CA] transition-colors font-medium"
                >
                  확인
                </button>
              </div>
            </form>
          </div>
        </div>,
        document.body
      )}

      {/* Accordion Header */}
      <div
        onClick={onToggle}
        className="w-full px-2 py-2.5 flex items-center justify-between hover:bg-white/20 transition-colors cursor-pointer"
      >
        <div className="flex items-center gap-1.5 min-w-0 flex-shrink-0">
          <ChevronDown
            className={`w-4 h-4 text-black transition-transform duration-200 flex-shrink-0 ${isExpanded ? 'rotate-180' : ''}`}
          />
          <span className="font-semibold text-sm text-black whitespace-nowrap">
            {title}
            {capacity != null && (
              typeof capacity === 'object'
                ? capacity.special_count > 0
                  ? `(${capacity.limit}+${capacity.special_count})`
                  : `(${capacity.limit})`
                : `(${capacity})`
            )}
          </span>
        </div>

        <div className="flex items-center gap-1.5 ml-1">
          {/* 알림 벨: 레슨 제외 모든 패널 + 로그인 상태에서만 표시 */}
          {title !== '레슨' && user && (
            <>
              <div className="flex gap-0.5">
                <button
                  onClick={handleNotification1Toggle}
                  className={`p-1 rounded-lg transition-colors relative ${notifConfirmed ? 'hover:bg-gray-100' : 'cursor-default opacity-50'
                    }`}
                  aria-label={notifEnabled ? '알림 끄기' : '알림 켜기'}
                  title={notifConfirmed ? undefined : '정원 확정 후 설정 가능'}
                >
                  <Bell
                    className={`w-4 h-4 ${notifEnabled ? 'text-[#1C5D99] fill-[#1C5D99]' : 'text-gray-400 fill-gray-400'}`}
                  />
                  {/* 알림 꺼짐: 사선 표시 */}
                  {!notifEnabled && (
                    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                      <div className="w-5 h-[1.5px] bg-gray-400 -rotate-45" />
                    </div>
                  )}
                </button>
              </div>

              <div className="w-px h-7 bg-gray-300" />
            </>
          )}

          <div className="flex flex-col items-end ml-1.5">
            <span className="text-[9px] leading-tight text-gray-700">{statusText}</span>
            <span className={`text-sm font-bold tabular-nums leading-tight ${getCountdownColor()}`}>
              {formatTime(remainingMilliseconds)}
            </span>
          </div>

          <div className="w-px h-7 bg-gray-300" />

          <div className="flex gap-2">
            <button
              onClick={handleCancel}
              disabled={!isCancelEnabled || isApplying || isCancelling}
              className={`px-2.5 py-1.5 rounded-lg text-xs font-bold border transition-all whitespace-nowrap ${isCancelEnabled && !isApplying && !isCancelling
                ? 'bg-[#EAEAEA] text-black border-[#EAEAEA] hover:bg-[#D5D5D5] active:bg-[#C0C0C0] cursor-pointer'
                : 'bg-[#EAEAEA]/20 text-gray-500 border-[#EAEAEA]/20 cursor-not-allowed opacity-40'
                }`}
            >
              {isCancelling ? '처리중...' : '취소'}
            </button>
            <button
              onClick={handleApply}
              disabled={!isApplyEnabled || isApplying || isCancelling}
              className={`px-2.5 py-1.5 rounded-lg text-xs font-bold border transition-all whitespace-nowrap ${isApplyEnabled && !isApplying && !isCancelling
                ? 'bg-[#EAEAEA] text-black border-[#EAEAEA] hover:bg-[#D5D5D5] active:bg-[#C0C0C0] cursor-pointer'
                : 'bg-[#EAEAEA]/20 text-gray-500 border-[#EAEAEA]/20 cursor-not-allowed opacity-40'
                }`}
            >
              {isApplying ? '처리중...' : '신청'}
            </button>
          </div>
        </div>
      </div>

      {/* Accordion Content */}
      <div
        className={`accordion-content overflow-hidden transition-all duration-500 linear ${accordionVisibilityClass}`}
      >
        <div className="pb-4">
          <BoardTable type={title} applications={applications} highlightCount={
            capacity == null
              ? undefined
              : typeof capacity === 'object'
                ? capacity.limit + capacity.special_count
                : capacity
          } />
        </div>
      </div>
    </div>
  );
}
