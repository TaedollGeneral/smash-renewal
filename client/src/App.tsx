import { useState, useRef, useCallback, useEffect, useMemo } from 'react';
import { Toaster } from 'sonner';
import { ClipboardList } from 'lucide-react';
import { Header } from '@/components/Header';
import { AccordionPanel } from '@/components/AccordionPanel';
import { Sidebar } from '@/components/Sidebar';
import { ExerciseListModal } from '@/components/ExerciseListModal';
import { buildExerciseListText } from '@/lib/buildExerciseListText';
import type { DayType, BoardType, User, Capacity, CapacityDetails, CategoryState, NotifStatus } from '@/types';
import { fetchAllBoardData, type BoardEntry } from '@/hooks/useScheduleSystem';
import { usePushNotifications } from '@/hooks/usePushNotifications';
import { fetchWithAuth } from '@/lib/fetchWithAuth';


function App() {
  const [currentDay, setCurrentDay] = useState<DayType>('수');
  const [expandedPanels, setExpandedPanels] = useState<Set<BoardType>>(new Set());
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isListModalOpen, setIsListModalOpen] = useState(false);

  // 사용자 정보 상태 (로컬 스토리지 연동)
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('smash_user');
    if (saved) {
      try {
        return JSON.parse(saved) as User;
      } catch {
        return null;
      }
    }
    return null;
  });

  // ─── 알림 상태 (수/금 확정 여부 + 본인 알림 On/Off) ─────────────────────────
  const [notifStatus, setNotifStatus] = useState<NotifStatus | null>(null);
  const { registerPush } = usePushNotifications();

  // /api/notifications/status 조회
  const fetchNotifStatus = useCallback(async (token: string) => {
    try {
      const res = await fetchWithAuth('/api/notifications/status', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) setNotifStatus(await res.json());
    } catch (err) {
      console.warn('[알림 상태] 조회 실패:', err);
    }
  }, []);

  // 로그인 완료 또는 페이지 로드 시:
  //   1) PWA 알림 권한 요청 + 구독 등록 (UPSERT로 멱등)
  //   2) 알림 설정 상태 초기 조회
  // 로그아웃 시: notifStatus 초기화
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (user) {
      registerPush(user.token);
      fetchNotifStatus(user.token);
    } else {
      setNotifStatus(null);
    }
  }, [user]);

  // 알림 On/Off 토글 성공 시 부모 상태 업데이트 (AccordionPanel → App)
  const handleNotifToggle = useCallback((category: string, enabled: boolean) => {
    setNotifStatus((prev) =>
      prev ? { ...prev, prefs: { ...prev.prefs, [category]: enabled } } : null
    );
  }, []);

  // JWT 토큰 만료 체크
  useEffect(() => {
    const token = localStorage.getItem('smash_token');
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        if (payload.exp * 1000 < Date.now()) {
          localStorage.removeItem('smash_token');
          localStorage.removeItem('smash_user');
          setUser(null);
        }
      } catch {
        localStorage.removeItem('smash_token');
        localStorage.removeItem('smash_user');
        setUser(null);
      }
    }
  }, []);

  // 전역 401 자동 로그아웃 핸들러
  // fetchWithAuth가 401 응답을 받으면 'auth:logout' 이벤트를 dispatch하고,
  // 여기서 localStorage와 user 상태를 초기화하여 로그인 화면으로 전환한다.
  const forceLogout = useCallback(() => {
    localStorage.removeItem('smash_token');
    localStorage.removeItem('smash_user');
    setUser(null);
  }, []);

  useEffect(() => {
    window.addEventListener('auth:logout', forceLogout);
    return () => window.removeEventListener('auth:logout', forceLogout);
  }, [forceLogout]);

  /**
   * 정원 상태
   * - 초기값: undefined (서버 응답 전까지 로딩 처리)
   */
  const [capacities, setCapacities] = useState<Capacity>({ 수: null, 금: null });

  // Pull-to-refresh 상태 관리
  const [isPulling, setIsPulling] = useState(false);
  const [pullDistance, setPullDistance] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const touchStartY = useRef(0);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // 브라우저 네이티브 오버스크롤 차단:
  // React의 onTouchMove는 passive:true로 등록되어 preventDefault()가 동작하지 않음
  // → native addEventListener로 passive:false 리스너 별도 등록
  useEffect(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    const preventOverscroll = (e: TouchEvent) => {
      if (touchStartY.current === 0) return;
      const touchY = e.touches[0].clientY;
      const movingDown = touchY > touchStartY.current; // 손가락 아래로 = 위쪽 오버스크롤
      const movingUp = touchY < touchStartY.current;   // 손가락 위로 = 아래쪽 오버스크롤

      // 중첩 스크롤 영역(board 테이블 등)이 아직 스크롤 가능하면 허용
      const target = e.target as HTMLElement;
      const scrollableChild = target.closest('.board-table-scroll') as HTMLElement | null;
      if (scrollableChild) {
        const childAtTop = scrollableChild.scrollTop <= 0;
        const childAtBottom = scrollableChild.scrollTop + scrollableChild.clientHeight >= scrollableChild.scrollHeight - 1;
        // board 내부에서 아직 스크롤할 수 있으면 기본 동작 허용
        if (movingDown && !childAtTop) return;
        if (movingUp && !childAtBottom) return;
      }

      // 메인 스크롤 컨테이너 경계에서 오버스크롤 차단
      const atTop = el.scrollTop <= 0;
      const atBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 1;
      if ((atTop && movingDown) || (atBottom && movingUp)) {
        e.preventDefault();
      }
    };
    el.addEventListener('touchmove', preventOverscroll, { passive: false });
    return () => el.removeEventListener('touchmove', preventOverscroll);
  }, []);

  // 스크롤 컨테이너 바깥 영역(헤더 등)에서의 터치 드래그로 인한 PWA 오버스크롤 차단
  useEffect(() => {
    const preventDocumentOverscroll = (e: TouchEvent) => {
      const el = scrollContainerRef.current;
      // 스크롤 컨테이너 내부 이벤트는 위 핸들러가 처리
      if (el && el.contains(e.target as Node)) return;
      // 사이드바 등 별도 스크롤 영역은 허용
      const target = e.target as HTMLElement;
      if (target.closest('[data-scrollable], .overflow-y-auto')) return;
      e.preventDefault();
    };
    document.addEventListener('touchmove', preventDocumentOverscroll, { passive: false });
    return () => document.removeEventListener('touchmove', preventDocumentOverscroll);
  }, []);

  /**
   * 카테고리별 상태 정보 (Status & Countdown)
   * - 초기값: 로딩 중 상태 (waiting)
   * - 서버에서 status, statusText, deadlineTimestamp를 모두 받아옴
   */
  const [categoryStates, setCategoryStates] = useState<Record<DayType, Record<BoardType, CategoryState>>>({
    '수': {
      '운동': { status: 'waiting', statusText: '로딩중...', deadlineTimestamp: 0 },
      '게스트': { status: 'waiting', statusText: '로딩중...', deadlineTimestamp: 0 },
      '레슨': { status: 'waiting', statusText: '로딩중...', deadlineTimestamp: 0 },
      '잔여석': { status: 'waiting', statusText: '로딩중...', deadlineTimestamp: 0 },
    },
    '금': {
      '운동': { status: 'waiting', statusText: '로딩중...', deadlineTimestamp: 0 },
      '게스트': { status: 'waiting', statusText: '로딩중...', deadlineTimestamp: 0 },
      '레슨': { status: 'waiting', statusText: '로딩중...', deadlineTimestamp: 0 }, // 타입 호환용
      '잔여석': { status: 'waiting', statusText: '로딩중...', deadlineTimestamp: 0 },
    },
  });

  // ─── 1. 정원 fetch (실제 서버 호출) ─────────────────────────────────────────
  // 폴링: 5분에 한번 + soft refresh
  const [allApplications, setAllApplications] = useState<Record<string, BoardEntry[]>>({});

  // category → (dayType, boardType) 역매핑 (userAlreadyApplied를 categoryStates에 병합하기 위함)
  const CAT_TO_DAY_PANEL: Record<string, [DayType, BoardType]> = {
    'WED_REGULAR':  ['수', '운동'],
    'WED_GUEST':    ['수', '게스트'],
    'WED_LEFTOVER': ['수', '잔여석'],
    'WED_LESSON':   ['수', '레슨'],
    'FRI_REGULAR':  ['금', '운동'],
    'FRI_GUEST':    ['금', '게스트'],
    'FRI_LEFTOVER': ['금', '잔여석'],
  };

  // ⭐️ 배치 API: 7개 개별 요청 → 1회 /api/all-boards 호출로 통합
  const [boardOverloaded, setBoardOverloaded] = useState(false);
  const fetchAllBoards = useCallback(async () => {
    if (!localStorage.getItem('smash_token')) return;
    try {
      const { applications, userApplied, overloaded } = await fetchAllBoardData();
      // 서킷 브레이커 발동 시: 기존 데이터 유지, overloaded 플래그만 설정
      if (overloaded) {
        setBoardOverloaded(true);
        console.log('[게시판 데이터] 서버 과부하 — 기존 데이터 유지');
        return;
      }
      setBoardOverloaded(false);
      setAllApplications(applications);
      // 신청 여부를 categoryStates에 병합 (별도 API 호출 없이 기존 응답 재활용)
      setCategoryStates(prev => {
        const next = structuredClone(prev) as typeof prev;
        for (const [cat, applied] of Object.entries(userApplied)) {
          const mapping = CAT_TO_DAY_PANEL[cat];
          if (mapping) {
            const [day, panel] = mapping;
            next[day][panel] = { ...next[day][panel], userAlreadyApplied: applied };
          }
        }
        return next;
      });
      console.log('[게시판 데이터] 갱신 완료');
    } catch (error) {
      console.error('[게시판 데이터] 갱신 실패:', error);
    }
  }, []);

  // ⭐️ 초기 1회 로드 (로그인 시)
  useEffect(() => {
    if (user) fetchAllBoards();
  }, [user, fetchAllBoards]);

  const fetchCapacities = useCallback(async () => {
    const token = localStorage.getItem('smash_token');
    if (!token) return;
    try {
      const response = await fetchWithAuth(`/api/capacities`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error('Network response was not ok');

      const data = await response.json();
      setCapacities(data);
      console.log('[정원] 갱신 성공:', new Date().toLocaleTimeString());
    } catch (error) {
      console.error('[정원] 갱신 실패:', error);
    }
  }, []);

  // ─── 2. 카운트다운/상태 fetch (실제 서버 호출) ──────────────────────────────
  // 폴링: 5분에 한번 + soft refresh + 카운트다운 종료 시
  const fetchCategoryStates = useCallback(async () => {
    const token = localStorage.getItem('smash_token');
    if (!token) return;
    try {
      const response = await fetchWithAuth(`/api/category-states`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error('Network response was not ok');

      const data = await response.json();
      setCategoryStates(data);
      console.log('[상태/카운트다운] 갱신 성공:', new Date().toLocaleTimeString());
    } catch (error) {
      console.error('[상태/카운트다운] 갱신 실패:', error);
    }
  }, []);

  // ─── 폴링 인터벌 설정 ───────────────────────────────────────────────────────
  // 게시판 현황 폴링은 각 AccordionPanel 내 useScheduleSystem 훅이 담당

  // 정원: 10분마다 (로그인 상태에서만)
  useEffect(() => {
    if (!user) return;
    fetchCapacities();
    const id = setInterval(fetchCapacities, 10 * 60 * 1000);
    return () => clearInterval(id);
  }, [user, fetchCapacities]);

  // 카운트다운/상태: 5분마다 (로그인 상태에서만)
  useEffect(() => {
    if (!user) return;
    fetchCategoryStates();
    const id = setInterval(fetchCategoryStates, 5 * 60 * 1000);
    return () => clearInterval(id);
  }, [user, fetchCategoryStates]);

  // ─── 카운트다운 0 도달 시 핸들러 (디바운스 + 랜덤 지터) ─────────────────────
  // 동일 정각에 여러 패널이 동시에 카운트다운 0에 도달하면 중복 호출 방지 (2초 디바운스).
  // 랜덤 지터(0~500ms)로 212명 동시 접속 시 Thundering Herd 현상을 완화한다.
  const lastCountdownFetchRef = useRef(0);

  const graceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleCountdownZero = (dayType: DayType, category: BoardType) => {
    const now = Date.now();
    if (now - lastCountdownFetchRef.current < 2000) return;
    lastCountdownFetchRef.current = now;

    // 카운트다운 0 → 5초간 게시판 "집계중" 표시, 조회 차단
    setBoardOverloaded(true);

    const jitter = Math.random() * 500;
    console.log(`[카운트다운] ${dayType}요일 ${category} 종료 → 상태 즉시 갱신, 게시판 5초 후 갱신`);

    // 카테고리 상태(버튼 활성화/카운트다운)는 즉시 갱신
    setTimeout(() => fetchCategoryStates(), jitter);

    // 게시판 명단 조회는 5초 후
    if (graceTimerRef.current) clearTimeout(graceTimerRef.current);
    graceTimerRef.current = setTimeout(() => {
      fetchAllBoards();
      graceTimerRef.current = null;
    }, 5000);
  };

  // ─── Soft refresh: 세 가지 데이터 모두 즉시 갱신 ────────────────────────────
  const handleSoftRefresh = async () => {
    setIsRefreshing(true);
    console.log('[Soft refresh] 시작');
    try {
      await Promise.all([
        fetchCapacities(),
        fetchCategoryStates(),
        fetchAllBoards(),
      ]);
      console.log('[Soft refresh] 완료');
    } catch (error) {
      console.error('[Soft refresh] 실패:', error);
    } finally {
      setTimeout(() => {
        setIsRefreshing(false);
        setPullDistance(0);
        setIsPulling(false);
      }, 500);
    }
  };

  // Pull-to-refresh 터치 핸들러
  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartY.current = e.touches[0].clientY;
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    const el = scrollContainerRef.current;
    if (!el || el.scrollTop > 0 || isRefreshing || touchStartY.current === 0) return;
    const distance = e.touches[0].clientY - touchStartY.current;
    // 20px 데드존: 의도치 않은 미세한 터치 무시
    if (distance > 20) {
      setIsPulling(true);
      // 저항 계수 0.3으로 낮춤 (기존 0.5 → 더 많이 당겨야 같은 거리)
      setPullDistance(Math.min((distance - 20) * 0.3, 120));
    }
  };

  const handleTouchEnd = () => {
    touchStartY.current = 0;
    // 트리거 임계값 90px로 상향 (기존 60px)
    if (pullDistance > 70 && !isRefreshing) {
      handleSoftRefresh();
    } else {
      setIsPulling(false);
      setPullDistance(0);
    }
  };

  const handleCapacitiesChange = async (newCapacities: { 수?: number; 금?: number }) => {
    try {
      const token = localStorage.getItem('smash_token') ?? '';

      // total 숫자만 추출하여 전송
      const payload: Record<string, number> = {};
      // Number()로 감싸서 문자열이 섞여 있어도 확실하게 숫자로 변환 후 전송
      if (newCapacities.수 != null) payload['수'] = Number(newCapacities.수);
      if (newCapacities.금 != null) payload['금'] = Number(newCapacities.금);

      const response = await fetchWithAuth('/api/admin/capacity', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error ?? '정원 확정에 실패했습니다.');
      }

      // 서버 응답의 상세 포맷 데이터를 기존 상태에 병합
      // (한쪽 요일만 전송 시 다른 요일이 null로 올 수 있으므로 덮어쓰기 방지)
      const data = await response.json();
      setCapacities(prev => {
        const merged = { ...prev };
        for (const [day, value] of Object.entries(data.capacities)) {
          if (value != null) merged[day as keyof typeof merged] = value as typeof merged[keyof typeof merged];
        }
        return merged;
      });

      // 정원 확정 후 알림 상태(confirmed 플래그) 즉시 갱신
      // — 이 호출이 없으면 notifStatus.wed/fri_confirmed가 false로 남아
      //   벨 버튼이 비활성 상태를 유지하여 사용자가 카테고리 알림을 구독할 수 없음
      if (token) {
        fetchNotifStatus(token);
      }
    } catch (error) {
      console.error('[정원 확정] API 호출 실패:', error);
      alert(error instanceof Error ? error.message : '정원 확정에 실패했습니다.');
      fetchCapacities(); // 서버 상태로 되돌리기
    }
  };

  // 현재 페이지(수/금)의 확정 명단 텍스트 — 프론트엔드에서 계산
  const exerciseListText = useMemo(
    () => buildExerciseListText(currentDay, allApplications, capacities),
    [currentDay, allApplications, capacities],
  );

  const accordionPanels: Record<DayType, BoardType[]> = {
    '수': ['운동', '게스트', '레슨', '잔여석'],
    '금': ['운동', '게스트', '잔여석'],
  };

  const togglePanel = (panel: BoardType) => {
    const newExpanded = new Set(expandedPanels);
    if (newExpanded.has(panel)) {
      newExpanded.delete(panel);
    } else {
      newExpanded.add(panel);
    }
    setExpandedPanels(newExpanded);
  };

  return (
    <>
      {/* Sonner 토스트 컨테이너 — AccordionPanel의 toast() 호출이 여기서 렌더됨 */}
      <Toaster position="top-center" richColors />
      <div className="flex flex-col h-[100dvh] bg-[#1C5D99] relative">
        {/* Background texture layer */}
        <div className="absolute inset-0 pointer-events-none z-0 overflow-hidden">
          {/* Radial gradient mesh — 자연스러운 빛의 깊이감 */}
          <div
            className="absolute inset-0"
            style={{
              background: `
                radial-gradient(ellipse 90% 55% at 15% 5%, rgba(79, 134, 198, 0.45) 0%, transparent 65%),
                radial-gradient(ellipse 55% 45% at 85% 95%, rgba(28, 93, 153, 0.35) 0%, transparent 60%)
              `,
            }}
          />
          {/* Ultra-subtle film grain — opacity 0.05, 낮은 baseFrequency */}
          <div
            className="absolute inset-0"
            style={{
              opacity: 0.05,
              backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='grain'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23grain)'/%3E%3C/svg%3E")`,
              backgroundRepeat: 'repeat',
              backgroundSize: '256px 256px',
            }}
          />
          {/* Top vignette */}
          <div
            className="absolute inset-0"
            style={{
              background: 'linear-gradient(180deg, rgba(0,0,0,0.06) 0%, transparent 140px)',
            }}
          />
        </div>
        <Sidebar
          isOpen={isSidebarOpen}
          onClose={() => setIsSidebarOpen(false)}
          user={user}
          setUser={setUser}
          capacities={capacities}
          onCapacitiesChange={handleCapacitiesChange}
        />

        <Header
          currentDay={currentDay}
          onDayChange={setCurrentDay}
          onMenuClick={() => setIsSidebarOpen(true)}
          user={user}
        />

        {/* Main Content - Scrollable */}
        <div
          className="flex-1 overflow-y-auto relative"
          ref={scrollContainerRef}
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleTouchEnd}
        >
          {!user ? (
            /* 비로그인 상태: 로그인 안내 */
            <div className="flex flex-col items-center justify-center h-full text-white/80 px-6">
              <svg className="w-16 h-16 mb-4 opacity-60" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
              </svg>
              <p className="text-lg font-semibold mb-1">로그인이 필요합니다</p>
              <p className="text-sm text-white/60">좌측 상단 메뉴에서 로그인해주세요.</p>
            </div>
          ) : (
            <>
              {/* Pull-to-refresh indicator */}
              <div
                className="absolute top-0 left-0 right-0 flex items-center justify-center overflow-hidden transition-all duration-200"
                style={{
                  height: `${pullDistance}px`,
                  opacity: isPulling || isRefreshing ? 1 : 0,
                }}
              >
                <div className="flex items-center gap-2 text-white">
                  <svg
                    className={`w-5 h-5 ${isRefreshing ? 'animate-spin' : ''}`}
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                    />
                  </svg>
                  <span className="text-sm font-medium">
                    {isRefreshing
                      ? '새로고침 중...'
                      : pullDistance > 60
                        ? '놓아서 새로고침'
                        : '아래로 당겨서 새로고침'}
                  </span>
                </div>
              </div>

              <div
                className="flex flex-col gap-2 p-2 pb-20"
                style={{
                  transform: `translateY(${isPulling || isRefreshing ? pullDistance : 0}px)`,
                  transition: isPulling ? 'none' : 'transform 0.3s ease-out',
                }}
              >
                {accordionPanels[currentDay].map((panel) => (
                  <AccordionPanel
                    key={`${currentDay}-${panel}`}
                    title={panel}
                    isExpanded={expandedPanels.has(panel)}
                    onToggle={() => togglePanel(panel)}
                    dayType={currentDay}
                    user={user}
                    capacity={capacities[currentDay]?.details?.[panel as keyof CapacityDetails]}
                    categoryState={categoryStates[currentDay][panel]}
                    onCountdownZero={() => handleCountdownZero(currentDay, panel)}
                    allApplications={allApplications}
                    onActionSuccess={fetchAllBoards}
                    boardOverloaded={boardOverloaded}
                    notifConfirmed={currentDay === '수' ? (notifStatus?.wed_confirmed ?? false) : (notifStatus?.fri_confirmed ?? false)}
                    notifPrefs={notifStatus?.prefs ?? {}}
                    onNotifToggle={handleNotifToggle}
                  />
                ))}
              </div>
            </>
          )}
        </div>

      </div>

      {/* Floating Action Button — 확정 명단 보기 */}
      {user && (
        <button
          onClick={() => setIsListModalOpen(true)}
          className="fixed bottom-5 right-4 z-[200] w-12 h-12 rounded-full bg-white flex items-center justify-center hover:scale-110 active:scale-95 transition-all duration-200"
          style={{ boxShadow: '0 6px 24px rgba(0,0,0,0.25), 0 2px 8px rgba(28,93,153,0.3)' }}
          aria-label="확정 명단 보기"
        >
          <ClipboardList className="w-5 h-5 text-[#1C5D99]" strokeWidth={2.5} />
        </button>
      )}

      {/* 확정 명단 모달 */}
      <ExerciseListModal
        isOpen={isListModalOpen}
        onClose={() => setIsListModalOpen(false)}
        dayType={currentDay}
        formattedText={exerciseListText}
      />

    </>
  );
}

export default App;