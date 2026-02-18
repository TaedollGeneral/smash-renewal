import { useState, useEffect } from 'react';
import { X } from 'lucide-react';

interface SemesterSettingModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentSemester: string;
  currentWeek: string;
  onSave: (semester: string, week: string) => void;
}

export function SemesterSettingModal({
  isOpen,
  onClose,
  currentSemester,
  currentWeek,
  onSave,
}: SemesterSettingModalProps) {
  const [semester, setSemester] = useState('');
  const [week, setWeek] = useState('');

  useEffect(() => {
    if (isOpen) {
      setSemester(currentSemester);
      setWeek(currentWeek);
    }
  }, [isOpen, currentSemester, currentWeek]);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!semester || !week) {
      alert('학기와 주차를 모두 입력해주세요.');
      return;
    }

    const semesterNum = parseInt(semester);
    const weekNum = parseInt(week);

    if (semesterNum < 1 || semesterNum > 2) {
      alert('학기는 1 또는 2만 입력 가능합니다.');
      return;
    }

    if (weekNum < 1 || weekNum > 20) {
      alert('주차는 1~20 사이의 값만 입력 가능합니다.');
      return;
    }

    onSave(semester, week);
    alert('학기/주차가 설정되었습니다.');
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/60 z-[60] flex items-center justify-center p-4">
      <div className="bg-white rounded-lg p-6 w-full max-w-md shadow-2xl">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-gray-900">학기/주차 설정</h3>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded transition-colors"
          >
            <X className="w-5 h-5 text-gray-700" />
          </button>
        </div>

        <p className="text-sm text-gray-600 mb-4">현재 학기와 주차를 설정하세요.</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">학기</label>
            <select
              value={semester}
              onChange={(e) => setSemester(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-500"
              required
            >
              <option value="">학기 선택</option>
              <option value="1">1학기</option>
              <option value="2">2학기</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">주차</label>
            <input
              type="number"
              min="1"
              max="20"
              value={week}
              onChange={(e) => setWeek(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-500"
              placeholder="1 ~ 20"
              required
            />
            <p className="text-xs text-gray-500 mt-1">1부터 20까지 입력 가능합니다.</p>
          </div>

          {semester && week && (
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
              <p className="text-sm text-gray-600">미리보기</p>
              <p className="text-lg font-bold text-gray-900 mt-1">
                {semester}학기 {week}주차
              </p>
            </div>
          )}

          <div className="flex gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors font-medium"
            >
              취소
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-800 transition-colors font-medium"
            >
              저장
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
