import React from 'react';
import { AlertCircle, AlertTriangle, Clock } from 'lucide-react';

export const UserActionItemsTab: React.FC = () => {
  const mockItems = [
    {
      id: 1,
      type: 'URGENT',
      title: '個別支援計画が未作成です',
      description: 'サービス提供開始日を過ぎていますが、計画が未作成です。早めの対応をお願いします。',
      icon: <AlertCircle className="text-rose-600 w-5 h-5" />,
      badgeColor: 'bg-rose-100 text-rose-700',
    },
    {
      id: 2,
      type: 'WARNING',
      title: 'モニタリング期限が経過しています',
      description: '前回のモニタリングから6ヶ月が経過しました。次回の予定を立てましょう。',
      icon: <Clock className="text-amber-600 w-5 h-5" />,
      badgeColor: 'bg-amber-100 text-amber-700',
    },
    {
      id: 3,
      type: 'WARNING',
      title: '日報が未完了です',
      description: '過去3日間の日報が未入力のままになっています。記録をお願いします。',
      icon: <AlertTriangle className="text-amber-600 w-5 h-5" />,
      badgeColor: 'bg-amber-100 text-amber-700',
    }
  ];

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="mb-6">
        <h2 className="text-xl font-black text-slate-800 flex items-center gap-2">
          <AlertCircle className="w-6 h-6 text-rose-600" />
          この利用者に関する確認事項
        </h2>
        <p className="text-sm text-slate-500 mt-1 font-medium">この利用者について対応が必要なアラート一覧です。</p>
      </div>

      <div className="space-y-4">
        {mockItems.map(item => (
          <div key={item.id} className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm flex items-start gap-4">
            <div className={`p-3 rounded-xl ${item.badgeColor}`}>
              {item.icon}
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-bold text-slate-800 mb-1">{item.title}</h3>
              <p className="text-slate-600 text-sm font-medium">{item.description}</p>
            </div>
            <div className="text-indigo-600 font-bold text-sm bg-indigo-50 px-4 py-2 rounded-lg hover:bg-indigo-100 transition-colors cursor-pointer shrink-0">
              対応する
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
