import React, { useState } from 'react';
import { 
  FilePlus2, User, FileText, CheckCircle2, 
  Loader2, AlertCircle, ChevronRight,
  FileBadge2, Sparkles
} from 'lucide-react';
import { createPlanDraft } from '../services/plans.ts';

const PlanCreator: React.FC = () => {
    const [userId, setUserId] = useState(1);
    const [policyId] = useState(1);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<{status: string, id: number} | null>(null);
    const [error, setError] = useState<string | null>(null);

    const handleCreateDraft = async () => {
        setLoading(true);
        setError(null);
        setResult(null);

        try {
            const data = await createPlanDraft({
                user_id: userId,
                holistic_support_policy_id: policyId,
            });
            setResult({ status: data.status, id: data.plan_id });
        } catch (err: any) {
            const msg = err.response?.data?.msg || err.message || '計画作成に失敗しました。';
            setError(msg);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-[calc(100vh-120px)] bg-white rounded-[2.5rem] shadow-xl border border-slate-200 overflow-hidden animate-in fade-in duration-500">
            
            {/* 1. Sticky Header */}
            <header className="px-8 py-6 border-b border-slate-100 bg-white z-10 flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-black text-slate-800 tracking-tight flex items-center gap-3">
                        <FilePlus2 className="text-emerald-600" size={28} />
                        個別支援計画 新規作成
                    </h1>
                    <p className="text-sm text-slate-500 font-medium">支援の根拠となる基本計画（ドラフト）を構築します</p>
                </div>
                <div className="px-4 py-1.5 bg-emerald-50 text-emerald-600 rounded-full text-[10px] font-black uppercase tracking-widest border border-emerald-100">
                    Authority: Create_Plan
                </div>
            </header>

            {/* 2. Scrollable Content (Creation Wizard Form) */}
            <div className="flex-1 overflow-y-auto p-8 bg-slate-50/30">
                <div className="max-w-3xl mx-auto space-y-8">
                    
                    {/* Guidance Card */}
                    <section className="bg-gradient-to-br from-slate-800 to-slate-900 p-8 rounded-[2rem] text-white shadow-xl relative overflow-hidden">
                        <div className="absolute top-0 right-0 w-40 h-40 bg-emerald-500 opacity-10 rounded-full -mr-20 -mt-20" />
                        <div className="relative z-10 space-y-4">
                            <div className="flex items-center gap-2 text-emerald-400 font-black text-xs uppercase tracking-[0.2em]">
                                <Sparkles size={14} /> System Guidance
                            </div>
                            <h2 className="text-xl font-bold leading-relaxed">
                                適切な支援を行うため、まずは「総合支援方針」に基づいた計画の枠組みを作成します。
                            </h2>
                            <p className="text-sm text-white/60 font-medium leading-relaxed">
                                下記の情報を入力し、ドラフトを作成してください。作成後、具体的な長期目標・短期目標の設定が可能になります。
                            </p>
                        </div>
                    </section>

                    {/* Form Fields */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                        <div className="bg-white p-8 rounded-[2rem] border border-slate-100 shadow-lg space-y-4">
                            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-2">
                                <User size={14} className="text-indigo-500" /> Target User ID
                            </label>
                            <input 
                                type="number" value={userId} onChange={e => setUserId(Number(e.target.value))}
                                className="w-full p-4 bg-slate-50 border border-slate-100 rounded-2xl focus:bg-white focus:border-indigo-500 outline-none text-2xl font-black text-slate-700 font-mono transition-all"
                            />
                            <p className="text-xs text-slate-400 font-medium">対象となる利用者のシステムIDを入力</p>
                        </div>

                        <div className="bg-white p-8 rounded-[2rem] border border-slate-100 shadow-lg space-y-4 opacity-75">
                            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-2">
                                <FileText size={14} className="text-emerald-500" /> Holistic Policy ID
                            </label>
                            <input 
                                type="number" value={policyId} disabled
                                className="w-full p-4 bg-slate-50 border border-slate-100 rounded-2xl text-2xl font-black text-slate-300 font-mono"
                            />
                            <p className="text-xs text-slate-400 font-medium">基準となる総合支援方針は固定されています</p>
                        </div>
                    </div>

                    {error && (
                        <div className="bg-rose-50 border border-rose-100 p-6 rounded-[2rem] flex items-start gap-4 animate-in shake duration-500">
                            <AlertCircle className="text-rose-500 shrink-0" size={24} />
                            <p className="text-sm text-rose-700 font-bold">{error}</p>
                        </div>
                    )}

                    {result && (
                        <div className="bg-emerald-50 border border-emerald-100 p-8 rounded-[2rem] space-y-4 animate-in zoom-in duration-500">
                            <div className="flex items-center gap-3 text-emerald-700 font-black">
                                <CheckCircle2 size={24} /> 計画原案の作成に成功しました
                            </div>
                            <div className="grid grid-cols-2 gap-4 text-xs font-bold text-emerald-600/70">
                                <div className="bg-white p-4 rounded-xl shadow-sm border border-emerald-100">Plan ID: {result.id}</div>
                                <div className="bg-white p-4 rounded-xl shadow-sm border border-emerald-100">Status: {result.status}</div>
                            </div>
                            <button className="w-full py-4 bg-emerald-600 text-white rounded-2xl font-black hover:bg-emerald-700 transition-all flex items-center justify-center gap-2 shadow-lg shadow-emerald-900/20">
                                目標の設定へ進む <ChevronRight size={18} />
                            </button>
                        </div>
                    )}

                </div>
            </div>

            {/* 3. Sticky Footer Actions */}
            <footer className="px-8 py-6 bg-white border-t border-slate-100 flex items-center justify-between">
                <div className="flex items-center gap-4 text-slate-400 font-bold text-xs uppercase tracking-widest">
                    <FileBadge2 size={18} />
                    Ready for drafting
                </div>
                {!result && (
                    <button 
                        onClick={handleCreateDraft} disabled={loading}
                        className="px-10 py-4 bg-slate-900 text-white rounded-2xl font-black hover:bg-slate-800 transition-all shadow-2xl flex items-center gap-3 disabled:opacity-50"
                    >
                        {loading ? <Loader2 className="animate-spin" size={20} /> : <FilePlus2 size={20} />}
                        計画原案を作成する
                    </button>
                )}
            </footer>
        </div>
    );
}

export default PlanCreator;