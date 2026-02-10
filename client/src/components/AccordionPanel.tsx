import { ChevronDown, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { BoardType } from '@/types';

interface AccordionPanelProps {
  title: BoardType;
  isExpanded: boolean;
  onToggle: () => void;
  deadline: string;
}

const BOARD_COLORS: Record<BoardType, string> = {
  '운동': 'bg-blue-500',
  '게스트': 'bg-emerald-500',
  '레슨': 'bg-violet-500',
  '잔여석': 'bg-amber-500',
};

export function AccordionPanel({
  title,
  isExpanded,
  onToggle,
  deadline,
}: AccordionPanelProps) {
  return (
    <div className="border-b bg-white">
      {/* Header */}
      <button
        onClick={onToggle}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-accent/50 transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <span className={cn('size-2.5 rounded-full', BOARD_COLORS[title])} />
          <span className="font-medium text-sm">{title}</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <Clock className="size-3" />
            {deadline}
          </span>
          <ChevronDown
            className={cn(
              'size-4 text-muted-foreground transition-transform duration-200',
              isExpanded && 'rotate-180',
            )}
          />
        </div>
      </button>

      {/* Content */}
      <div
        className={cn(
          'accordion-content overflow-hidden transition-all duration-200',
          isExpanded ? 'max-h-96' : 'max-h-0',
        )}
      >
        <div className="px-4 pb-4">
          <div className="rounded-lg border overflow-x-auto board-table-scroll">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="px-3 py-2 text-left font-medium text-muted-foreground">코트</th>
                  <th className="px-3 py-2 text-left font-medium text-muted-foreground">시간</th>
                  <th className="px-3 py-2 text-left font-medium text-muted-foreground">상태</th>
                </tr>
              </thead>
              <tbody>
                {/* 서버에서 데이터를 받아올 영역 — Phase 4에서 API 연동 */}
                <tr className="border-b last:border-b-0">
                  <td className="px-3 py-2.5 text-muted-foreground" colSpan={3}>
                    데이터를 불러오는 중...
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
