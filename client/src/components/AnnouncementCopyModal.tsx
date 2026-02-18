import { useState } from 'react';
import { X, Copy, Check } from 'lucide-react';

interface AnnouncementCopyModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentDay: '수' | '금';
  setCurrentDay: (day: '수' | '금') => void;
}

export function AnnouncementCopyModal({
  isOpen,
  onClose,
  currentDay,
  setCurrentDay,
}: AnnouncementCopyModalProps) {
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  // Mock data - 실제로는 백엔드에서 가져올 데이터
  const mockAnnouncementText = `[${currentDay}요일 운동 명단]

🏸 운동 참가자 (48명)
1. 홍길동
2. 김철수
3. 이영희
4. 박민수
5. 최지은
6. 정수현
7. 강민지
8. 윤서준
9. 임하은
10. 조민석
... (총 48명)

👥 게스트 (5명)
1. 손님A (초대: 홍길동)
2. 손님B (초대: 김철수)
3. 손님C (초대: 이영희)
4. 손님D (초대: 박민수)
5. 손님E (초대: 최지은)

🎓 레슨 (8명)
1. 초급반 - 강민지, 윤서준
2. 중급반 - 임하은, 조민석
3. 고급반 - 정수현, 최지은
...

총 인원: 61명`;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(mockAnnouncementText);
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
          <h3 className="text-lg font-bold text-gray-900">공지용 명단 복사</h3>
          <button
            onClick={handleClose}
            className="p-1 hover:bg-gray-100 rounded transition-colors"
          >
            <X className="w-5 h-5 text-gray-700" />
          </button>
        </div>

        <p className="text-sm text-gray-600 mb-4">
          {currentDay}요일 운동 명단을 복사하여 공지에 사용하세요.
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
          {mockAnnouncementText}
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
