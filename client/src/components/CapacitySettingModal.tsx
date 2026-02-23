import { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import type { User } from '@/types';

interface CapacitySettingModalProps {
  isOpen: boolean;
  onClose: () => void;
  user: User | null;
  currentCapacities: {
    수?: number;
    금?: number;
  };
  onSave: (capacities: { 수?: number; 금?: number }) => void;
}

export function CapacitySettingModal({
  isOpen,
  onClose,
  currentCapacities,
  onSave,
  user,
}: CapacitySettingModalProps) {
  const [currentDay, setCurrentDay] = useState<'수' | '금'>('수');
  const [wednesday, setWednesday] = useState('');
  const [friday, setFriday] = useState('');

  useEffect(() => {
    if (isOpen) {
      setWednesday(currentCapacities.수?.toString() || '');
      setFriday(currentCapacities.금?.toString() || '');
    }
  }, [isOpen, currentCapacities]);

  if (!isOpen) return null;

  const isManager = user?.role === 'manager';
  const handleSubmit = (e: React.FormEvent) => {
    if (!isManager) {
      window.confirm(`해당 메뉴는 임원진 전용입니다.`);
      return;
    }
    e.preventDefault();

    const newCapacities: { 수?: number; 금?: number } = { ...currentCapacities };

    if (currentDay === '수') {
      if (wednesday) {
        newCapacities.수 = parseInt(wednesday);
        alert('수요일 운동정원이 확정되었습니다.');
      } else {
        alert('정원을 입력해주세요.');
        return;
      }
    } else {
      if (friday) {
        newCapacities.금 = parseInt(friday);
        alert('금요일 운동정원이 확정되었습니다.');
      } else {
        alert('정원을 입력해주세요.');
        return;
      }
    }

    onSave(newCapacities);
    onClose();
  };

  const currentCapacity = currentDay === '수' ? wednesday : friday;
  const setCurrentCapacity = currentDay === '수' ? setWednesday : setFriday;

  return (
    <div className="fixed inset-0 bg-black/60 z-[60] flex items-center justify-center p-4">
      <div className="bg-white rounded-lg p-6 w-full max-w-md shadow-2xl">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-gray-900">운동정원 확정</h3>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded transition-colors"
          >
            <X className="w-5 h-5 text-gray-700" />
          </button>
        </div>

        <p className="text-sm text-gray-600 mb-4">
          수요일과 금요일을 개별적으로 확정할 수 있습니다.
        </p>

        <div className="flex gap-2 mb-4">
          <button
            type="button"
            onClick={() => setCurrentDay('수')}
            className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${currentDay === '수'
              ? 'bg-[#1C5D99] text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-[#1C5D99]/20'
              }`}
          >
            수요일
          </button>
          <button
            type="button"
            onClick={() => setCurrentDay('금')}
            className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${currentDay === '금'
              ? 'bg-[#1C5D99] text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-[#1C5D99]/20'
              }`}
          >
            금요일
          </button>
        </div>

        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {currentDay}요일 운동 정원
            </label>
            <input
              type="number"
              min="0"
              value={currentCapacity}
              onChange={(e) => setCurrentCapacity(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-500"
              placeholder="예: 48"
            />
          </div>

          <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
            <p className="text-sm text-gray-600 mb-2">현재 확정된 정원</p>
            <div className="space-y-1">
              <p className="text-sm text-gray-900">
                수요일: <span className="font-bold">{currentCapacities.수 ? `${currentCapacities.수}명` : '미설정'}</span>
              </p>
              <p className="text-sm text-gray-900">
                금요일: <span className="font-bold">{currentCapacities.금 ? `${currentCapacities.금}명` : '미설정'}</span>
              </p>
            </div>
          </div>

          <div className="flex gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 bg-[#1C5D99] text-white rounded-lg hover:bg-[#155090] transition-colors font-medium"
            >
              취소
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-2 bg-[#1C5D99] text-white rounded-lg hover:bg-[#155090] transition-colors font-medium"
            >
              {currentDay}요일 확정
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}