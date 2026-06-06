import React from 'react';
import { Users, FileText, AlertCircle, Search, CheckSquare, MessageSquare } from 'lucide-react';

const DashboardPage: React.FC = () => {
  // TODO: Replace with GET /api/dashboard/summary
  const dashboardSummaryMock = [
    {
      id: 'today-users',
      title: '今日の利用者',
      value: 24,
      detail: '予定: 26名',
      icon: <Users className="w-8 h-8 text-indigo-600" />,
      colorClass: 'bg-indigo-50 border-indigo-100',
    },
    {
      id: 'incomplete-daily-logs',
      title: '未完了日報',
      value: 6,
      detail: '至急対応推奨',
      icon: <FileText className="w-8 h-8 text-amber-600" />,
      colorClass: 'bg-amber-50 border-amber-100',
    },
    {
      id: 'action-items',
      title: '管理確認事項',
      value: 2,
      detail: '計画未作成・期限超過等',
      icon: <AlertCircle className="w-8 h-8 text-rose-600" />,
      colorClass: 'bg-rose-50 border-rose-100',
    },
    {
      id: 'uncompleted-monitoring',
      title: '未実施モニタリング',
      value: 3,
      detail: '期限が近づいています',
      icon: <Search className="w-8 h-8 text-amber-600" />,
      colorClass: 'bg-amber-50 border-amber-100',
    },
    {
      id: 'pending-approvals',
      title: '未完了承認',
      value: 1,
      detail: 'サビ管確認待ち',
      icon: <CheckSquare className="w-8 h-8 text-amber-600" />,
      colorClass: 'bg-amber-50 border-amber-100',
    },
    {
      id: 'today-case-conferences',
      title: '本日のケース会議',
      value: 1,
      detail: '14:00〜 田中様',
      icon: <MessageSquare className="w-8 h-8 text-indigo-600" />,
      colorClass: 'bg-indigo-50 border-indigo-100',
    },
  ];

  return (
    <div className="p-6 md:p-8 animate-in fade-in duration-500">
      <div className="mb-8">
        <h1 className="text-3xl font-black text-slate-800 tracking-tight">ホーム</h1>
        <p className="text-slate-500 mt-2 font-medium">今日の状況と、確認が必要な項目です。</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {dashboardSummaryMock.map((item) => (
          <div 
            key={item.id} 
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
              <h2 className="text-lg font-bold text-slate-800">{item.title}</h2>
              <p className="text-sm font-bold text-slate-500 mt-1">{item.detail}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default DashboardPage;
