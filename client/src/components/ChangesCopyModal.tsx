import { useState } from 'react';
import { X, Copy, Check } from 'lucide-react';

interface ChangesCopyModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentDay: '수' | '금';
  setCurrentDay: (day: '수' | '금') => void;
}

export function ChangesCopyModal({
  isOpen,
  onClose,
  currentDay,
  setCurrentDay,
}: ChangesCopyModalProps) {
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  // Mock data - 실제로는 백엔드에서 가져올 데이터
  const mockChangesText = `[${currentDay}요일 변경사항]

📝 신규 신청 (5명)
- 홍길동 (운동)
- 김철수 (운동)
- 이영희 (게스트)
- 박민수 (레슨 - 초급반)
- 최지은 (잔여석)

❌ 취소 (3명)
- 정수현 (운동)
- 강민지 (게스트)
- 윤서준 (레슨 - 중급반)

🔄 변경 (2건)
- 임하은: 운동 → 레슨 (고급반)
- 조민석: 게스트 → 운동

━━━━━━━━━━━━━━━━
📊 현재 현황
운동: 45/48명
게스트: 4/12명
레슨: 7/8명
잔여석: 2/10명

최종 업데이트: ${new Date().toLocaleString('ko-KR')}`;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(mockChangesText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      alert('복사에 실패했습니다.');
    }
  };

  const handleClose = () => {
    setCopied(false);
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/60 z-[60] flex items-center justify-center p-4">
      <div className="bg-white rounded-lg p-6 w-full max-w-2xl shadow-2xl max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-gray-900">변경사항 복사</h3>
          <button
            onClick={handleClose}
            className="p-1 hover:bg-gray-100 rounded transition-colors"
          >
            <X className="w-5 h-5 text-gray-700" />
          </button>
        </div>

        <p className="text-sm text-gray-600 mb-4">
          {currentDay}요일 변경사항을 복사하여 공지에 사용하세요.
        </p>

        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setCurrentDay('수')}
            className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${
              currentDay === '수'
                ? 'bg-gray-700 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            수요일
          </button>
          <button
            onClick={() => setCurrentDay('금')}
            className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${
              currentDay === '금'
                ? 'bg-gray-700 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            금요일
          </button>
        </div>

        <div className="flex-1 overflow-y-auto bg-gray-50 border border-gray-300 rounded-lg p-4 mb-4 font-mono text-sm whitespace-pre-wrap">
          {mockChangesText}
        </div>

        <button
          onClick={handleCopy}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-800 transition-colors font-medium"
        >
          {copied ? (
            <>
              <Check className="w-5 h-5" />
              복사 완료!
            </>
          ) : (
            <>
              <Copy className="w-5 h-5" />
              복사하기
            </>
          )}
        </button>
      </div>
    </div>
  );
}
