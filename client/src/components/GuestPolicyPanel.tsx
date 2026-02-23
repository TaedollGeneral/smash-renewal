import { X, AlertTriangle, Info, ChevronRight, ScrollText } from 'lucide-react';

interface GuestPolicyPanelProps {
    isOpen: boolean;
    onClose: () => void;
}

const PRIORITY_COLORS = {
    1: { bg: 'bg-blue-50', border: 'border-blue-200', badge: 'bg-[#1C5D99] text-white', text: 'text-[#1C5D99]' },
    2: { bg: 'bg-emerald-50', border: 'border-emerald-200', badge: 'bg-emerald-600 text-white', text: 'text-emerald-700' },
    3: { bg: 'bg-orange-50', border: 'border-orange-200', badge: 'bg-orange-500 text-white', text: 'text-orange-700' },
};

export function GuestPolicyPanel({ isOpen, onClose }: GuestPolicyPanelProps) {
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
                <div className="flex items-center justify-between px-4 py-4 border-b border-white/20 pt-[max(16px,env(safe-area-inset-top))] flex-shrink-0">
                    <div className="flex items-center gap-2">
                        <ScrollText className="w-5 h-5 text-white" />
                        <h2 className="text-base font-bold text-white">운영 원칙 안내</h2>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-white/20 rounded-lg transition-colors">
                        <X className="w-5 h-5 text-white" />
                    </button>
                </div>

                {/* Scrollable body */}
                <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">

                    {/* 공지 헤더 배너 */}
                    <div className="bg-white rounded-xl px-4 py-3 shadow-sm">
                        <p className="text-[10px] text-gray-400 uppercase tracking-wider mb-0.5">공지</p>
                        <p className="text-sm font-bold text-[#1C5D99] leading-snug">
                            운동 정원 배정 및 운영 원칙
                        </p>
                        <p className="text-[11px] text-gray-500 mt-1.5 leading-relaxed">
                            동아리 운영의 투명성을 위해 시스템 자동 배정 로직에 근거한 원칙을 공지합니다. 1순위 게스트의 유동적 운영과 요일별 정원 산출 방식을 명확히 하는 데 목적이 있습니다.
                        </p>
                    </div>

                    {/* ─── SECTION 1 ─── */}
                    <SectionHeader number="1" title="게스트 운영 정책 및 신청 자격" />

                    {/* 비용 안내 */}
                    <div className="bg-white/15 border border-white/20 rounded-lg px-3 py-2.5 space-y-1.5">
                        <div className="flex items-center gap-1.5">
                            <Info className="w-3.5 h-3.5 text-white/80 flex-shrink-0" />
                            <span className="text-[11px] font-semibold text-white">게스트 비용</span>
                        </div>
                        <div className="flex items-center justify-between pl-5">
                            <div className="flex items-center gap-2">
                                <span className="text-[10px] px-1.5 py-0.5 bg-blue-500 text-white rounded font-bold">수요일</span>
                                <span className="text-[11px] font-bold text-white">8,000원</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="text-[10px] px-1.5 py-0.5 bg-violet-500 text-white rounded font-bold">금요일</span>
                                <span className="text-[11px] font-bold text-white">7,000원</span>
                            </div>
                        </div>
                    </div>

                    {/* 1순위 */}
                    <PriorityCard
                        rank={1}
                        label="정원 외 유동"
                        title="OB 및 교류전 목적"
                        subtitle="SMASH 활동 6개월 이상 졸업생"
                        items={[
                            { label: '신청 방법', value: '게스트 게시판에 신청글 작성' },
                            { label: '특징', value: '기본 정원 영향을 주지 않는 별도 인원으로 관리' },
                        ]}
                        warning='본문에 반드시 (ob) 또는 (교류전) 텍스트를 입력해야 시스템이 인식합니다. 해당 문구가 없으면 신청 확인이 어려울 수 있습니다.'
                        colors={PRIORITY_COLORS[1]}
                    />

                    {/* 2순위 */}
                    <PriorityCard
                        rank={2}
                        label="정원 내 고정"
                        title="재학생 · 휴학생"
                        subtitle="SMASH 활동 경력이 있는 재·휴학생"
                        items={[
                            { label: '신청 방법', value: '게스트 게시판을 통해 선착순 신청' },
                            { label: '특징', value: '요일별 지정된 게스트 고정 정원 내에서 배정' },
                        ]}
                        colors={PRIORITY_COLORS[2]}
                    />

                    {/* 3순위 */}
                    <PriorityCard
                        rank={3}
                        label="정원 내 잔여"
                        title="외부 일반인"
                        subtitle=""
                        items={[
                            { label: '신청 방법', value: '잔여석 신청 오픈 시 신청' },
                            { label: '특징', value: '정기 운동 신청 후 남은 잔여석 범위 내에서만 선착순 경쟁' },
                        ]}
                        colors={PRIORITY_COLORS[3]}
                    />

                    {/* ─── SECTION 2 ─── */}
                    <SectionHeader number="2" title="요일별 정원 산출 로직" />

                    {/* 수요일 */}
                    <DayCard
                        day="수요일"
                        dayColor="bg-blue-500"
                        focus="정기 운동 중심"
                        rows={[
                            { icon: '🔵', label: '고정 게스트 정원', value: '0석', sub: '2순위 게스트 고정석 없음' },
                            { icon: '📊', label: '잔여석 산출', value: '전체 − 정기 운동 신청자', sub: '' },
                            { icon: '➕', label: '1순위(유동)', value: '별도 추가', sub: '위 계산과 무관하게 추가됨' },
                        ]}
                    />

                    {/* 금요일 */}
                    <DayCard
                        day="금요일"
                        dayColor="bg-violet-500"
                        focus="게스트 정원 보장"
                        rows={[
                            { icon: '🟣', label: '고정 게스트 정원', value: '최대 2석', sub: '2순위 우선 확보' },
                            { icon: '📊', label: '정기 운동 가용 정원', value: '전체 − 2순위 확정자', sub: '' },
                            { icon: '🔄', label: '2순위 미달 시', value: '남는 자리 → 정기 운동 전환', sub: '부원 추가 신청 가능' },
                            { icon: '➕', label: '1순위(유동)', value: '계산 미포함', sub: '부원 가용 정원 미감소' },
                        ]}
                    />

                    {/* ─── SECTION 3 ─── */}
                    <SectionHeader number="3" title="기타" />

                    <div className="bg-white rounded-xl overflow-hidden shadow-sm">
                        {[
                            { text: '게시판의 게스트 인원 = 고정 정원 내 인원 + 1순위 유동 인원의 합계로 표시될 수 있습니다.' },
                            { text: '모든 정원 계산은 서버 시각 (KST) 기준으로 자동 처리됩니다.' },
                            { text: '시스템 오류나 정원 조정이 필요한 경우 즉시 운영진에게 문의해 주세요.' },
                        ].map((item, i, arr) => (
                            <div
                                key={i}
                                className={`flex items-start gap-2.5 px-3 py-2.5 ${i < arr.length - 1 ? 'border-b border-gray-100' : ''}`}
                            >
                                <ChevronRight className="w-3.5 h-3.5 text-[#1C5D99] flex-shrink-0 mt-0.5" />
                                <p className="text-[11px] text-gray-700 leading-relaxed">{item.text}</p>
                            </div>
                        ))}
                    </div>

                    {/* 하단 협조 요청 */}
                    <div className="bg-white/15 border border-white/20 rounded-lg px-3 py-2.5">
                        <p className="text-[11px] text-white/90 text-center leading-relaxed">
                            위 내용을 숙지하여 원활한 운동 운영에 협조해 주시기 바랍니다. 🏸
                        </p>
                    </div>

                    <div className="h-4" />
                </div>
            </div>
        </div>
    );
}

/* ── Sub-components ── */

function SectionHeader({ number, title }: { number: string; title: string }) {
    return (
        <div className="flex items-center gap-2 pt-1">
            <span className="w-5 h-5 rounded-full bg-white text-[#1C5D99] flex items-center justify-center text-[11px] font-black flex-shrink-0">
                {number}
            </span>
            <span className="text-sm font-bold text-white">{title}</span>
        </div>
    );
}

interface PriorityCardProps {
    rank: number;
    label: string;
    title: string;
    subtitle: string;
    items: { label: string; value: string }[];
    warning?: string;
    colors: { bg: string; border: string; badge: string; text: string };
}

function PriorityCard({ rank, label, title, subtitle, items, warning, colors }: PriorityCardProps) {
    return (
        <div className={`rounded-xl overflow-hidden border ${colors.border} shadow-sm`}>
            {/* Card header */}
            <div className={`${colors.bg} px-3 py-2.5 flex items-center gap-2`}>
                <span className={`text-[10px] font-black px-2 py-0.5 rounded-full ${colors.badge} flex-shrink-0`}>
                    {rank}순위
                </span>
                <span className={`text-[10px] font-semibold ${colors.text}`}>{label}</span>
                <span className="text-[11px] font-bold text-gray-800 ml-auto truncate">{title}</span>
            </div>
            {subtitle ? (
                <div className={`${colors.bg} px-3 pb-2 border-b ${colors.border}`}>
                    <p className="text-[10px] text-gray-500">{subtitle}</p>
                </div>
            ) : null}
            {/* Card body */}
            <div className="bg-white px-3 py-2 space-y-1.5">
                {items.map((item, i) => (
                    <div key={i} className="flex gap-2">
                        <span className={`text-[10px] font-semibold ${colors.text} flex-shrink-0 w-16`}>{item.label}</span>
                        <span className="text-[11px] text-gray-700 leading-snug">{item.value}</span>
                    </div>
                ))}
                {warning && (
                    <div className="flex items-start gap-1.5 mt-2 bg-amber-50 border border-amber-200 rounded-lg px-2.5 py-2">
                        <AlertTriangle className="w-3 h-3 text-amber-500 flex-shrink-0 mt-0.5" />
                        <p className="text-[10px] text-amber-800 leading-relaxed">{warning}</p>
                    </div>
                )}
            </div>
        </div>
    );
}

interface DayCardRow { icon: string; label: string; value: string; sub: string; }

function DayCard({ day, dayColor, focus, rows }: {
    day: string;
    dayColor: string;
    focus: string;
    rows: DayCardRow[];
}) {
    return (
        <div className="bg-white rounded-xl overflow-hidden shadow-sm">
            {/* Day header */}
            <div className={`${dayColor} px-3 py-2 flex items-center gap-2`}>
                <span className="text-sm font-black text-white">{day}</span>
                <span className="text-[10px] text-white/80 font-medium">{focus}</span>
            </div>
            {/* Rows */}
            <div className="divide-y divide-gray-100">
                {rows.map((row, i) => (
                    <div key={i} className="flex items-start gap-2.5 px-3 py-2">
                        <span className="text-sm leading-none mt-0.5 flex-shrink-0">{row.icon}</span>
                        <div className="flex-1 min-w-0">
                            <div className="flex items-baseline gap-1.5 flex-wrap">
                                <span className="text-[10px] text-gray-500 flex-shrink-0">{row.label}</span>
                                <span className="text-[11px] font-semibold text-gray-800">{row.value}</span>
                            </div>
                            {row.sub && (
                                <p className="text-[10px] text-gray-400 mt-0.5">{row.sub}</p>
                            )}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}