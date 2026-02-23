import { useState } from 'react';
import { X, KeyRound, User, Eye, EyeOff, ShieldAlert, CheckCircle2 } from 'lucide-react';
import type { User as MorN } from '@/types';

interface ForcePasswordResetModalProps {
    isOpen: boolean;
    onClose: () => void;
    user: MorN | null;
}

export function ForcePasswordResetModal({ isOpen, onClose, user }: ForcePasswordResetModalProps) {
    const [targetId, setTargetId] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [showNew, setShowNew] = useState(false);
    const [showConfirm, setShowConfirm] = useState(false);
    const [isSuccess, setIsSuccess] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    const passwordMismatch = confirmPassword.length > 0 && newPassword !== confirmPassword;
    const isValid = targetId.trim().length > 0 && newPassword.length >= 4 && newPassword === confirmPassword;

    const isManager = user?.role === 'manager';
    const handleSubmit = async (e: React.FormEvent) => {
        if (!isManager) {
            window.confirm(`해당 메뉴는 임원진 전용입니다.`);
            return;
        }
        e.preventDefault();
        setError('');
        if (!isValid) return;

        setIsLoading(true);
        // 실서버 연동 시 아래 setTimeout을 실제 API 호출로 교체
        await new Promise(res => setTimeout(res, 1000));
        setIsLoading(false);
        setIsSuccess(true);
    };

    const handleClose = () => {
        setTargetId('');
        setNewPassword('');
        setConfirmPassword('');
        setShowNew(false);
        setShowConfirm(false);
        setIsSuccess(false);
        setIsLoading(false);
        setError('');
        onClose();
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[80] flex items-center justify-center p-4">
            {/* Backdrop */}
            <div className="absolute inset-0 bg-black/60" onClick={handleClose} />

            {/* Modal */}
            <div className="relative w-full max-w-sm bg-white rounded-2xl shadow-2xl overflow-hidden">
                {/* Header */}
                <div className="bg-[#1C5D99] px-5 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center flex-shrink-0">
                            <KeyRound className="w-4 h-4 text-white" />
                        </div>
                        <div>
                            <h2 className="text-sm font-bold text-white">임시 비밀번호 강제 설정</h2>
                            <p className="text-[10px] text-white/70 mt-0.5">임원진 전용 기능</p>
                        </div>
                    </div>
                    <button
                        onClick={handleClose}
                        className="p-1.5 hover:bg-white/20 rounded-lg transition-colors"
                    >
                        <X className="w-4 h-4 text-white" />
                    </button>
                </div>

                {/* Warning banner */}
                <div className="flex items-start gap-2 px-4 py-2.5 bg-amber-50 border-b border-amber-100">
                    <ShieldAlert className="w-3.5 h-3.5 text-amber-500 flex-shrink-0 mt-0.5" />
                    <p className="text-[10px] text-amber-700 leading-relaxed">
                        비밀번호를 잊어버린 회원에게만 사용하세요. 설정 후 반드시 회원에게 알려주시기 바랍니다.
                    </p>
                </div>

                {isSuccess ? (
                    /* 성공 화면 */
                    <div className="flex flex-col items-center justify-center py-10 px-6 gap-3">
                        <div className="w-14 h-14 rounded-full bg-green-100 flex items-center justify-center">
                            <CheckCircle2 className="w-8 h-8 text-green-500" />
                        </div>
                        <p className="text-sm font-bold text-gray-800 text-center">
                            비밀번호가 변경되었습니다
                        </p>
                        <p className="text-[11px] text-gray-500 text-center leading-relaxed">
                            <span className="font-semibold text-[#1C5D99]">{targetId}</span> 회원의
                            비밀번호가 임시 비밀번호로 설정되었습니다.
                            <br />회원에게 새 비밀번호를 안내해 주세요.
                        </p>
                        <button
                            onClick={handleClose}
                            className="mt-2 px-6 py-2 bg-[#1C5D99] text-white rounded-lg text-sm font-semibold hover:bg-[#1a5490] transition-colors"
                        >
                            확인
                        </button>
                    </div>
                ) : (
                    /* 입력 폼 */
                    <form onSubmit={handleSubmit} className="px-5 py-5 space-y-4">
                        {/* 대상 회원 ID */}
                        <div className="space-y-1.5">
                            <label className="flex items-center gap-1.5 text-xs font-semibold text-gray-700">
                                <User className="w-3.5 h-3.5 text-[#1C5D99]" />
                                대상 회원 ID
                            </label>
                            <input
                                type="text"
                                value={targetId}
                                onChange={e => setTargetId(e.target.value)}
                                placeholder="회원 아이디 입력"
                                className="w-full px-3 py-2.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1C5D99]/30 focus:border-[#1C5D99] transition-colors placeholder:text-gray-300"
                                autoComplete="off"
                                autoCapitalize="none"
                            />
                        </div>

                        {/* 새 비밀번호 */}
                        <div className="space-y-1.5">
                            <label className="flex items-center gap-1.5 text-xs font-semibold text-gray-700">
                                <KeyRound className="w-3.5 h-3.5 text-[#1C5D99]" />
                                새 비밀번호
                            </label>
                            <div className="relative">
                                <input
                                    type={showNew ? 'text' : 'password'}
                                    value={newPassword}
                                    onChange={e => setNewPassword(e.target.value)}
                                    placeholder="새 비밀번호 입력 (4자 이상)"
                                    className="w-full px-3 py-2.5 pr-10 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1C5D99]/30 focus:border-[#1C5D99] transition-colors placeholder:text-gray-300"
                                    autoComplete="new-password"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowNew(v => !v)}
                                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                                >
                                    {showNew ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                </button>
                            </div>
                        </div>

                        {/* 비밀번호 확인 */}
                        <div className="space-y-1.5">
                            <label className="flex items-center gap-1.5 text-xs font-semibold text-gray-700">
                                <KeyRound className="w-3.5 h-3.5 text-[#1C5D99]" />
                                비밀번호 확인
                            </label>
                            <div className="relative">
                                <input
                                    type={showConfirm ? 'text' : 'password'}
                                    value={confirmPassword}
                                    onChange={e => setConfirmPassword(e.target.value)}
                                    placeholder="비밀번호 재입력"
                                    className={`w-full px-3 py-2.5 pr-10 text-sm border rounded-lg focus:outline-none focus:ring-2 transition-colors placeholder:text-gray-300 ${passwordMismatch
                                        ? 'border-red-300 focus:ring-red-200 focus:border-red-400'
                                        : 'border-gray-200 focus:ring-[#1C5D99]/30 focus:border-[#1C5D99]'
                                        }`}
                                    autoComplete="new-password"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowConfirm(v => !v)}
                                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                                >
                                    {showConfirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                </button>
                            </div>
                            {passwordMismatch && (
                                <p className="text-[10px] text-red-500 pl-0.5">비밀번호가 일치하지 않습니다.</p>
                            )}
                        </div>

                        {error && (
                            <p className="text-[11px] text-red-500 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
                                {error}
                            </p>
                        )}

                        {/* Buttons */}
                        <div className="flex gap-2 pt-1">
                            <button
                                type="button"
                                onClick={handleClose}
                                className="flex-1 py-2.5 rounded-lg border border-gray-200 text-sm font-semibold text-gray-600 hover:bg-gray-50 transition-colors"
                            >
                                취소
                            </button>
                            <button
                                type="submit"
                                disabled={!isValid || isLoading}
                                className="flex-1 py-2.5 rounded-lg bg-[#1C5D99] text-white text-sm font-semibold hover:bg-[#1a5490] transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-1.5"
                            >
                                {isLoading ? (
                                    <>
                                        <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                                        </svg>
                                        처리 중...
                                    </>
                                ) : (
                                    '비밀번호 설정'
                                )}
                            </button>
                        </div>
                    </form>
                )}
            </div>
        </div>
    );
}
