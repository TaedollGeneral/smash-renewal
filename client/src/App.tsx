import { useState } from 'react';

type DayType = '수' | '금';
type BoardType = '운동' | '잔여석' | '게스트' | '레슨';

function App() {
  const [currentDay, setCurrentDay] = useState<DayType>('수');
  const [expandedPanels, setExpandedPanels] = useState<Set<BoardType>>(new Set());
  const [_isSidebarOpen, setIsSidebarOpen] = useState(false);

  // Mock data - 서버에서 받아올 데이터
  const semester = '1';
  const week = '3';

  // 수요일과 금요일에 따른 아코디언 패널 설정 (잔여석은 항상 마지막)
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
      {/* TODO: Sidebar 컴포넌트 (Phase 2에서 구현) */}

      {/* TODO: Header 컴포넌트 (Phase 2에서 구현) */}
      <header className="bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <button onClick={() => setIsSidebarOpen(true)} className="p-2">☰</button>
          <h1 className="text-lg font-medium">{semester}학기 {week}주차</h1>
          <div className="flex gap-2">
            {(['수', '금'] as DayType[]).map((day) => (
              <button
                key={day}
                onClick={() => setCurrentDay(day)}
                className={`px-3 py-1 rounded-md text-sm font-medium ${
                  currentDay === day
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-secondary text-secondary-foreground'
                }`}
              >
                {day}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Main Content - Scrollable */}
      <div className="flex-1 overflow-y-auto pb-44 md:pb-32">
        <div className="flex flex-col">
          {accordionPanels[currentDay].map((panel) => (
            // TODO: AccordionPanel 컴포넌트 (Phase 2에서 구현)
            <div
              key={panel}
              className="border-b bg-white"
            >
              <button
                onClick={() => togglePanel(panel)}
                className="w-full p-4 flex justify-between items-center"
              >
                <span className="font-medium">{panel}</span>
                <span className="text-muted-foreground text-sm">마감 23:59:59</span>
              </button>
              {expandedPanels.has(panel) && (
                <div className="p-4 pt-0 text-sm text-muted-foreground">
                  {panel} 게시판 내용 영역 (Phase 2에서 구현)
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* TODO: ApplicationPanel 컴포넌트 (Phase 2에서 구현) */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t p-4 shadow-lg">
        <p className="text-center text-muted-foreground text-sm">신청 패널 (Phase 2에서 구현)</p>
      </div>
    </div>
  );
}

export default App;
