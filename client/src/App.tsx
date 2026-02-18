import { useState, useRef, useCallback, useEffect } from 'react';
import { Header } from '@/components/Header';
import { AccordionPanel } from '@/components/AccordionPanel';
import { Sidebar } from '@/components/Sidebar';
import type { DayType, BoardType, User, Capacity, CategoryState, StatusType } from '@/types';

// ─── 서버 API 엔드포인트 (실제 구현 시 참고) ────────────────────────────────
// GET /api/capacities?semester=&week=        → { 수: number, 금: number }
//   폴링 주기: 5분, soft refresh
//
// GET /api/category-states?semester=&week=  → Record<DayType, Record<BoardType, {
//                                               status: StatusType,
//                                               statusText: string,
//                                               deadlineTimestamp: number  ← 절대 시각(Unix ms)
//                                             }>>
//   폴링 주기: 5분, soft refresh, 카운트다운=0
//
// GET /api/board-data?semester=&week=        → 게시판 현황 (신청자 목록 등)
//   폴링 주기: 2초, soft refresh
// ────────────────────────────────────────────────────────────────────────────

/**
 * Mock 정원 (고정값) — 컴포넌트 외부에 정의하여 렌더마다 재생성되지 않도록 함
 * 실서버 연동 시: fetchCapacities() 내에서 API 응답으로 대체
 */
const MOCK_CAPACITIES: Capacity = { 수: 12, 금: 14 };

/**
 * 마감 타임스탬프로부터 CategoryState를 계산하는 헬퍼 (Mock 전용)
 * 실제 서버에서는 status/statusText를 함께 내려줌
 */
function computeStateFromDeadline(deadlineTimestamp: number): CategoryState {
  const remainingSeconds = Math.max(0, Math.floor((deadlineTimestamp - Date.now()) / 1000));

  let status: StatusType;
  let statusText: string;

  if (remainingSeconds <= 0) {
    status = 'waiting';
    statusText = '종료';
  } else if (remainingSeconds < 300) {
    status = 'cancel-period';
    statusText = '취소 마감까지';
  } else if (remainingSeconds < 600) {
    status = 'before-open';
    statusText = '오픈까지';
  } else {
    status = 'open';
    statusText = '신청 마감까지';
  }

  return { status, statusText, deadlineTimestamp };
}

function App() {
  const [currentDay, setCurrentDay] = useState<DayType>('수');
  const [expandedPanels, setExpandedPanels] = useState<Set<BoardType>>(new Set());
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
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

  useEffect(() => {
    // JWT 토큰 만료 시 자동 로그아웃
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
   * - 초기값: undefined → 서버 응답 전까지 AccordionPanel에 capacity가 표시되지 않음
   * - fetchCapacities() 완료 후 실제 값으로 업데이트됨
   */
  const [capacities, setCapacities] = useState<Capacity>({ 수: undefined, 금: undefined });

  // Pull-to-refresh 상태
  const [isPulling, setIsPulling] = useState(false);
  const [pullDistance, setPullDistance] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const touchStartY = useRef(0);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Mock 마감 타임스탬프: 최초 1회 생성 후 고정 (useRef)
  const mockDeadlinesRef = useRef<Record<DayType, Record<BoardType, number>> | null>(null);
  if (mockDeadlinesRef.current === null) {
    const now = Date.now();
    mockDeadlinesRef.current = {
      '수': {
        '운동':   now + 3600 * 1000,
        '게스트': now + 2400 * 1000,
        '레슨':   now + 1800 * 1000,
        '잔여석': now + 5400 * 1000,
      },
      '금': {
        '운동':   now + 180 * 1000,
        '게스트': now + 600 * 1000,
        '레슨':   now - 1000,
        '잔여석': now + 7200 * 1000,
      },
    };
  }
  const mockDeadlines = mockDeadlinesRef.current;

  // 카테고리별 상태 정보 - 초기값을 deadlineTimestamp 기준으로 동기 계산
  const [categoryStates, setCategoryStates] = useState<Record<DayType, Record<BoardType, CategoryState>>>(() => {
    const result = {} as Record<DayType, Record<BoardType, CategoryState>>;
    (['수', '금'] as DayType[]).forEach(day => {
      result[day] = {} as Record<BoardType, CategoryState>;
      (['운동', '게스트', '레슨', '잔여석'] as BoardType[]).forEach(category => {
        result[day][category] = computeStateFromDeadline(mockDeadlines[day][category]);
      });
    });
    return result;
  });

  const [semester, setSemester] = useState('1');
  const [week, setWeek] = useState('3');

  // ─── 1. 정원 fetch ──────────────────────────────────────────────────────────
  // 폴링: 5분에 한번 + soft refresh
  //
  // useCallback deps: [semester, week]
  //   → semester/week가 변경되면 새 함수 참조 생성
  //   → 아래 useEffect([fetchCapacities])가 자동으로 재실행되어
  //      이전 인터벌 해제 + 즉시 재호출 + 새 인터벌 등록
  const fetchCapacities = useCallback(async () => {
    try {
      // TODO: const data = await fetch(`/api/capacities?semester=${semester}&week=${week}`).then(r => r.json());
      // setCapacities(data);
      setCapacities(MOCK_CAPACITIES);
      console.log('[정원] 갱신:', new Date().toLocaleTimeString());
    } catch (error) {
      console.error('[정원] 실패:', error);
    }
  }, [semester, week]);

  // ─── 2. 카운트다운 fetch ────────────────────────────────────────────────────
  // 폴링: 5분에 한번 + soft refresh + 카운트다운=0
  //
  // [실서버 연동 시]
  //   fetch(`/api/category-states?semester=${semester}&week=${week}`)
  //   서버는 deadlineTimestamp(절대 시각)를 포함한 CategoryState를 반환해야 함
  const fetchCategoryStates = useCallback(async () => {
    try {
      // TODO: const data = await fetch(`/api/category-states?semester=${semester}&week=${week}`).then(r => r.json());
      // setCategoryStates(data);
      const mockData = {} as Record<DayType, Record<BoardType, CategoryState>>;
      (['수', '금'] as DayType[]).forEach(day => {
        mockData[day] = {} as Record<BoardType, CategoryState>;
        (['운동', '게스트', '레슨', '잔여석'] as BoardType[]).forEach(category => {
          mockData[day][category] = computeStateFromDeadline(mockDeadlines[day][category]);
        });
      });
      setCategoryStates(mockData);
      console.log('[카운트다운] 갱신:', new Date().toLocaleTimeString());
    } catch (error) {
      console.error('[카운트다운] 실패:', error);
    }
  }, [semester, week, mockDeadlines]);

  // ─── 3. 게시판 현황 fetch ───────────────────────────────────────────────────
  // 폴링: 2초에 한번 + soft refresh
  //
  // [실서버 연동 시]
  //   fetch(`/api/board-data?semester=${semester}&week=${week}`)
  const fetchBoardData = useCallback(async () => {
    try {
      // TODO: const data = await fetch(`/api/board-data?semester=${semester}&week=${week}`).then(r => r.json());
      // setBoardData(data);
      console.log('[게시판 현황] 갱신:', new Date().toLocaleTimeString());
    } catch (error) {
      console.error('[게시판 현황] 실패:', error);
    }
  }, [semester, week]);

  // ─── 폴링 인터벌 설정 ───────────────────────────────────────────────────────
  // 정원: 5분마다
  useEffect(() => {
    fetchCapacities();
    const id = setInterval(fetchCapacities, 5 * 60 * 1000);
    return () => clearInterval(id);
  }, [fetchCapacities]);

  // 카운트다운: 5분마다
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

  // ─── 카운트다운 0 → 카테고리 상태 즉시 갱신 ────────────────────────────────
  const handleCountdownZero = (dayType: DayType, category: BoardType) => {
    console.log(`[카운트다운] ${dayType}요일 ${category} 0 도달 → 즉시 갱신`);
    fetchCategoryStates();
  };

  // ─── Soft refresh: 세 가지 모두 즉시 갱신 ──────────────────────────────────
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

  const handleSemesterWeekChange = (newSemester: string, newWeek: string) => {
    setSemester(newSemester);
    setWeek(newWeek);
    // semester/week 변경 → useCallback deps 변경 → 각 useEffect 자동 재실행
    // (이전 인터벌 해제 + 즉시 재호출 + 새 인터벌 등록)
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
        semester={semester}
        week={week}
        onSemesterWeekChange={handleSemesterWeekChange}
      />

      <Header
        semester={semester}
        week={week}
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
