import React, { useEffect, useState } from 'react';
import { Clock, CheckCircle, FileEdit, Plus, Link as LinkIcon, AlertCircle } from 'lucide-react';
import { fetchUserDailyLogs, type DailyLogItem } from '../../services/userService';

const statusBadge = (status: string) => {
  switch (status) {
    case 'COMPLETED':
    case 'APPROVED': return <span className="flex items-center gap-1 text-xs font-bold text-emerald-700 bg-emerald-100 px-2 py-1 rounded-full"><CheckCircle className="w-3 h-3" /> 完了</span>;
    case 'DRAFT': return <span className="flex items-center gap-1 text-xs font-bold text-amber-700 bg-amber-100 px-2 py-1 rounded-full"><Clock className="w-3 h-3" /> 確認待ち</span>;
    default: return <span className="flex items-center gap-1 text-xs font-bold text-slate-600 bg-slate-100 px-2 py-1 rounded-full"><FileEdit className="w-3 h-3" /> {status}</span>;
  }
};

export const UserDailyLogsTab: React.FC<{ userId: number }> = ({ userId }) => {
  const [items, setItems] = useState<DailyLogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchUserDailyLogs(userId)
      .then(res => setItems(res.items))
      .catch(() => setError('日報の取得に失敗しました。'))
      .finally(() => setLoading(false));
  }, [userId]);

  if (loading) return <div className="flex justify-center p-12"><div className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" /></div>;
  if (error) return <div className="bg-rose-50 text-rose-600 p-4 rounded-xl font-bold flex items-center gap-2"><AlertCircle className="w-5 h-5" />{error}</div>;

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-black text-slate-800">日報履歴</h2>
        <button className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-xl font-bold hover:bg-indigo-700 transition-colors shadow-sm">
          <Plus className="w-5 h-5" /> 新規日報作成
        </button>
      </div>

      {items.length === 0 ? (
        <div className="bg-slate-50 text-slate-500 p-8 rounded-2xl text-center font-bold border border-slate-200">
          まだ日報が記録されていません。
        </div>
      ) : (
        <div className="space-y-4 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-200 before:to-transparent">
          {items.map(log => (
            <div key={log.id} className="relative flex items-start gap-4 group">
              <div className="flex items-center justify-center w-10 h-10 rounded-full border-4 border-white bg-indigo-100 text-indigo-600 shadow shrink-0 z-10 mt-1">
                <Clock className="w-4 h-4" />
              </div>
              <div className="flex-1 bg-white p-5 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow">
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <div className="text-sm font-black text-indigo-600">{log.log_date}</div>
                    <div className="text-xs font-bold text-slate-400 mt-0.5">{log.location_type}</div>
                  </div>
                  {statusBadge(log.log_status)}
                </div>
                <p className="text-slate-700 font-medium text-sm mb-4 leading-relaxed">{log.support_content_notes}</p>
                {log.activities.length > 0 && (
                  <div className="bg-slate-50 rounded-xl p-3 mb-4">
                    <div className="flex items-start gap-2">
                      <LinkIcon className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                      <div className="w-full">
                        <div className="text-xs font-bold text-slate-400 mb-1">活動記録</div>
                        {log.activities.map(act => (
                          <div key={act.id} className="text-sm font-bold text-slate-700 flex justify-between">
                            <span>{act.support_content}</span>
                            <span className="text-slate-400 text-xs font-medium">{act.start_time}〜{act.end_time}</span>
                          </div>
                        ))}
                        <div className="text-xs font-bold text-slate-500 mt-1">
                          記録者: {log.activities[0]?.supporter_name ?? '—'}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
