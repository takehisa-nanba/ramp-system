import React, { useEffect, useState } from 'react';
import { Plus, Clock, FileText, CheckCircle, AlertTriangle, AlertCircle } from 'lucide-react';
import { fetchUserMonitoringReports, type UserMonitoringResponse } from '../../services/userService';

const getDaysUntil = (dateStr: string | null): number | null => {
  if (!dateStr) return null;
  const diff = new Date(dateStr).getTime() - new Date().setHours(0,0,0,0);
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
};

export const UserMonitoringTab: React.FC<{ userId: number }> = ({ userId }) => {
  const [data, setData] = useState<UserMonitoringResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchUserMonitoringReports(userId)
      .then(setData)
      .catch(() => setError('モニタリング情報の取得に失敗しました。'))
      .finally(() => setLoading(false));
  }, [userId]);

  if (loading) return <div className="flex justify-center p-12"><div className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" /></div>;
  if (error) return <div className="bg-rose-50 text-rose-600 p-4 rounded-xl font-bold flex items-center gap-2"><AlertCircle className="w-5 h-5" />{error}</div>;

  const daysUntil = getDaysUntil(data?.next_monitoring_due ?? null);
  const isOverdue = daysUntil !== null && daysUntil < 0;
  const isUrgent = daysUntil !== null && daysUntil <= 30 && daysUntil >= 0;

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-black text-slate-800">モニタリング</h2>
      </div>

      {/* 1. 次回モニタリング期限 */}
      {data?.next_monitoring_due ? (
        <div className={`border-l-4 p-6 rounded-r-2xl shadow-sm flex items-start gap-4 ${isOverdue ? 'bg-rose-50 border-rose-500' : isUrgent ? 'bg-amber-50 border-amber-500' : 'bg-slate-50 border-slate-300'}`}>
          <div className={`p-3 rounded-xl mt-1 ${isOverdue ? 'bg-rose-100 text-rose-700' : isUrgent ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-600'}`}>
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div>
            <h3 className={`text-sm font-bold mb-1 ${isOverdue ? 'text-rose-700' : isUrgent ? 'text-amber-700' : 'text-slate-600'}`}>次回モニタリング期限（暫定）</h3>
            <p className={`text-2xl font-black ${isOverdue ? 'text-rose-900' : isUrgent ? 'text-amber-900' : 'text-slate-800'}`}>
              {data.next_monitoring_due}
              <span className={`text-sm font-bold ml-3 ${isOverdue ? 'text-rose-700' : isUrgent ? 'text-amber-700' : 'text-slate-500'}`}>
                {isOverdue ? `(${Math.abs(daysUntil!)}日超過)` : daysUntil !== null ? `(残り${daysUntil}日)` : ''}
              </span>
            </p>
          </div>
        </div>
      ) : (
        <div className="bg-slate-50 p-4 rounded-2xl text-slate-500 font-bold border border-slate-200">モニタリング期限が設定されていません。</div>
      )}

      {/* 2. 現在評価対象の計画 */}
      {data?.active_plan_summary && (
        <div>
          <h3 className="text-lg font-black text-slate-800 mb-4 flex items-center gap-2">
            <FileText className="w-5 h-5 text-indigo-600" /> 現在評価対象の計画
          </h3>
          <div className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm">
            <div className="flex items-center gap-2 mb-2">
              <span className="bg-emerald-100 text-emerald-700 px-3 py-1 rounded-full text-xs font-bold flex items-center gap-1">
                <CheckCircle className="w-3 h-3" /> 有効 (ACTIVE)
              </span>
              <span className="text-sm font-bold text-slate-500">第{data.active_plan_summary.plan_version}期 計画</span>
            </div>
            <h4 className="text-lg font-black text-slate-800 mb-3">{data.active_plan_summary.primary_goal ?? '目標未設定'}</h4>
            <div className="text-sm font-medium text-slate-600 bg-slate-50 p-3 rounded-xl border border-slate-100">
              この計画に対する日々の支援記録（日報）をもとに、目標の達成度を評価します。
            </div>
          </div>
        </div>
      )}

      {/* 3. 新規モニタリング実施 */}
      <div className="pt-2">
        <button className="flex items-center justify-center gap-2 w-full md:w-auto bg-indigo-600 text-white px-6 py-3 rounded-xl font-bold hover:bg-indigo-700 transition-colors shadow-sm text-lg">
          <Plus className="w-6 h-6" /> 新規モニタリング実施
        </button>
      </div>

      {/* 4. 過去のモニタリング履歴 */}
      <div className="pt-4 border-t border-slate-200">
        <h3 className="text-lg font-black text-slate-800 mb-4 flex items-center gap-2">
          <Clock className="w-5 h-5 text-slate-400" /> 過去のモニタリング履歴
        </h3>
        {(data?.history ?? []).length === 0 ? (
          <p className="text-sm text-slate-400 font-medium p-6 bg-white border border-slate-200 rounded-2xl text-center">モニタリング記録がありません。</p>
        ) : (
          <div className="space-y-4">
            {data!.history.map(r => (
              <div key={r.id} className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm">
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <div className="text-xs font-bold text-slate-400 mb-1">実施日: {r.report_date}</div>
                    <h4 className="text-md font-bold text-slate-800">計画ID:{r.support_plan_id} の評価</h4>
                  </div>
                  <span className="text-xs font-bold text-slate-500 bg-white border border-slate-200 px-2 py-1 rounded-lg">記録者: {r.supporter_name}</span>
                </div>
                <p className="text-sm font-medium text-slate-700 mb-3">{r.monitoring_summary}</p>
                {r.target_goal_progress_notes && (
                  <p className="text-xs font-medium text-slate-500 bg-slate-50 p-2 rounded-lg">{r.target_goal_progress_notes}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
