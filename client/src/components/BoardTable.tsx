import type { BoardType } from '@/types';

interface BoardTableProps {
  type: BoardType;
}

// Mock data for each board type - 50명 이상의 데이터
const mockData = {
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

export function BoardTable({ type }: BoardTableProps) {
  const data = mockData[type] || [];

  const renderHeaders = () => {
    switch (type) {
      case '운동':
        return (
          <>
            <th className="py-2 px-1 text-center text-xs font-medium text-gray-800 bg-gray-300 w-10 sticky top-0 z-10">No</th>
            <th className="py-2 px-2 text-center text-xs font-medium text-gray-800 bg-gray-300 w-20 sticky top-0 z-10">이름</th>
            <th className="py-2 px-1 text-center text-xs font-medium text-gray-800 bg-gray-300 sticky top-0 z-10">신청시간</th>
          </>
        );
      case '게스트':
        return (
          <>
            <th className="py-2 px-1 text-center text-xs font-medium text-gray-800 bg-gray-300 w-10 sticky top-0 z-10">No</th>
            <th className="py-2 px-2 text-center text-xs font-medium text-gray-800 bg-gray-300 w-20 sticky top-0 z-10">신청자</th>
            <th className="py-2 px-2 text-center text-xs font-medium text-gray-800 bg-gray-300 w-20 sticky top-0 z-10">게스트</th>
            <th className="py-2 px-1 text-center text-xs font-medium text-gray-800 bg-gray-300 sticky top-0 z-10">신청시간</th>
          </>
        );
      case '레슨':
        return (
          <>
            <th className="py-2 px-1 text-center text-xs font-medium text-gray-800 bg-gray-300 w-10 sticky top-0 z-10">No</th>
            <th className="py-2 px-2 text-center text-xs font-medium text-gray-800 bg-gray-300 w-20 sticky top-0 z-10">이름</th>
            <th className="py-2 px-1 text-center text-xs font-medium text-gray-800 bg-gray-300 w-14 sticky top-0 z-10">레슨</th>
            <th className="py-2 px-1 text-center text-xs font-medium text-gray-800 bg-gray-300 sticky top-0 z-10">신청시간</th>
          </>
        );
      case '잔여석':
        return (
          <>
            <th className="py-2 px-1 text-center text-xs font-medium text-gray-800 bg-gray-300 w-10 sticky top-0 z-10">No</th>
            <th className="py-2 px-2 text-center text-xs font-medium text-gray-800 bg-gray-300 w-20 sticky top-0 z-10">신청자</th>
            <th className="py-2 px-1 text-center text-xs font-medium text-gray-800 bg-gray-300 w-12 sticky top-0 z-10">인원</th>
            <th className="py-2 px-1 text-center text-xs font-medium text-gray-800 bg-gray-300 sticky top-0 z-10">신청시간</th>
          </>
        );
    }
  };

  const renderRows = () => {
    switch (type) {
      case '운동':
        return data.map((item: any, index: number) => (
          <tr key={item.no} className={`border-b border-gray-200 hover:bg-gray-200 transition-colors ${index % 2 === 0 ? 'bg-white' : 'bg-gray-100'}`}>
            <td className="py-2 px-1 text-center text-xs text-gray-900">{item.no}</td>
            <td className="py-2 px-2 text-center text-xs text-gray-900">{item.name}</td>
            <td className="py-2 px-1 text-center text-xs text-gray-600 tabular-nums">{item.time}</td>
          </tr>
        ));
      case '게스트':
        return data.map((item: any, index: number) => (
          <tr key={item.no} className={`border-b border-gray-200 hover:bg-gray-200 transition-colors ${index % 2 === 0 ? 'bg-white' : 'bg-gray-100'}`}>
            <td className="py-2 px-1 text-center text-xs text-gray-900">{item.no}</td>
            <td className="py-2 px-2 text-center text-xs text-gray-900">{item.applicant}</td>
            <td className="py-2 px-2 text-center text-xs text-gray-900">{item.guest}</td>
            <td className="py-2 px-1 text-center text-xs text-gray-600 tabular-nums">{item.time}</td>
          </tr>
        ));
      case '레슨':
        return data.map((item: any, index: number) => (
          <tr key={item.no} className={`border-b border-gray-200 hover:bg-gray-200 transition-colors ${index % 2 === 0 ? 'bg-white' : 'bg-gray-100'}`}>
            <td className="py-2 px-1 text-center text-xs text-gray-900">{item.no}</td>
            <td className="py-2 px-2 text-center text-xs text-gray-900">{item.name}</td>
            <td className="py-2 px-1 text-center text-xs text-gray-900">{item.lessonTime}</td>
            <td className="py-2 px-1 text-center text-xs text-gray-600 tabular-nums">{item.time}</td>
          </tr>
        ));
      case '잔여석':
        return data.map((item: any, index: number) => (
          <tr key={item.no} className={`border-b border-gray-200 hover:bg-gray-200 transition-colors ${index % 2 === 0 ? 'bg-white' : 'bg-gray-100'}`}>
            <td className="py-2 px-1 text-center text-xs text-gray-900">{item.no}</td>
            <td className="py-2 px-2 text-center text-xs text-gray-900">{item.applicant}</td>
            <td className="py-2 px-1 text-center text-xs text-gray-900">{item.participants}</td>
            <td className="py-2 px-1 text-center text-xs text-gray-600 tabular-nums">{item.time}</td>
          </tr>
        ));
    }
  };

  return (
    <div className="board-table-scroll overflow-x-auto max-h-96 overflow-y-auto">
      <table className="w-full border-y border-gray-300">
        <thead>
          <tr>{renderHeaders()}</tr>
        </thead>
        <tbody>
          {data.length > 0 ? (
            renderRows()
          ) : (
            <tr>
              <td
                colSpan={type === '운동' ? 3 : 4}
                className="py-8 text-center text-sm text-gray-500"
              >
                신청 내역이 없습니다
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
