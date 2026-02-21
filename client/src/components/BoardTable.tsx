import type { BoardType } from '@/types';
import type { BoardEntry } from '@/hooks/useScheduleSystem';
import { formatTimestamp } from '@/lib/utils';

interface BoardTableProps {
  type: BoardType;
  applications?: BoardEntry[];
}

export function BoardTable({ type, applications = [] }: BoardTableProps) {

  const renderHeaders = () => {
    switch (type) {
      case '운동':
        return (
          <>
            <th className="py-2 pl-2 pr-1 text-center text-xs font-medium text-white bg-[#63666A] w-10 sticky top-0 left-0 z-20">No</th>
            <th className="py-2 px-2 text-center text-xs font-medium text-white bg-[#63666A] w-1/2 sticky top-0 z-10">이름</th>
            <th className="py-2 px-1 text-center text-xs font-medium text-white bg-[#63666A] w-1/2 sticky top-0 z-10">신청시간</th>
          </>
        );
      case '게스트':
        return (
          <>
            <th className="py-2 pl-2 pr-1 text-center text-xs font-medium text-white bg-[#63666A] w-10 sticky top-0 left-0 z-20">No</th>
            <th className="py-2 px-2 text-center text-xs font-medium text-white bg-[#63666A] w-1/3 sticky top-0 z-10">신청자</th>
            <th className="py-2 px-2 text-center text-xs font-medium text-white bg-[#63666A] w-1/3 sticky top-0 z-10">게스트</th>
            <th className="py-2 px-1 text-center text-xs font-medium text-white bg-[#63666A] w-1/3 sticky top-0 z-10">신청시간</th>
          </>
        );
      case '레슨':
        return (
          <>
            <th className="py-2 pl-2 pr-1 text-center text-xs font-medium text-white bg-[#63666A] w-10 sticky top-0 left-0 z-20">No</th>
            <th className="py-2 px-2 text-center text-xs font-medium text-white bg-[#63666A] w-1/3 sticky top-0 z-10">이름</th>
            <th className="py-2 px-1 text-center text-xs font-medium text-white bg-[#63666A] w-1/3 sticky top-0 z-10">레슨</th>
            <th className="py-2 px-1 text-center text-xs font-medium text-white bg-[#63666A] w-1/3 sticky top-0 z-10">신청시간</th>
          </>
        );
      case '잔여석':
        return (
          <>
            <th className="py-2 pl-2 pr-1 text-center text-xs font-medium text-white bg-[#63666A] w-10 sticky top-0 left-0 z-20">No</th>
            <th className="py-2 px-2 text-center text-xs font-medium text-white bg-[#63666A] w-1/3 sticky top-0 z-10">신청자</th>
            <th className="py-2 px-2 text-center text-xs font-medium text-white bg-[#63666A] w-1/3 sticky top-0 z-10">참여인원</th>
            <th className="py-2 px-1 text-center text-xs font-medium text-white bg-[#63666A] w-1/3 sticky top-0 z-10">신청시간</th>
          </>
        );
    }
  };

  // timestamp는 Unix seconds(float) → ms 변환 후 formatTimestamp 적용
  const fmtTime = (entry: BoardEntry) => formatTimestamp(entry.timestamp * 1000);

  const renderRows = () => {
    switch (type) {
      case '운동':
        return applications.map((entry, index) => {
          // 👈 상위 10명 조건 추가
          const textColor = index < 10 ? 'text-green-400' : 'text-white';

          return (
            <tr key={entry.user_id} className={`border-b border-[#3a3a3a] hover:bg-[#3a3a3a] transition-colors ${index % 2 === 0 ? 'bg-[#272727]' : 'bg-[#2e2e2e]'}`}>
              <td className={`py-2 pl-2 pr-1 text-center text-xs sticky left-0 z-10 bg-inherit ${textColor}`}>{index + 1}</td>
              <td className={`py-2 px-2 text-center text-xs ${textColor}`}>{entry.name}</td>
              <td className="py-2 px-1 text-center text-xs text-gray-400 tabular-nums">{fmtTime(entry)}</td>
            </tr>
          );
        });
      case '게스트':
        return applications.map((entry, index) => (
          <tr key={entry.user_id} className={`border-b border-[#3a3a3a] hover:bg-[#3a3a3a] transition-colors ${index % 2 === 0 ? 'bg-[#272727]' : 'bg-[#2e2e2e]'}`}>
            <td className="py-2 pl-2 pr-1 text-center text-xs text-white sticky left-0 z-10 bg-inherit">{index + 1}</td>
            <td className="py-2 px-2 text-center text-xs text-white">{entry.name}</td>
            <td className="py-2 px-2 text-center text-xs text-white">{entry.guest_name ?? '-'}</td>
            <td className="py-2 px-1 text-center text-xs text-gray-400 tabular-nums">{fmtTime(entry)}</td>
          </tr>
        ));
      case '레슨':
        return applications.map((entry, index) => (
          <tr key={entry.user_id} className={`border-b border-[#3a3a3a] hover:bg-[#3a3a3a] transition-colors ${index % 2 === 0 ? 'bg-[#272727]' : 'bg-[#2e2e2e]'}`}>
            <td className="py-2 pl-2 pr-1 text-center text-xs text-white sticky left-0 z-10 bg-inherit">{index + 1}</td>
            <td className="py-2 px-2 text-center text-xs text-white">{entry.name}</td>
            <td className="py-2 px-1 text-center text-xs text-white">{entry.guest_name ?? '-'}</td>
            <td className="py-2 px-1 text-center text-xs text-gray-400 tabular-nums">{fmtTime(entry)}</td>
          </tr>
        ));
      case '잔여석':
        return applications.map((entry, index) => (
          <tr key={entry.user_id} className={`border-b border-[#3a3a3a] hover:bg-[#3a3a3a] transition-colors ${index % 2 === 0 ? 'bg-[#272727]' : 'bg-[#2e2e2e]'}`}>
            <td className="py-2 pl-2 pr-1 text-center text-xs text-white sticky left-0 z-10 bg-inherit">{index + 1}</td>
            <td className="py-2 px-2 text-center text-xs text-white">{entry.name}</td>
            <td className="py-2 px-1 text-center text-xs text-white">{entry.guest_name ?? '-'}</td>
            <td className="py-2 px-1 text-center text-xs text-gray-400 tabular-nums">{fmtTime(entry)}</td>
          </tr>
        ));
    }
  };

  return (
    <div className={`board-table-scroll overflow-x-auto overflow-y-auto ${type === '운동' ? 'max-h-[500px]' : 'max-h-96'}`}>      <table className="w-full border-y border-[#3a3a3a]">
      <thead>
        <tr>{renderHeaders()}</tr>
      </thead>
      <tbody>
        {applications.length > 0 ? (
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
