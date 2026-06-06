import React from 'react';
import { Clock, CheckCircle, FileEdit, Plus, Link as LinkIcon } from 'lucide-react';

export const UserDailyLogsTab: React.FC<{ userId: number }> = () => {
  const mockLogs = [
    {
      id: 1,
      date: '2026-06-06',
      time: '10:00 - 12:00',
      supporter: '山田 太郎',
      summary: 'PC作業訓練。タイピング速度の向上が見られたが、後半集中力が切れる場面があった。',
      planRelation: '短期目標1「PC操作の基礎習得」に基づく支援',
      status: 'completed', // completed, draft, pending
    },
    {
      id: 2,
      date: '2026-06-05',
      time: '13:00 - 15:00',
      supporter: '佐藤 花子',
      summary: 'コミュニケーション訓練。グループワークで自ら発言する姿勢が見られた。',
      planRelation: '短期目標2「他者との円滑なコミュニケーション」に基づく支援',
      status: 'pending',
    },
    {
      id: 3,
      date: '2026-06-04',
      time: '10:00 - 15:00',
      supporter: '山田 太郎',
      summary: '作業所内での軽作業。1日通して安定して取り組めていた。',
      planRelation: '総合支援方針に基づく日常的な見守り・支援',
      status: 'completed',
    }
  ];

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed': return <span className="flex items-center gap-1 text-xs font-bold text-emerald-700 bg-emerald-100 px-2 py-1 rounded-full"><CheckCircle className="w-3 h-3" /> 完了</span>;
      case 'pending': return <span className="flex items-center gap-1 text-xs font-bold text-amber-700 bg-amber-100 px-2 py-1 rounded-full"><Clock className="w-3 h-3" /> 確認待ち</span>;
      case 'draft': return <span className="flex items-center gap-1 text-xs font-bold text-slate-700 bg-slate-100 px-2 py-1 rounded-full"><FileEdit className="w-3 h-3" /> 下書き</span>;
      default: return null;
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-black text-slate-800">日報履歴</h2>
        <button className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-xl font-bold hover:bg-indigo-700 transition-colors shadow-sm">
          <Plus className="w-5 h-5" /> 新規日報作成
        </button>
      </div>

      <div className="space-y-4 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-200 before:to-transparent">
        {mockLogs.map((log) => (
          <div key={log.id} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
            {/* Timeline dot */}
            <div className="flex items-center justify-center w-10 h-10 rounded-full border-4 border-white bg-indigo-100 text-indigo-600 shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10">
              <Clock className="w-4 h-4" />
            </div>
            
            {/* Card */}
            <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] bg-white p-5 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex justify-between items-start mb-3">
                <div>
                  <div className="text-sm font-black text-indigo-600">{log.date}</div>
                  <div className="text-xs font-bold text-slate-400 mt-0.5">{log.time}</div>
                </div>
                {getStatusBadge(log.status)}
              </div>
              
              <p className="text-slate-700 font-medium text-sm mb-4 leading-relaxed">
                {log.summary}
              </p>
              
              <div className="bg-slate-50 rounded-xl p-3 mb-4">
                <div className="flex items-start gap-2">
                  <LinkIcon className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                  <div>
                    <div className="text-xs font-bold text-slate-400 mb-0.5">計画との関連</div>
                    <div className="text-sm font-bold text-slate-700">{log.planRelation}</div>
                  </div>
                </div>
              </div>

              <div className="flex justify-end">
                <div className="text-xs font-bold text-slate-500 bg-white border border-slate-200 px-2 py-1 rounded-lg">
                  記録者: {log.supporter}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
