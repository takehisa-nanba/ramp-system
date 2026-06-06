import React, { useEffect, useState } from 'react';
import { MessageSquare, Plus, Users, Calendar, AlertCircle } from 'lucide-react';
import { fetchUserCaseConferences, type CaseConferenceItem } from '../../services/userService';

const conferenceTypeLabel: Record<string, string> = {
  AD_HOC: '随時',
  REGULAR: '定例',
  EMERGENCY: '緊急',
};

export const UserCaseConferenceTab: React.FC<{ userId: number }> = ({ userId }) => {
  const [items, setItems] = useState<CaseConferenceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchUserCaseConferences(userId)
      .then(res => setItems(res.items))
      .catch(() => setError('ケース会議記録の取得に失敗しました。'))
      .finally(() => setLoading(false));
  }, [userId]);

  if (loading) return <div className="flex justify-center p-12"><div className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" /></div>;
  if (error) return <div className="bg-rose-50 text-rose-600 p-4 rounded-xl font-bold flex items-center gap-2"><AlertCircle className="w-5 h-5" />{error}</div>;

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-black text-slate-800">ケース会議</h2>
        <button className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-xl font-bold hover:bg-indigo-700 transition-colors shadow-sm">
          <Plus className="w-5 h-5" /> 新規ケース会議を記録
        </button>
      </div>

      {items.length === 0 ? (
        <div className="bg-slate-50 text-slate-500 p-8 rounded-2xl text-center font-bold border border-slate-200">
          ケース会議の記録がありません。
        </div>
      ) : (
        <div>
          <h3 className="text-lg font-black text-slate-800 mb-4 flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-slate-400" /> 会議録
          </h3>
          <div className="space-y-4">
            {items.map(conf => (
              <div key={conf.id} className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm">
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-bold text-indigo-600 bg-indigo-100 px-2 py-0.5 rounded">
                        {conferenceTypeLabel[conf.conference_type] ?? conf.conference_type}
                      </span>
                      <div className="text-xs font-bold text-slate-400 flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {conf.conference_datetime ? new Date(conf.conference_datetime).toLocaleString() : '—'}
                      </div>
                    </div>
                    <h4 className="text-md font-bold text-slate-800">{conf.concern_summary}</h4>
                  </div>
                  <span className="text-xs font-bold text-slate-500 bg-white border border-slate-200 px-2 py-1 rounded-lg shrink-0 ml-3">
                    記録: {conf.initiator_name}
                  </span>
                </div>

                {conf.participants.length > 0 && (
                  <div className="flex items-center gap-1 text-xs font-medium text-slate-500 mb-3">
                    <Users className="w-3 h-3" />
                    参加者: {conf.participants.join('、')}
                  </div>
                )}

                <div>
                  <div className="text-xs font-bold text-slate-400 mb-1">決定事項・対応方針</div>
                  <p className="text-sm font-medium text-slate-700 bg-slate-50 p-3 rounded-xl">{conf.agreed_action}</p>
                </div>

                {conf.plan_direction_update && (
                  <div className="mt-3">
                    <div className="text-xs font-bold text-slate-400 mb-1">計画への反映方針</div>
                    <p className="text-sm font-medium text-slate-700 bg-indigo-50 p-3 rounded-xl border border-indigo-100">{conf.plan_direction_update}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
