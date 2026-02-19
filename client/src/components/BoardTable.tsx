import type { BoardType } from '@/types';

interface BoardTableProps {
  type: BoardType;
}

// Mock data for each board type - 50명 이상의 데이터
const names = ['홍길동', '김철수', '이영희', '박민수', '최지은', '정수진', '강민호', '윤서연', '임동현', '한지민',
               '조은비', '배성훈', '송하늘', '신유진', '오준영', '양서현', '구민재', '권나연', '남태영', '문지훈'];

const mockData = {
  운동: Array.from({ length: 55 }, (_, i) => ({
    no: i + 1,
    name: names[i % names.length],
    time: `${Math.floor(i / 10)} ${String(14 + Math.floor(i / 6) % 10).padStart(2, '0')}:${String((23 + i * 3) % 60).padStart(2, '0')}:${String((15 + i * 7) % 60).padStart(2, '0')}.${String((i * 13) % 100).padStart(2, '0')}`,
  })),
  게스트: Array.from({ length: 30 }, (_, i) => ({
    no: i + 1,
    applicant: names[i % names.length],
    guest: names[(i + 5) % names.length],
    time: `${Math.floor(i / 10)} ${String(14 + Math.floor(i / 6) % 10).padStart(2, '0')}:${String((23 + i * 3) % 60).padStart(2, '0')}:${String((15 + i * 7) % 60).padStart(2, '0')}.${String((i * 13) % 100).padStart(2, '0')}`,
  })),
  레슨: Array.from({ length: 20 }, (_, i) => ({
    no: i + 1,
    name: names[i % names.length],
    lessonTime: `${18 + Math.floor(i / 10)}:00`,
    time: `${Math.floor(i / 10)} ${String(14 + Math.floor(i / 6) % 10).padStart(2, '0')}:${String((23 + i * 3) % 60).padStart(2, '0')}:${String((15 + i * 7) % 60).padStart(2, '0')}.${String((i * 13) % 100).padStart(2, '0')}`,
  })),
  잔여석: Array.from({ length: 25 }, (_, i) => ({
    no: i + 1,
    applicant: names[i % names.length],
    participants: names[(i + 10) % names.length],
    time: `${Math.floor(i / 10)} ${String(14 + Math.floor(i / 6) % 10).padStart(2, '0')}:${String((23 + i * 3) % 60).padStart(2, '0')}:${String((15 + i * 7) % 60).padStart(2, '0')}.${String((i * 13) % 100).padStart(2, '0')}`,
  })),
};

export function BoardTable({ type }: BoardTableProps) {
  const data = mockData[type] || [];

  const renderHeaders = () => {
    switch (type) {
      case '운동':
        return (
          <>
            <th className="py-2 pl-2 pr-1 text-center text-xs font-semibold text-white bg-[#546E7A] w-10 sticky top-0 left-0 z-20">No</th>
            <th className="py-2 px-2 text-center text-xs font-semibold text-white bg-[#546E7A] w-1/2 sticky top-0 z-10">이름</th>
            <th className="py-2 px-1 text-center text-xs font-semibold text-white bg-[#546E7A] w-1/2 sticky top-0 z-10">신청시간</th>
          </>
        );
      case '게스트':
        return (
          <>
            <th className="py-2 pl-2 pr-1 text-center text-xs font-semibold text-white bg-[#546E7A] w-10 sticky top-0 left-0 z-20">No</th>
            <th className="py-2 px-2 text-center text-xs font-semibold text-white bg-[#546E7A] w-1/3 sticky top-0 z-10">신청자</th>
            <th className="py-2 px-2 text-center text-xs font-semibold text-white bg-[#546E7A] w-1/3 sticky top-0 z-10">게스트</th>
            <th className="py-2 px-1 text-center text-xs font-semibold text-white bg-[#546E7A] w-1/3 sticky top-0 z-10">신청시간</th>
          </>
        );
      case '레슨':
        return (
          <>
            <th className="py-2 pl-2 pr-1 text-center text-xs font-semibold text-white bg-[#546E7A] w-10 sticky top-0 left-0 z-20">No</th>
            <th className="py-2 px-2 text-center text-xs font-semibold text-white bg-[#546E7A] w-1/3 sticky top-0 z-10">이름</th>
            <th className="py-2 px-1 text-center text-xs font-semibold text-white bg-[#546E7A] w-1/3 sticky top-0 z-10">레슨</th>
            <th className="py-2 px-1 text-center text-xs font-semibold text-white bg-[#546E7A] w-1/3 sticky top-0 z-10">신청시간</th>
          </>
        );
      case '잔여석':
        return (
          <>
            <th className="py-2 pl-2 pr-1 text-center text-xs font-semibold text-white bg-[#546E7A] w-10 sticky top-0 left-0 z-20">No</th>
            <th className="py-2 px-2 text-center text-xs font-semibold text-white bg-[#546E7A] w-1/3 sticky top-0 z-10">신청자</th>
            <th className="py-2 px-2 text-center text-xs font-semibold text-white bg-[#546E7A] w-1/3 sticky top-0 z-10">참여인원</th>
            <th className="py-2 px-1 text-center text-xs font-semibold text-white bg-[#546E7A] w-1/3 sticky top-0 z-10">신청시간</th>
          </>
        );
    }
  };

  const renderRows = () => {
    switch (type) {
      case '운동':
        return data.map((item: any) => (
          <tr key={item.no} className="bg-[#F5F5F5] border-b border-white hover:bg-[#E8E8E8] transition-colors">
            <td className="py-2 pl-2 pr-1 text-center text-xs font-semibold text-[#1D3557] sticky left-0 z-10 bg-inherit">{item.no}</td>
            <td className="py-2 px-2 text-center text-xs font-semibold text-[#1D3557]">{item.name}</td>
            <td className="py-2 px-1 text-center text-xs font-semibold text-[#1D3557] tabular-nums">{item.time}</td>
          </tr>
        ));
      case '게스트':
        return data.map((item: any) => (
          <tr key={item.no} className="bg-[#F5F5F5] border-b border-white hover:bg-[#E8E8E8] transition-colors">
            <td className="py-2 pl-2 pr-1 text-center text-xs font-semibold text-[#1D3557] sticky left-0 z-10 bg-inherit">{item.no}</td>
            <td className="py-2 px-2 text-center text-xs font-semibold text-[#1D3557]">{item.applicant}</td>
            <td className="py-2 px-2 text-center text-xs font-semibold text-[#1D3557]">{item.guest}</td>
            <td className="py-2 px-1 text-center text-xs font-semibold text-[#1D3557] tabular-nums">{item.time}</td>
          </tr>
        ));
      case '레슨':
        return data.map((item: any) => (
          <tr key={item.no} className="bg-[#F5F5F5] border-b border-white hover:bg-[#E8E8E8] transition-colors">
            <td className="py-2 pl-2 pr-1 text-center text-xs font-semibold text-[#1D3557] sticky left-0 z-10 bg-inherit">{item.no}</td>
            <td className="py-2 px-2 text-center text-xs font-semibold text-[#1D3557]">{item.name}</td>
            <td className="py-2 px-1 text-center text-xs font-semibold text-[#1D3557]">{item.lessonTime}</td>
            <td className="py-2 px-1 text-center text-xs font-semibold text-[#1D3557] tabular-nums">{item.time}</td>
          </tr>
        ));
      case '잔여석':
        return data.map((item: any) => (
          <tr key={item.no} className="bg-[#F5F5F5] border-b border-white hover:bg-[#E8E8E8] transition-colors">
            <td className="py-2 pl-2 pr-1 text-center text-xs font-semibold text-[#1D3557] sticky left-0 z-10 bg-inherit">{item.no}</td>
            <td className="py-2 px-2 text-center text-xs font-semibold text-[#1D3557]">{item.applicant}</td>
            <td className="py-2 px-1 text-center text-xs font-semibold text-[#1D3557]">{item.participants}</td>
            <td className="py-2 px-1 text-center text-xs font-semibold text-[#1D3557] tabular-nums">{item.time}</td>
          </tr>
        ));
    }
  };

  return (
    <div className="board-table-scroll overflow-x-auto max-h-96 overflow-y-auto">
      <table className="w-full border-y border-[#3a3a3a]">
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
