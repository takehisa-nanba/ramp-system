import React from 'react';
import { 
  Users, Clock, CheckCircle, AlertCircle, 
  TrendingUp, Calendar, ChevronRight, ArrowUpRight
} from 'lucide-react';

interface DashboardProps {
  supporterName: string | null;
}

const Dashboard: React.FC<DashboardProps> = ({ supporterName }) => {
  const stats = [
    { label: '本日の利用者', value: '24', detail: '予定: 26名', icon: <Users className="text-indigo-600" />, color: 'bg-indigo-50' },
    { label: '現在の通所数', value: '18', detail: '出席率: 72%', icon: <Clock className="text-amber-600" />, color: 'bg-amber-50' },
    { label: '日報完了', value: '12', detail: '残り: 6件', icon: <CheckCircle className="text-emerald-600" />, color: 'bg-emerald-50' },
    { label: '未対応の欠席', value: '2', detail: '至急確認', icon: <AlertCircle className="text-rose-600" />, color: 'bg-rose-50' },
  ];

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      
      {/* 1. Welcome Section */}
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] mb-1">Overview</p>
          <h1 className="text-4xl font-black text-slate-800 tracking-tighter">
            こんにちは、<span className="text-indigo-600">{supporterName}</span> さん
          </h1>
          <p className="text-slate-500 font-medium mt-1 text-lg">今日の事業所の状況を確認しましょう。</p>
        </div>
        <div className="flex items-center gap-3 bg-white p-2 rounded-2xl shadow-sm border border-slate-100">
          <div className="p-2 bg-indigo-50 text-indigo-600 rounded-xl">
            <Calendar size={20} />
          </div>
          <div className="pr-4">
            <p className="text-[10px] font-black text-slate-400 uppercase">Today</p>
            <p className="text-sm font-black text-slate-700">2026年 5月 16日 (土)</p>
          </div>
        </div>
      </header>

      {/* 2. Stats Grid (Premium Cards) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, i) => (
          <div key={i} className="group bg-white p-6 rounded-[2rem] border border-slate-100 shadow-xl shadow-slate-200/50 hover:shadow-indigo-100 hover:border-indigo-100 transition-all cursor-pointer relative overflow-hidden">
            <div className={`absolute top-0 right-0 w-24 h-24 ${stat.color} opacity-20 rounded-bl-[4rem] -mr-8 -mt-8 transition-transform group-hover:scale-110`} />
            <div className="relative z-10 space-y-4">
              <div className={`${stat.color} w-12 h-12 rounded-2xl flex items-center justify-center shadow-inner`}>
                {stat.icon}
              </div>
              <div>
                <p className="text-sm font-bold text-slate-500">{stat.label}</p>
                <div className="flex items-end gap-2">
                  <span className="text-3xl font-black text-slate-800 tracking-tight">{stat.value}</span>
                  <span className="text-xs font-bold text-slate-400 mb-1.5">{stat.detail}</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* 3. Main Dashboard Layout (Two Columns) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left Column: Recent Activity / Feed */}
        <div className="lg:col-span-8 space-y-6">
          <section className="bg-white rounded-[2.5rem] border border-slate-100 shadow-xl shadow-slate-200/40 overflow-hidden">
            <div className="px-8 py-6 border-b border-slate-50 flex items-center justify-between">
              <h2 className="text-xl font-black text-slate-800 flex items-center gap-2">
                <TrendingUp className="text-indigo-600" size={24} />
                リアルタイム稼働状況
              </h2>
              <button className="text-xs font-bold text-indigo-600 hover:bg-indigo-50 px-3 py-1.5 rounded-lg transition-all">すべて見る</button>
            </div>
            <div className="p-2">
              {[1, 2, 3].map((_, i) => (
                <div key={i} className="flex items-center gap-4 p-6 hover:bg-slate-50 rounded-[2rem] transition-all group cursor-pointer">
                  <div className="w-12 h-12 rounded-2xl bg-slate-100 flex items-center justify-center font-black text-slate-400 group-hover:bg-white group-hover:shadow-md transition-all">
                    {i + 10}:00
                  </div>
                  <div className="flex-1">
                    <p className="font-bold text-slate-800">利用者 佐藤さんが通所しました</p>
                    <p className="text-xs text-slate-400 font-medium">体調良好・検温 36.5℃</p>
                  </div>
                  <ArrowUpRight className="text-slate-200 group-hover:text-indigo-500 transition-colors" size={20} />
                </div>
              ))}
            </div>
          </section>
        </div>

        {/* Right Column: Quick Tasks / Alerts */}
        <div className="lg:col-span-4 space-y-6">
          <section className="bg-slate-900 rounded-[2.5rem] p-8 text-white shadow-2xl shadow-indigo-200 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500 opacity-20 rounded-full -mr-16 -mt-16" />
            <h3 className="text-lg font-black mb-4 relative z-10">タスク・アラート</h3>
            <div className="space-y-4 relative z-10">
              <div className="bg-white/10 p-4 rounded-2xl border border-white/10 flex items-start gap-3">
                <AlertCircle className="text-rose-400 shrink-0" size={20} />
                <div>
                  <p className="text-sm font-bold">期限切れの支援計画</p>
                  <p className="text-[10px] text-white/50">利用者：鈴木 太郎 (あと2日)</p>
                </div>
              </div>
              <div className="bg-white/10 p-4 rounded-2xl border border-white/10 flex items-start gap-3">
                <MessageSquare className="text-indigo-400 shrink-0" size={20} />
                <div>
                  <p className="text-sm font-bold">未読メッセージ</p>
                  <p className="text-[10px] text-white/50">ご家族より 1件</p>
                </div>
              </div>
            </div>
            <button className="w-full mt-6 py-3 bg-indigo-600 rounded-xl font-bold text-sm hover:bg-indigo-500 transition-all flex items-center justify-center gap-2 shadow-lg shadow-indigo-900/50">
              全タスクを確認 <ChevronRight size={16} />
            </button>
          </section>

          <section className="bg-white rounded-[2.5rem] p-8 border border-slate-100 shadow-xl">
             <h3 className="text-sm font-black text-slate-400 uppercase tracking-widest mb-4">今日のスケジュール</h3>
             <div className="space-y-4">
                <div className="flex gap-4 items-start">
                  <div className="w-1 h-10 bg-indigo-500 rounded-full" />
                  <div>
                    <p className="text-xs font-black text-slate-400">14:00 - 15:00</p>
                    <p className="text-sm font-bold text-slate-700">ケース会議（田中様）</p>
                  </div>
                </div>
                <div className="flex gap-4 items-start">
                  <div className="w-1 h-10 bg-slate-200 rounded-full" />
                  <div>
                    <p className="text-xs font-black text-slate-400">16:30 - 17:30</p>
                    <p className="text-sm font-bold text-slate-700">全体ミーティング</p>
                  </div>
                </div>
             </div>
          </section>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
