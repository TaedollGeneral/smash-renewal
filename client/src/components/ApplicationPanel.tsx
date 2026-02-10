import { useState } from 'react';
import { Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { BoardType } from '@/types';

interface ApplicationPanelProps {
  availablePanels: BoardType[];
}

export function ApplicationPanel({ availablePanels }: ApplicationPanelProps) {
  const [selectedBoard, setSelectedBoard] = useState<BoardType | ''>('');

  const handleSubmit = () => {
    if (!selectedBoard) return;
    // TODO: Phase 4에서 API 연동
    alert(`${selectedBoard} 신청이 접수되었습니다.`);
  };

  return (
    <div className="fixed bottom-0 left-0 right-0 z-20 border-t bg-white/95 backdrop-blur-sm shadow-[0_-2px_10px_rgba(0,0,0,0.05)]">
      <div className="px-4 py-3 space-y-3">
        {/* 게시판 선택 */}
        <div className="flex gap-2 overflow-x-auto board-table-scroll">
          {availablePanels.map((panel) => (
            <button
              key={panel}
              onClick={() => setSelectedBoard(panel)}
              className={`shrink-0 px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                selectedBoard === panel
                  ? 'bg-primary text-primary-foreground border-primary'
                  : 'bg-white text-muted-foreground border-border hover:border-foreground/30'
              }`}
            >
              {panel}
            </button>
          ))}
        </div>

        {/* 신청 버튼 */}
        <Button
          onClick={handleSubmit}
          disabled={!selectedBoard}
          className="w-full"
          size="lg"
        >
          <Send className="size-4" />
          {selectedBoard ? `${selectedBoard} 신청하기` : '게시판을 선택하세요'}
        </Button>
      </div>
    </div>
  );
}
