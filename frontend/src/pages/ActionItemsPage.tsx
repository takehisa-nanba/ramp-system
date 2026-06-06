import React from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, Clock, AlertCircle } from 'lucide-react';

const ActionItemsPage: React.FC = () => {
  const navigate = useNavigate();

  // TODO: Replace with GET /api/action-items
  const mockActionItems = [
    {
      id: 1,
      userId: 13,
      userName: '鈴木 太郎',
      type: 'URGENT',
      title: '鈴木 太郎さんの個別支援計画が未作成です',
      description: 'サービス提供開始日を過ぎていますが、計画が未作成です。早めの対応をお願いします。',
      icon: <AlertCircle className="text-rose-600 w-5 h-5" />,
      badgeColor: 'bg-rose-100 text-rose-700',
    },
    {
      id: 2,
      userId: 15,
      userName: '佐藤 花子',
      type: 'WARNING',
      title: '佐藤 花子さんのモニタリング期限が経過しています',
      description: '前回のモニタリングから6ヶ月が経過しました。次回の予定を立てましょう。',
      icon: <Clock className="text-amber-600 w-5 h-5" />,
      badgeColor: 'bg-amber-100 text-amber-700',
    },
    {
      id: 3,
      userId: 20,
      userName: '田中 一郎',
      type: 'WARNING',
      title: '田中 一郎さんの日報が未完了です',
      description: '過去3日間の日報が未入力のままになっています。記録をお願いします。',
      icon: <AlertTriangle className="text-amber-600 w-5 h-5" />,
      badgeColor: 'bg-amber-100 text-amber-700',
    },
  ];

  return (
    <div className="p-6 md:p-8 animate-in fade-in duration-500 max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-black text-slate-800 tracking-tight flex items-center gap-3">
          <AlertCircle className="text-rose-600 w-8 h-8" />
          管理確認事項
        </h1>
        <p className="text-slate-500 mt-2 font-medium">対応が必要なリスク項目の一覧です。</p>
      </div>

      <div className="space-y-4">
        {mockActionItems.map((item) => (
          <div 
            key={item.id}
            onClick={() => navigate(`/users/${item.userId}`)}
            className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm hover:shadow-md transition-all cursor-pointer flex items-start gap-4"
          >
            <div className={`p-3 rounded-xl ${item.badgeColor}`}>
              {item.icon}
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-1">
                <h2 className="text-lg font-bold text-slate-800">{item.title}</h2>
                <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${item.badgeColor}`}>
                  {item.userName}
                </span>
              </div>
              <p className="text-slate-600 text-sm font-medium">{item.description}</p>
            </div>
            <div className="text-indigo-600 font-bold text-sm bg-indigo-50 px-4 py-2 rounded-lg hover:bg-indigo-100 transition-colors">
              対応する
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ActionItemsPage;
