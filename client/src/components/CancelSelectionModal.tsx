import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X, UserMinus, ChevronRight } from 'lucide-react';

interface CancelSelectionModalProps {
    isOpen: boolean;
    onClose: () => void;
    category: string;
    dayType: '수' | '금';
    /** 현재 신청된 참가자 이름 목록 */
    participants: string[];
    onConfirm: (selectedName: string) => void;
}

export function CancelSelectionModal({
    isOpen,
    onClose,
    category,
    dayType,
    participants,
    onConfirm,
}: CancelSelectionModalProps) {
    const [selected, setSelected] = useState<string | null>(null);

    // 열릴 때마다 선택 초기화
    useEffect(() => {
        if (isOpen) setSelected(null);
    }, [isOpen]);

    if (!isOpen) return null;

    const handleConfirm = () => {
        if (!selected) return;
        onConfirm(selected);
        onClose();
    };

    const handleBackdrop = (e: React.MouseEvent) => {
        if (e.target === e.currentTarget) onClose();
    };

    return createPortal(
        <div
            className="fixed inset-0 bg-black/60 z-[9999] flex items-center justify-center p-6"
            onClick={handleBackdrop}
        >
            <div className="bg-white w-full max-w-sm rounded-2xl shadow-2xl overflow-hidden">

                {/* Header */}
                <div className="flex items-center justify-between px-5 py-4 bg-red-500">
                    <div className="flex items-center gap-2">
                        <UserMinus className="w-5 h-5 text-white" />
                        <h3 className="text-base font-bold text-white">
                            {dayType}요일 {category} 취소
                        </h3>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-1.5 hover:bg-white/20 rounded-lg transition-colors"
                    >
                        <X className="w-5 h-5 text-white" />
                    </button>
                </div>

                {/* Prompt */}
                <div className="px-5 pt-5 pb-3">
                    <p className="text-sm text-gray-500 leading-relaxed">
                        취소할 신청을 선택하세요.
                    </p>
                </div>

                {/* Participant list */}
                <div className="px-5 pb-3 space-y-2 max-h-64 overflow-y-auto">
                    {participants.length === 0 ? (
                        <div className="py-8 text-center text-sm text-gray-400">
                            신청된 참가자가 없습니다.
                        </div>
                    ) : (
                        participants.map((name) => {
                            const isSelected = selected === name;
                            return (
                                <button
                                    key={name}
                                    type="button"
                                    onClick={() => setSelected(name)}
                                    className={`w-full flex items-center justify-between px-4 py-3 rounded-xl border-2 transition-all text-left ${isSelected
                                            ? 'border-red-400 bg-red-50'
                                            : 'border-gray-100 bg-gray-50 hover:border-gray-300 hover:bg-gray-100'
                                        }`}
                                >
                                    <div className="flex items-center gap-3">
                                        {/* 선택 표시 원 */}
                                        <div
                                            className={`w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 transition-all ${isSelected
                                                    ? 'border-red-500 bg-red-500'
                                                    : 'border-gray-300 bg-white'
                                                }`}
                                        >
                                            {isSelected && (
                                                <div className="w-2 h-2 rounded-full bg-white" />
                                            )}
                                        </div>
                                        <span
                                            className={`text-sm font-semibold ${isSelected ? 'text-red-600' : 'text-gray-700'
                                                }`}
                                        >
                                            {name}
                                        </span>
                                    </div>
                                    {isSelected && (
                                        <ChevronRight className="w-4 h-4 text-red-400 flex-shrink-0" />
                                    )}
                                </button>
                            );
                        })
                    )}
                </div>

                {/* Bottom buttons */}
                <div className="flex gap-2 px-5 py-4 border-t border-gray-100">
                    <button
                        type="button"
                        onClick={onClose}
                        className="flex-1 px-4 py-2.5 bg-gray-100 text-gray-600 rounded-xl hover:bg-gray-200 active:bg-gray-300 transition-colors text-sm font-semibold"
                    >
                        닫기
                    </button>
                    <button
                        type="button"
                        onClick={handleConfirm}
                        disabled={!selected}
                        className={`flex-1 px-4 py-2.5 rounded-xl text-sm font-bold transition-all ${selected
                                ? 'bg-red-500 hover:bg-red-600 active:bg-red-700 text-white shadow-sm'
                                : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                            }`}
                    >
                        {selected ? `"${selected}" 취소` : '취소하기'}
                    </button>
                </div>

            </div>
        </div>,
        document.body
    );
}