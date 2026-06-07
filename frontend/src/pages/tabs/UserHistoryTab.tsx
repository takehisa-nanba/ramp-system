import React from 'react';
import { History, FileText, CheckCircle, Search, MessageSquare, Edit3 } from 'lucide-react';

export const UserHistoryTab: React.FC = () => {
  const events = [
    {
      id: 1,
      date: '2026/06/05',
      type: 'daily_log',
      title: '支援記録を登録',
      user: '山田 太郎',
      icon: <Edit3 className="w-4 h-4" />,
      color: 'bg-blue-100 text-blue-600'
    },
    {
      id: 2,
      date: '2026/04/05',
      type: 'plan_activate',
      title: '個別支援計画を有効化',
      user: '鈴木 管理者',
      icon: <CheckCircle className="w-4 h-4" />,
      color: 'bg-emerald-100 text-emerald-600'
    },
    {
      id: 3,
      date: '2026/04/01',
      type: 'plan_create',
      title: '個別支援計画を作成',
      user: '鈴木 管理者',
      icon: <FileText className="w-4 h-4" />,
      color: 'bg-indigo-100 text-indigo-600'
    },
    {
      id: 4,
      date: '2026/03/20',
      type: 'case_conference',
      title: 'ケース会議を記録',
      user: '鈴木 管理者',
      icon: <MessageSquare className="w-4 h-4" />,
      color: 'bg-purple-100 text-purple-600'
    },
    {
      id: 5,
      date: '2026/03/15',
      type: 'monitoring',
      title: 'モニタリングを実施',
      user: '鈴木 管理者',
      icon: <Search className="w-4 h-4" />,
      color: 'bg-amber-100 text-amber-600'
    }
  ];

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="mb-6">
        <h2 className="text-xl font-black text-slate-800 flex items-center gap-2">
          <History className="w-6 h-6 text-slate-400" />
          支援イベント履歴
        </h2>
        <p className="text-sm text-slate-500 mt-1 font-medium">これまでの支援業務の大きな状態遷移を時系列で確認できます。</p>
      </div>

      <div className="bg-white border border-slate-200 p-6 rounded-2xl shadow-sm relative">
        <div className="absolute left-[39px] top-6 bottom-6 w-0.5 bg-slate-100"></div>
        <div className="space-y-6 relative">
          {events.map((ev) => (
            <div key={ev.id} className="flex items-start gap-4">
              <div className={`w-10 h-10 rounded-full border-4 border-white ${ev.color} flex items-center justify-center shrink-0 z-10 shadow-sm`}>
                {ev.icon}
              </div>
              <div className="pt-2">
                <div className="flex items-center gap-3 mb-1">
                  <h3 className="text-md font-bold text-slate-800">{ev.title}</h3>
                  <span className="text-xs font-bold text-slate-400">{ev.date}</span>
                </div>
                <p className="text-sm font-medium text-slate-500">操作者: {ev.user}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
