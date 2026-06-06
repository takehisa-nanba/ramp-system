import React, { useEffect, useState } from 'react';
import { FileText, Target, Calendar, CheckCircle, Plus, History, AlertCircle } from 'lucide-react';
import {
  fetchUserSupportPlans,
  type UserSupportPlansResponse,
  type ActiveSupportPlan,
  type SupportPlanSummary,
} from '../../services/userService';

const statusLabel: Record<string, { label: string; color: string }> = {
  ACTIVE: { label: '有効 (ACTIVE)', color: 'bg-emerald-100 text-emerald-700' },
  DRAFT: { label: '下書き (DRAFT)', color: 'bg-slate-100 text-slate-600' },
  PENDING_CONSENT: { label: '同意待ち', color: 'bg-amber-100 text-amber-700' },
  PENDING_CONFERENCE: { label: '会議待ち', color: 'bg-indigo-100 text-indigo-700' },
  ARCHIVED: { label: '過去 (ARCHIVED)', color: 'bg-slate-100 text-slate-500' },
};

const ActivePlanCard: React.FC<{ plan: ActiveSupportPlan }> = ({ plan }) => (
  <div className="bg-white border-2 border-emerald-100 p-6 rounded-2xl shadow-sm relative overflow-hidden">
    <div className="absolute top-0 left-0 w-2 h-full bg-emerald-500" />
    <div className="flex justify-between items-start mb-6">
      <div>
        <span className="bg-emerald-100 text-emerald-700 px-3 py-1 rounded-full text-xs font-bold flex items-center gap-1 mb-2 w-fit">
          <CheckCircle className="w-3 h-3" /> 有効 (ACTIVE)
        </span>
        <h3 className="text-xl font-black text-slate-800">
          {plan.long_term_goals[0]?.description ?? '長期目標が未設定です'}
        </h3>
      </div>
      <div className="text-right shrink-0 ml-4">
        <div className="text-xs font-bold text-slate-400 mb-1">計画期間</div>
        <div className="text-sm font-bold text-slate-700">
          {plan.start_date ?? '—'} 〜 {plan.end_date ?? '—'}
        </div>
      </div>
    </div>

    {/* 短期目標 */}
    {plan.long_term_goals.length > 0 && (
      <div className="mb-6">
        <h4 className="text-sm font-bold text-slate-400 mb-3 flex items-center gap-2">
          <Target className="w-4 h-4" /> 短期目標・支援内容
        </h4>
        <div className="grid gap-4 md:grid-cols-2">
          {plan.long_term_goals.flatMap(ltg => ltg.short_term_goals).map(stg => (
            <div key={stg.id} className="border border-slate-200 rounded-xl p-4 hover:border-indigo-200 hover:shadow-sm transition-all">
              <div className="text-indigo-600 font-black mb-2 text-sm">{stg.description}</div>
              {stg.individual_goals.map(ig => (
                <div key={ig.id} className="space-y-2">
                  <div>
                    <div className="text-xs font-bold text-slate-400">本人の取組</div>
                    <div className="text-sm font-medium text-slate-700">{ig.user_commitment}</div>
                  </div>
                  <div>
                    <div className="text-xs font-bold text-slate-400">支援内容</div>
                    <div className="text-sm font-medium text-slate-700">{ig.support_actions}</div>
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    )}

    {/* 次回モニタリング */}
    <div className="bg-amber-50 border border-amber-100 rounded-xl p-4 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="bg-amber-200 p-2 rounded-lg text-amber-700"><Calendar className="w-5 h-5" /></div>
        <div>
          <div className="text-xs font-bold text-amber-700">次回モニタリング予定（暫定）</div>
          <div className="text-sm font-black text-amber-900">{plan.next_monitoring_due ?? '未設定'}</div>
        </div>
      </div>
    </div>
  </div>
);

const PlanHistoryTable: React.FC<{ plans: SupportPlanSummary[] }> = ({ plans }) => (
  <div>
    <h3 className="text-lg font-black text-slate-800 mb-4 flex items-center gap-2">
      <History className="w-5 h-5 text-slate-400" /> 計画履歴
    </h3>
    {plans.length === 0 ? (
      <p className="text-sm font-medium text-slate-400 p-4 text-center bg-white border border-slate-200 rounded-2xl">過去の計画はありません。</p>
    ) : (
      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
        <table className="w-full text-left">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              <th className="p-4 text-xs font-black text-slate-500 uppercase">ステータス</th>
              <th className="p-4 text-xs font-black text-slate-500 uppercase">期間</th>
              <th className="p-4 text-xs font-black text-slate-500 uppercase">作成日</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {plans.map(p => {
              const st = statusLabel[p.plan_status] ?? { label: p.plan_status, color: 'bg-slate-100 text-slate-500' };
              return (
                <tr key={p.id} className="hover:bg-slate-50 transition-colors">
                  <td className="p-4">
                    <span className={`text-xs font-bold px-2 py-1 rounded-full ${st.color}`}>{st.label}</span>
                  </td>
                  <td className="p-4 text-sm font-bold text-slate-700">{p.start_date ?? '—'} 〜 {p.end_date ?? '—'}</td>
                  <td className="p-4 text-sm font-medium text-slate-600">{p.created_at ? new Date(p.created_at).toLocaleDateString() : '—'}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    )}
  </div>
);

export const UserSupportPlanTab: React.FC<{ userId: number }> = ({ userId }) => {
  const [data, setData] = useState<UserSupportPlansResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchUserSupportPlans(userId)
      .then(setData)
      .catch(() => setError('個別支援計画の取得に失敗しました。'))
      .finally(() => setLoading(false));
  }, [userId]);

  if (loading) return <div className="flex justify-center p-12"><div className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" /></div>;
  if (error) return <div className="bg-rose-50 text-rose-600 p-4 rounded-xl font-bold flex items-center gap-2"><AlertCircle className="w-5 h-5" />{error}</div>;

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-black text-slate-800 flex items-center gap-2">
          <FileText className="w-6 h-6 text-indigo-600" /> 個別支援計画
        </h2>
        <button className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-xl font-bold hover:bg-indigo-700 transition-colors shadow-sm">
          <Plus className="w-5 h-5" /> 次期計画を作成
        </button>
      </div>

      {data?.active_plan ? (
        <ActivePlanCard plan={data.active_plan} />
      ) : (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 p-6 rounded-2xl font-bold text-center">
          現在有効な個別支援計画がありません。
        </div>
      )}

      <PlanHistoryTable plans={data?.plan_history ?? []} />
    </div>
  );
};
