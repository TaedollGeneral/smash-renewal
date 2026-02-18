import { useState, useRef, useCallback, useEffect } from 'react';
import { Header } from '@/components/Header';
import { AccordionPanel } from '@/components/AccordionPanel';
import { Sidebar } from '@/components/Sidebar';
import type { DayType, BoardType, User, Capacity, CategoryState } from '@/types';


function App() {
  const [currentDay, setCurrentDay] = useState<DayType>('수');
  const [expandedPanels, setExpandedPanels] = useState<Set<BoardType>>(new Set());
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

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

  /**
   * 정원 상태
   * - 초기값: undefined (서버 응답 전까지 로딩 처리)
   */
  const [capacities, setCapacities] = useState<Capacity>({ 수: undefined, 금: undefined });

  // Pull-to-refresh 상태 관리
  const [isPulling, setIsPulling] = useState(false);
  const [pullDistance, setPullDistance] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const touchStartY = useRef(0);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

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
  const fetchCapacities = useCallback(async () => {
    try {
      const response = await fetch(`/api/capacities`);
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
    try {
      const response = await fetch(`/api/category-states`);
      if (!response.ok) throw new Error('Network response was not ok');

      const data = await response.json();
      setCategoryStates(data);
      console.log('[상태/카운트다운] 갱신 성공:', new Date().toLocaleTimeString());
    } catch (error) {
      console.error('[상태/카운트다운] 갱신 실패:', error);
    }
  }, []);

  // ─── 3. 게시판 현황 fetch (실제 서버 호출) ──────────────────────────────────
  // 폴링: 2초에 한번 + soft refresh
  const fetchBoardData = useCallback(async () => {
    try {
      const response = await fetch(`/api/board-data`);
      if (!response.ok) throw new Error('Network response was not ok');

      // const data = await response.json();
      // setBoardData(data); // TODO: BoardData 상태 생성 후 주석 해제하여 연결
      console.log('[게시판 현황] 갱신 성공:', new Date().toLocaleTimeString());
    } catch (error) {
      console.error('[게시판 현황] 갱신 실패:', error);
    }
  }, []);

  // ─── 폴링 인터벌 설정 ───────────────────────────────────────────────────────

  // 정원: 5분마다
  useEffect(() => {
    fetchCapacities();
    const id = setInterval(fetchCapacities, 5 * 60 * 1000);
    return () => clearInterval(id);
  }, [fetchCapacities]);

  // 카운트다운/상태: 5분마다
  useEffect(() => {
    fetchCategoryStates();
    const id = setInterval(fetchCategoryStates, 5 * 60 * 1000);
    return () => clearInterval(id);
  }, [fetchCategoryStates]);

  // 게시판 현황: 2초마다
  useEffect(() => {
    fetchBoardData();
    const id = setInterval(fetchBoardData, 2000);
    return () => clearInterval(id);
  }, [fetchBoardData]);

  // ─── 카운트다운 0 도달 시 핸들러 ────────────────────────────────────────────
  const handleCountdownZero = (dayType: DayType, category: BoardType) => {
    console.log(`[카운트다운] ${dayType}요일 ${category} 종료 → 상태 즉시 갱신 요청`);
    fetchCategoryStates();
  };

  // ─── Soft refresh: 세 가지 데이터 모두 즉시 갱신 ────────────────────────────
  const handleSoftRefresh = async () => {
    setIsRefreshing(true);
    console.log('[Soft refresh] 시작');
    try {
      await Promise.all([
        fetchCapacities(),
        fetchCategoryStates(),
        fetchBoardData(),
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
    const el = scrollContainerRef.current;
    if (!el || el.scrollTop > 0) return;
    touchStartY.current = e.touches[0].clientY;
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    const el = scrollContainerRef.current;
    if (!el || el.scrollTop > 0 || isRefreshing) return;
    const distance = e.touches[0].clientY - touchStartY.current;
    if (distance > 0) {
      setIsPulling(true);
      setPullDistance(Math.min(distance * 0.5, 120));
    }
  };

  const handleTouchEnd = () => {
    if (pullDistance > 60 && !isRefreshing) {
      handleSoftRefresh();
    } else {
      setIsPulling(false);
      setPullDistance(0);
    }
  };

  const handleCapacitiesChange = (newCapacities: Capacity) => {
    setCapacities(newCapacities);
    // TODO: 백엔드 API 호출 (임원진 정원 확정)
  };

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
    <div className="flex flex-col h-screen bg-gray-100">
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
        {/* Pull-to-refresh indicator */}
        <div
          className="absolute top-0 left-0 right-0 flex items-center justify-center overflow-hidden transition-all duration-200"
          style={{
            height: `${pullDistance}px`,
            opacity: isPulling || isRefreshing ? 1 : 0,
          }}
        >
          <div className="flex items-center gap-2 text-gray-600">
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
          className="flex flex-col"
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
              capacity={panel === '운동' ? capacities[currentDay] : undefined}
              categoryState={categoryStates[currentDay][panel]}
              onCountdownZero={() => handleCountdownZero(currentDay, panel)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

export default App;