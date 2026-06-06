import React, { useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { AlertTriangle, Clock, AlertCircle, CheckSquare, MessageSquare } from 'lucide-react';

const ActionItemsPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const currentType = searchParams.get('type') || 'all';

  // TODO: Replace with GET /api/action-items
  const mockActionItems = [
    {
      id: 1,
      userId: 13,
      userName: '鈴木 太郎',
      severity: 'URGENT',
      type: 'approval',
      title: '鈴木 太郎さんの個別支援計画が未作成です',
      description: 'サービス提供開始日を過ぎていますが、計画が未作成です。早めの対応をお願いします。',
      icon: <AlertCircle className="text-rose-600 w-5 h-5" />,
      badgeColor: 'bg-rose-100 text-rose-700',
    },
    {
      id: 2,
      userId: 15,
      userName: '佐藤 花子',
      severity: 'WARNING',
      type: 'monitoring',
      title: '佐藤 花子さんのモニタリング期限が経過しています',
      description: '前回のモニタリングから6ヶ月が経過しました。次回の予定を立てましょう。',
      icon: <Clock className="text-amber-600 w-5 h-5" />,
      badgeColor: 'bg-amber-100 text-amber-700',
    },
    {
      id: 3,
      userId: 20,
      userName: '田中 一郎',
      severity: 'WARNING',
      type: 'daily_log',
      title: '田中 一郎さんの日報が未完了です',
      description: '過去3日間の日報が未入力のままになっています。記録をお願いします。',
      icon: <AlertTriangle className="text-amber-600 w-5 h-5" />,
      badgeColor: 'bg-amber-100 text-amber-700',
    },
    {
      id: 4,
      userId: 22,
      userName: '山田 次郎',
      severity: 'WARNING',
      type: 'approval',
      title: '山田 次郎さんの個別支援計画が承認待ちです',
      description: 'サビ管の確認・承認待ちの計画があります。',
      icon: <CheckSquare className="text-amber-600 w-5 h-5" />,
      badgeColor: 'bg-amber-100 text-amber-700',
    },
    {
      id: 5,
      userId: 25,
      userName: '高橋 三郎',
      severity: 'INFO',
      type: 'case_conference',
      title: '高橋 三郎さんのケース会議が予定されています',
      description: '本日 14:00〜 ケース会議が予定されています。事前の確認をお願いします。',
      icon: <MessageSquare className="text-indigo-600 w-5 h-5" />,
      badgeColor: 'bg-indigo-100 text-indigo-700',
    },
  ];

  const filteredItems = useMemo(() => {
    if (currentType === 'all') return mockActionItems;
    return mockActionItems.filter(item => item.type === currentType);
  }, [currentType, mockActionItems]);

  const tabs = [
    { id: 'all', label: 'すべて' },
    { id: 'daily_log', label: '日報' },
    { id: 'monitoring', label: 'モニタリング' },
    { id: 'approval', label: '承認待ち' },
    { id: 'case_conference', label: 'ケース会議' },
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

      {/* タブUI */}
      <div className="flex gap-2 mb-6 border-b border-slate-200 pb-2 overflow-x-auto">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setSearchParams({ type: tab.id })}
            className={`px-4 py-2 font-bold text-sm whitespace-nowrap rounded-lg transition-colors ${
              currentType === tab.id 
                ? 'bg-indigo-600 text-white' 
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="space-y-4">
        {filteredItems.length === 0 ? (
          <div className="p-12 text-center text-slate-500 font-bold bg-slate-50 rounded-2xl border border-slate-200">
            該当する確認事項はありません
          </div>
        ) : (
          filteredItems.map((item) => (
            <div 
              key={item.id}
              onClick={() => navigate(`/users/${item.userId}`)}
              className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm hover:shadow-md transition-all cursor-pointer flex items-start gap-4 group"
            >
              <div className={`p-3 rounded-xl ${item.badgeColor}`}>
                {item.icon}
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-1">
                  <h2 className="text-lg font-bold text-slate-800 group-hover:text-indigo-600 transition-colors">{item.title}</h2>
                  <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${item.badgeColor}`}>
                    {item.userName}
                  </span>
                </div>
                <p className="text-slate-600 text-sm font-medium">{item.description}</p>
              </div>
              <div className="text-indigo-600 font-bold text-sm bg-indigo-50 px-4 py-2 rounded-lg group-hover:bg-indigo-100 transition-colors shrink-0">
                対応する
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default ActionItemsPage;
