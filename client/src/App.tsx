import { useState, useEffect } from 'react';
import { Header } from '@/components/Header';
import { AccordionPanel } from '@/components/AccordionPanel';
import { ApplicationPanel } from '@/components/ApplicationPanel';
import { AppSidebar } from '@/components/AppSidebar';
import type { DayType, BoardType } from '@/types';

// Mock data - 서버 연동 시 제거 예정
/* eslint-disable @typescript-eslint/no-explicit-any */
const mockBoardData: Record<BoardType, any[]> = {
  운동: Array.from({ length: 55 }, (_, i) => ({
    no: i + 1,
    name: `회원${i + 1}`,
    time: `${String(14 + Math.floor(i / 60)).padStart(2, '0')}:${String((23 + i) % 60).padStart(2, '0')}:${String((15 + i * 3) % 60).padStart(2, '0')}`,
  })),
  게스트: Array.from({ length: 30 }, (_, i) => ({
    no: i + 1,
    applicant: `회원${i + 1}`,
    guest: `게스트${i + 1}`,
    time: `${String(14 + Math.floor(i / 60)).padStart(2, '0')}:${String((23 + i) % 60).padStart(2, '0')}:${String((15 + i * 3) % 60).padStart(2, '0')}`,
  })),
  레슨: Array.from({ length: 20 }, (_, i) => ({
    no: i + 1,
    name: `회원${i + 1}`,
    lessonTime: `${18 + Math.floor(i / 10)}:00`,
    time: `${String(14 + Math.floor(i / 60)).padStart(2, '0')}:${String((23 + i) % 60).padStart(2, '0')}:${String((15 + i * 3) % 60).padStart(2, '0')}`,
  })),
  잔여석: Array.from({ length: 25 }, (_, i) => ({
    no: i + 1,
    applicant: `회원${i + 1}`,
    participants: `${(i % 3) + 1}명`,
    time: `${String(14 + Math.floor(i / 60)).padStart(2, '0')}:${String((23 + i) % 60).padStart(2, '0')}:${String((15 + i * 3) % 60).padStart(2, '0')}`,
  })),
};
/* eslint-enable @typescript-eslint/no-explicit-any */

function App() {
  const [currentDay, setCurrentDay] = useState<DayType>('수');
  const [expandedPanels, setExpandedPanels] = useState<Set<BoardType>>(new Set());
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // 서버에서 받아올 학기/주차 데이터
  const [semesterInfo, setSemesterInfo] = useState({ semester: '', week: '' });

  useEffect(() => {
    // TODO: 서버 API 호출로 교체 예정
    // fetchSemesterInfo().then(data => setSemesterInfo(data));
    setSemesterInfo({ semester: '1', week: '3' });
  }, []);

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
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Sidebar */}
      <AppSidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />

      {/* Header */}
      <Header
        semester={semesterInfo.semester}
        week={semesterInfo.week}
        currentDay={currentDay}
        onDayChange={setCurrentDay}
        onMenuClick={() => setIsSidebarOpen(true)}
      />

      {/* Main Content - Scrollable */}
      <div className="flex-1 overflow-y-auto pb-44 md:pb-32">
        <div className="flex flex-col">
          {accordionPanels[currentDay].map((panel) => (
            <AccordionPanel
              key={panel}
              title={panel}
              isExpanded={expandedPanels.has(panel)}
              onToggle={() => togglePanel(panel)}
              deadline="23:59:59"
              data={mockBoardData[panel] || []}
            />
          ))}
        </div>
      </div>

      {/* Fixed Bottom Application Panel */}
      <ApplicationPanel availablePanels={accordionPanels[currentDay]} />
    </div>
  );
}

export default App;
