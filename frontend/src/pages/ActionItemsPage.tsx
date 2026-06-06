import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { AlertTriangle, Clock, AlertCircle } from 'lucide-react';
import { fetchActionItems, type ActionItem } from '../services/userService';

const ActionItemsPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const currentType = searchParams.get('type') || 'all';

  const [items, setItems] = useState<ActionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadActionItems = async () => {
      try {
        setLoading(true);
        const res = await fetchActionItems();
        setItems(res.items);
      } catch (err) {
        console.error(err);
        setError('管理確認事項の取得に失敗しました。');
      } finally {
        setLoading(false);
      }
    };
    loadActionItems();
  }, []);

  const filteredItems = useMemo(() => {
    if (currentType === 'all') return items;
    return items.filter(item => item.type === currentType);
  }, [currentType, items]);

  const tabs = [
    { id: 'all', label: 'すべて' },
    { id: 'daily_log', label: '日報' },
    { id: 'monitoring', label: 'モニタリング' },
    { id: 'approval', label: '承認待ち' },
    { id: 'case_conference', label: 'ケース会議' },
  ];

  // severity に応じたスタイルのマッピング
  const getSeverityStyle = (severity: 'high' | 'medium' | 'low') => {
    switch (severity) {
      case 'high':
        return {
          badgeColor: 'bg-rose-100 text-rose-700 border border-rose-200',
          icon: <AlertCircle className="text-rose-600 w-5 h-5" />,
        };
      case 'medium':
        return {
          badgeColor: 'bg-amber-100 text-amber-700 border border-amber-200',
          icon: <AlertTriangle className="text-amber-600 w-5 h-5" />,
        };
      case 'low':
      default:
        return {
          badgeColor: 'bg-indigo-100 text-indigo-700 border border-indigo-200',
          icon: <Clock className="text-indigo-600 w-5 h-5" />,
        };
    }
  };

  const getActionItemTargetPath = (item: ActionItem) => {
    switch (item.type) {
      case 'daily_log':
        return `/users/${item.user_id}/daily-logs`;
      case 'monitoring':
        return `/users/${item.user_id}/monitoring-reports`;
      case 'approval':
        return `/users/${item.user_id}/support-plans`;
      case 'case_conference':
        return `/users/${item.user_id}/case-conferences`;
      default:
        return `/users/${item.user_id}/action-items`;
    }
  };

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

      {loading ? (
        <div className="flex justify-center p-12">
          <div className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"></div>
        </div>
      ) : error ? (
        <div className="bg-rose-50 text-rose-600 p-4 rounded-xl font-bold">{error}</div>
      ) : filteredItems.length === 0 ? (
        <div className="p-12 text-center text-slate-500 font-bold bg-slate-50 rounded-2xl border border-slate-200">
          該当する確認事項はありません
        </div>
      ) : (
        <div className="space-y-4">
          {filteredItems.map((item, index) => {
            const style = getSeverityStyle(item.severity);
            return (
              <div 
                key={`${item.user_id}-${item.type}-${index}`}
                onClick={() => navigate(getActionItemTargetPath(item))}
                className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm hover:shadow-md transition-all cursor-pointer flex items-start gap-4 group"
              >
                <div className={`p-3 rounded-xl ${style.badgeColor}`}>
                  {style.icon}
                </div>
                <div className="flex-1">
                  <div className="flex flex-wrap items-center gap-3 mb-1">
                    <h2 className="text-lg font-bold text-slate-800 group-hover:text-indigo-600 transition-colors">{item.title}</h2>
                    <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${style.badgeColor}`}>
                      {item.user_name}
                    </span>
                    <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                      {item.category_label}
                    </span>
                  </div>
                  <p className="text-slate-600 text-sm font-medium">{item.description}</p>
                </div>
                <div className="text-indigo-600 font-bold text-sm bg-indigo-50 px-4 py-2 rounded-lg group-hover:bg-indigo-100 transition-colors shrink-0">
                  対応する
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default ActionItemsPage;
