import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertCircle, AlertTriangle, Clock } from 'lucide-react';
import { fetchActionItems, type ActionItem } from '../../services/userService';

export const UserActionItemsTab: React.FC<{ userId: number }> = ({ userId }) => {
  const navigate = useNavigate();
  const [items, setItems] = useState<ActionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadItems = async () => {
      try {
        setLoading(true);
        const res = await fetchActionItems();
        setItems(res.items);
      } catch (err) {
        console.error(err);
        setError('確認事項の取得に失敗しました。');
      } finally {
        setLoading(false);
      }
    };
    loadItems();
  }, []);

  const userFilteredItems = useMemo(() => {
    return items.filter(item => item.user_id === userId);
  }, [items, userId]);

  const getActionItemTargetPath = (item: ActionItem) => {
    switch (item.type) {
      case 'daily_log':
        return `/users/${item.user_id}/daily-logs${item.target_date ? `?date=${item.target_date}` : ''}`;
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

  if (loading) {
    return (
      <div className="flex justify-center p-12">
        <div className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"></div>
      </div>
    );
  }

  if (error) {
    return <div className="bg-rose-50 text-rose-600 p-4 rounded-xl font-bold">{error}</div>;
  }

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
        {userFilteredItems.length === 0 ? (
          <div className="bg-slate-50 text-slate-500 p-8 rounded-2xl text-center font-bold border border-slate-200">
            この利用者に関する確認事項はありません
          </div>
        ) : (
          userFilteredItems.map((item, index) => {
            const style = getSeverityStyle(item.severity);
            return (
              <div 
                key={`${item.type}-${index}`} 
                onClick={() => navigate(getActionItemTargetPath(item))}
                className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm hover:shadow-md transition-all cursor-pointer flex items-start gap-4 group"
              >
                <div className={`p-3 rounded-xl ${style.badgeColor}`}>
                  {style.icon}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-1">
                    <h3 className="text-lg font-bold text-slate-800 group-hover:text-indigo-600 transition-colors">{item.title}</h3>
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
          })
        )}
      </div>
    </div>
  );
};
