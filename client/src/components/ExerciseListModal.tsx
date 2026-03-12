import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X, Copy, Check, ClipboardList } from 'lucide-react';

interface ExerciseListModalProps {
    isOpen: boolean;
    onClose: () => void;
    dayType: '수' | '금';
    formattedText: string;
}

export function ExerciseListModal({
    isOpen,
    onClose,
    dayType,
    formattedText,
}: ExerciseListModalProps) {
    const [copied, setCopied] = useState(false);

    // 열릴 때마다 복사 상태 초기화
    useEffect(() => {
        if (isOpen) setCopied(false);
    }, [isOpen]);

    // ESC 키로 닫기
    useEffect(() => {
        if (!isOpen) return;
        const handler = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose();
        };
        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, [isOpen, onClose]);

    if (!isOpen) return null;

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(formattedText);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch {
            // clipboard API 미지원 환경 fallback
            const el = document.createElement('textarea');
            el.value = formattedText;
            el.style.position = 'fixed';
            el.style.opacity = '0';
            document.body.appendChild(el);
            el.select();
            document.execCommand('copy');
            document.body.removeChild(el);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
    };

    const handleBackdrop = (e: React.MouseEvent) => {
        if (e.target === e.currentTarget) onClose();
    };

    const dayLabel = dayType === '수' ? '수요일' : '금요일';
    const accentColor = dayType === '수' ? '#1C5D99' : '#2D7DD2';

    return createPortal(
        <div
            className="fixed inset-0 bg-black/60 z-[9999] flex items-center justify-center p-5"
            onClick={handleBackdrop}
        >
            <div
                className="bg-white w-full max-w-sm rounded-2xl shadow-2xl overflow-hidden flex flex-col"
                style={{ maxHeight: '82vh' }}
            >
                {/* ── Header ─────────────────────────────────────────────── */}
                <div
                    className="flex items-center justify-between px-5 py-4 flex-shrink-0"
                    style={{ background: accentColor }}
                >
                    <div className="flex items-center gap-2.5">
                        <ClipboardList className="w-5 h-5 text-white" />
                        <div>
                            <h3 className="text-base font-bold text-white leading-none">
                                {dayLabel} 운동 명단
                            </h3>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-1.5 hover:bg-white/20 rounded-lg transition-colors"
                    >
                        <X className="w-5 h-5 text-white" />
                    </button>
                </div>

                {/* ── Formatted text ─────────────────────────────────────── */}
                <div className="flex-1 overflow-y-auto px-4 py-4 min-h-0">
                    <div className="relative bg-gray-50 rounded-xl">
                        <pre className="text-sm text-gray-700 whitespace-pre-wrap break-words leading-relaxed font-sans p-4 select-all">
                            {formattedText}
                        </pre>
                    </div>
                </div>
            </div>
        </div>,
        document.body,
    );
}
