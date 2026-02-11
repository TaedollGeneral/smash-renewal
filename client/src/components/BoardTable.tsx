import type { BoardType } from '@/types';

interface BoardTableProps {
  type: BoardType;
  data: any[]; // eslint-disable-line @typescript-eslint/no-explicit-any
}

export function BoardTable({ type, data }: BoardTableProps) {

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

  /* eslint-disable @typescript-eslint/no-explicit-any */
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
  /* eslint-enable @typescript-eslint/no-explicit-any */

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
