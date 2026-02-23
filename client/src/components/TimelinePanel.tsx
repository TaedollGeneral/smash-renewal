import { X, Clock, RefreshCw, AlertCircle } from 'lucide-react';

interface TimelinePanelProps {
    isOpen: boolean;
    onClose: () => void;
}

const ROWS = [
    {
        category: '수/금\n정기 운동',
        open: '토 22:00',
        transition: '일 10:00',
        deadline: ['수 00:00', '금 00:00'],
    },
    {
        category: '수/금\n게스트',
        open: '토 22:01',
        transition: null,
        deadline: ['수 18:00', '금 17:00'],
    },
    {
        category: '수요일\n레슨',
        open: '일 22:00',
        transition: null,
        deadline: ['수 18:00'],
    },
    {
        category: '수/금\n잔여석',
        open: '일 22:01',
        transition: null,
        deadline: ['수 18:00', '금 17:00'],
    },
];

export function TimelinePanel({ isOpen, onClose }: TimelinePanelProps) {
    return (
        <div
            className={`fixed inset-0 z-[70] transition-opacity duration-300 ${isOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
                }`}
        >
            {/* Backdrop */}
            <div className="absolute inset-0 bg-black/50" onClick={onClose} />

            {/* Panel */}
            <div
                className={`absolute top-0 left-0 h-full w-80 bg-[#1C5D99] flex flex-col transform transition-transform duration-300 ease-out shadow-2xl ${isOpen ? 'translate-x-0' : '-translate-x-full'
                    }`}
            >
                {/* Header */}
                <div className="flex items-center justify-between px-4 py-4 border-b border-white/20 pt-[max(16px,env(safe-area-inset-top))]">
                    <div className="flex items-center gap-2">
                        <Clock className="w-5 h-5 text-white" />
                        <h2 className="text-base font-bold text-white">오픈 및 마감 타임라인</h2>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-white/20 rounded-lg transition-colors"
                    >
                        <X className="w-5 h-5 text-white" />
                    </button>
                </div>

                {/* Scrollable body */}
                <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">

                    {/* Reset Notice */}
                    <div className="flex items-start gap-2 bg-white/15 border border-white/20 rounded-lg px-3 py-2.5">
                        <RefreshCw className="w-4 h-4 text-white/80 flex-shrink-0 mt-0.5" />
                        <p className="text-xs text-white/90 leading-relaxed">
                            매주 <span className="font-bold text-white">토요일 00:00</span>에
                            모든 데이터가 초기화됩니다.
                        </p>
                    </div>

                    {/* Section label */}
                    <div className="flex items-center gap-1.5">
                        <span className="text-base leading-none">💡</span>
                        <span className="text-sm font-bold text-white">요약 표</span>
                    </div>

                    {/* Table */}
                    <div className="rounded-xl overflow-hidden shadow-lg border border-white/10">
                        <table className="w-full border-collapse table-fixed text-[11px]">
                            <colgroup>
                                {/* 카테고리 */}
                                <col style={{ width: '26%' }} />
                                {/* 신청 오픈 */}
                                <col style={{ width: '22%' }} />
                                {/* 상태 전환 */}
                                <col style={{ width: '22%' }} />
                                {/* 최종 마감 */}
                                <col style={{ width: '30%' }} />
                            </colgroup>

                            {/* Head */}
                            <thead>
                                <tr className="bg-[#154a7a] text-white">
                                    <th className="px-2 py-2.5 text-left font-semibold border-r border-white/20 leading-tight">
                                        카테고리
                                    </th>
                                    <th className="px-1.5 py-2.5 text-center font-semibold border-r border-white/20 leading-tight">
                                        신청<br />오픈
                                    </th>
                                    <th className="px-1.5 py-2.5 text-center font-semibold border-r border-white/20 leading-tight">
                                        상태 전환<br />
                                        <span className="text-[9px] font-normal opacity-75">(취소만)</span>
                                    </th>
                                    <th className="px-1.5 py-2.5 text-center font-semibold leading-tight">
                                        최종<br />마감
                                    </th>
                                </tr>
                            </thead>

                            {/* Body */}
                            <tbody>
                                {ROWS.map((row, idx) => (
                                    <tr
                                        key={idx}
                                        className={`border-t border-gray-100 ${idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'
                                            }`}
                                    >
                                        {/* 카테고리 */}
                                        <td className="px-2 py-2.5 border-r border-gray-100 font-semibold text-gray-800 leading-tight whitespace-pre-line align-middle">
                                            {row.category}
                                        </td>

                                        {/* 신청 오픈 */}
                                        <td className="px-1.5 py-2.5 border-r border-gray-100 text-center align-middle">
                                            <span className="inline-block px-1.5 py-0.5 bg-blue-50 text-[#1C5D99] rounded font-semibold whitespace-nowrap">
                                                {row.open}
                                            </span>
                                        </td>

                                        {/* 상태 전환 */}
                                        <td className="px-1.5 py-2.5 border-r border-gray-100 text-center align-middle">
                                            {row.transition ? (
                                                <span className="inline-block px-1.5 py-0.5 bg-amber-50 text-amber-700 rounded font-semibold whitespace-nowrap">
                                                    {row.transition}
                                                </span>
                                            ) : (
                                                <span className="text-gray-300 font-bold">—</span>
                                            )}
                                        </td>

                                        {/* 최종 마감 */}
                                        <td className="px-1.5 py-2.5 text-center align-middle">
                                            {row.deadline.map((d, i) => (
                                                <span key={i} className="block text-gray-700 font-medium whitespace-nowrap leading-tight">
                                                    {d}
                                                </span>
                                            ))}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    {/* Legend */}
                    <div className="bg-white/10 rounded-lg px-3 py-3 space-y-2">
                        <div className="flex items-start gap-1.5">
                            <AlertCircle className="w-3.5 h-3.5 text-white/70 flex-shrink-0 mt-0.5" />
                            <p className="text-[11px] text-white/80 leading-relaxed">
                                <span className="font-semibold text-white">상태 전환</span>이란 신청 마감 후 취소만 가능한 구간으로 전환되는 시각입니다.
                            </p>
                        </div>
                        <div className="flex items-start gap-1.5">
                            <AlertCircle className="w-3.5 h-3.5 text-white/70 flex-shrink-0 mt-0.5" />
                            <p className="text-[11px] text-white/80 leading-relaxed">
                                <span className="font-semibold text-white">최종 마감</span> 이후에는 신청·취소 모두 불가합니다.
                            </p>
                        </div>
                        <div className="flex items-start gap-1.5">
                            <AlertCircle className="w-3.5 h-3.5 text-white/70 flex-shrink-0 mt-0.5" />
                            <p className="text-[11px] text-white/80 leading-relaxed">
                                마감 이후 신청·취소가 필요한 경우 <span className="font-semibold text-white">임원진에게 직접 연락</span>해 주세요.
                            </p>
                        </div>
                        <div className="flex items-start gap-1.5">
                            <AlertCircle className="w-3.5 h-3.5 text-red-300 flex-shrink-0 mt-0.5" />
                            <p className="text-[11px] text-white/80 leading-relaxed">
                                <span className="font-semibold text-red-300">당일 취소</span>는{' '}
                                <span className="font-semibold text-red-300">불참비 5,000원</span>이 부과됩니다.
                            </p>
                        </div>
                    </div>

                </div>
            </div>
        </div>
    );
}