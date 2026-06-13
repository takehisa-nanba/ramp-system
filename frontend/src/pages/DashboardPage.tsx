import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Users, FileText, AlertCircle, Search, CheckSquare, MessageSquare } from 'lucide-react';
import apiClient from '../services/apiClient';
import { Heading, Text } from '../components/common/Typography';

interface DashboardSummary {
  today_users: number;
  pending_daily_logs: number;
  pending_approvals: number;
  monitoring_due_count: number;
  action_items: number;
  today_case_conferences: number;
}

const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient.get<DashboardSummary>('/dashboard/summary')
      .then(res => setSummary(res.data))
      .catch(() => setSummary(null))
      .finally(() => setLoading(false));
  }, []);

  const cards = summary ? [
    {
      id: 'today-users',
      title: '今日の利用者',
      value: summary.today_users,
      detail: '本日の来所実績（チェックイン）数',
      icon: <Users className="w-8 h-8 text-indigo-600" />,
      colorClass: 'bg-indigo-50 border-indigo-100',
      path: '/today-users',
    },
    {
      id: 'incomplete-daily-logs',
      title: '未完了の支援記録',
      value: summary.pending_daily_logs,
      detail: summary.pending_daily_logs > 0 ? '至急対応推奨' : '対応不要',
      icon: <FileText className="w-8 h-8 text-amber-600" />,
      colorClass: summary.pending_daily_logs > 0 ? 'bg-amber-50 border-amber-100' : 'bg-slate-50 border-slate-100',
      path: '/action-items?type=daily_log',
    },
    {
      id: 'action-items',
      title: '管理確認事項',
      value: summary.action_items,
      detail: '未完了の支援記録・期限超過等の合計',
      icon: <AlertCircle className="w-8 h-8 text-rose-600" />,
      colorClass: summary.action_items > 0 ? 'bg-rose-50 border-rose-100' : 'bg-slate-50 border-slate-100',
      path: '/action-items',
    },
    {
      id: 'uncompleted-monitoring',
      title: '期限が近い支援計画',
      value: summary.monitoring_due_count,
      detail: summary.monitoring_due_count > 0 ? '見直し・期限超過の確認' : '対応不要',
      icon: <Search className="w-8 h-8 text-amber-600" />,
      colorClass: summary.monitoring_due_count > 0 ? 'bg-amber-50 border-amber-100' : 'bg-slate-50 border-slate-100',
      path: '/action-items?type=monitoring',
    },
    {
      id: 'pending-approvals',
      title: '未完了承認',
      value: summary.pending_approvals,
      detail: summary.pending_approvals > 0 ? 'サビ管確認待ち' : '対応不要',
      icon: <CheckSquare className="w-8 h-8 text-amber-600" />,
      colorClass: summary.pending_approvals > 0 ? 'bg-amber-50 border-amber-100' : 'bg-slate-50 border-slate-100',
      path: '/action-items?type=approval',
    },
    {
      id: 'today-case-conferences',
      title: '本日のケース会議',
      value: summary.today_case_conferences,
      detail: summary.today_case_conferences > 0 ? '今日の予定を確認' : '本日の予定なし',
      icon: <MessageSquare className="w-8 h-8 text-indigo-600" />,
      colorClass: 'bg-indigo-50 border-indigo-100',
      path: '/action-items?type=case_conference',
    },
  ] : [];

  return (
    <div className="px-4 pb-8 md:px-8 md:pb-12 animate-in fade-in duration-500">
      <div className="sticky top-0 z-10 bg-white/90 backdrop-blur-md pt-6 pb-4 md:pt-8 md:pb-4 mb-6 border-b border-slate-200">
        <Heading variant="h1">ホーム</Heading>
        <Text variant="small" className="mt-2">今日の状況と、確認が必要な項目です。</Text>
      </div>

      {loading ? (
        <div className="flex justify-center p-16">
          <div className="w-10 h-10 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
        </div>
      ) : summary === null ? (
        <div className="bg-rose-50 text-rose-600 p-6 rounded-2xl font-bold text-center">
          ダッシュボード情報の取得に失敗しました。
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {cards.map((item) => (
            <div
              key={item.id}
              onClick={() => navigate(item.path)}
              className={`p-6 rounded-[2rem] border shadow-sm hover:shadow-md transition-shadow cursor-pointer flex flex-col justify-between h-40 ${item.colorClass}`}
            >
              <div className="flex items-start justify-between">
                <div className="bg-white p-3 rounded-2xl shadow-sm">
                  {item.icon}
                </div>
                <span className="text-4xl font-black text-slate-800 tracking-tighter">
                  {item.value}
                </span>
              </div>
              <div>
                <Heading variant="h3">{item.title}</Heading>
                <Text variant="small" className="mt-1 font-bold">{item.detail}</Text>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default DashboardPage;
