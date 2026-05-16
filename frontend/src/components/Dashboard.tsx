import React from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Clock, FileText, AlertCircle, Calendar, 
  ChevronRight, Users, Bell, CheckCircle2 
} from 'lucide-react';

const Dashboard: React.FC<{ supporterName: string | null }> = ({ supporterName }) => {
  const navigate = useNavigate();
  const currentDate = new Date().toLocaleDateString('ja-JP', { 
    month: 'long', day: 'numeric', weekday: 'short' 
  });

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Header Area */}
      <header className="flex flex-col md:flex-row md:items-end justify-between pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-3xl font-bold text-slate-800 tracking-tight">
            こんにちは、{supporterName || 'ゲスト'}さん
          </h1>
          <p className="text-slate-500 mt-1 font-medium">{currentDate} の業務状況</p>
        </div>
      </header>

      {/* Quick Actions */}
      <section>
        <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-3">
          クイックアクション
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <button 
            onClick={() => navigate('/timecard')}
            className="group relative overflow-hidden rounded-2xl bg-gradient-to-br from-blue-500 to-blue-600 p-4 text-left shadow-md transition-all hover:shadow-lg hover:-translate-y-1"
          >
            <div className="absolute -right-4 -top-4 opacity-20 transition-transform group-hover:scale-110">
              <Clock size={80} />
            </div>
            <Clock className="mb-3 text-white" size={28} />
            <span className="block text-sm font-medium text-blue-100">Timecard</span>
            <span className="block text-lg font-bold text-white">出退勤の打刻</span>
          </button>

          <button className="group relative overflow-hidden rounded-2xl bg-gradient-to-br from-emerald-500 to-emerald-600 p-4 text-left shadow-md transition-all hover:shadow-lg hover:-translate-y-1">
            <div className="absolute -right-4 -top-4 opacity-20 transition-transform group-hover:scale-110">
              <FileText size={80} />
            </div>
            <FileText className="mb-3 text-white" size={28} />
            <span className="block text-sm font-medium text-emerald-100">Daily Log</span>
            <span className="block text-lg font-bold text-white">今日の日報作成</span>
          </button>
          
          <button className="group relative overflow-hidden rounded-2xl bg-white p-4 text-left shadow-sm border border-slate-200 transition-all hover:border-indigo-300 hover:shadow-md hover:-translate-y-1">
            <Users className="mb-3 text-indigo-500" size={28} />
            <span className="block text-sm font-medium text-slate-400">Client Search</span>
            <span className="block text-lg font-bold text-slate-700">利用者検索</span>
          </button>
          
          <button className="group relative overflow-hidden rounded-2xl bg-white p-4 text-left shadow-sm border border-slate-200 transition-all hover:border-slate-400 hover:shadow-md hover:-translate-y-1">
            <Calendar className="mb-3 text-slate-500" size={28} />
            <span className="block text-sm font-medium text-slate-400">Schedule</span>
            <span className="block text-lg font-bold text-slate-700">スケジュール</span>
          </button>
        </div>
      </section>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 pt-4">
        
        {/* Left Column: Today's Tasks */}
        <section className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
              <CheckCircle2 className="text-blue-500" size={22} />
              今日の予定・タスク
            </h2>
            <button className="text-sm font-medium text-blue-600 hover:text-blue-700 flex items-center">
              すべて見る <ChevronRight size={16} />
            </button>
          </div>
          
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="divide-y divide-slate-100">
              {/* Mock Task Item 1 */}
              <div className="p-4 hover:bg-slate-50 transition-colors flex items-start gap-4 cursor-pointer">
                <div className="flex flex-col items-center justify-center w-12 h-12 rounded-xl bg-blue-50 text-blue-600 font-bold shrink-0">
                  10:00
                </div>
                <div className="flex-1">
                  <div className="flex justify-between items-start">
                    <h3 className="font-bold text-slate-800">個別面談（就労準備）</h3>
                    <span className="px-2 py-1 bg-amber-100 text-amber-700 text-xs font-bold rounded-md">
                      重要
                    </span>
                  </div>
                  <p className="text-sm text-slate-500 mt-1">対象: 佐藤 健太 様 / 場所: 面談室A</p>
                </div>
              </div>

              {/* Mock Task Item 2 */}
              <div className="p-4 hover:bg-slate-50 transition-colors flex items-start gap-4 cursor-pointer">
                <div className="flex flex-col items-center justify-center w-12 h-12 rounded-xl bg-slate-100 text-slate-600 font-bold shrink-0">
                  13:30
                </div>
                <div className="flex-1">
                  <div className="flex justify-between items-start">
                    <h3 className="font-bold text-slate-800">企業訪問同行（A社）</h3>
                  </div>
                  <p className="text-sm text-slate-500 mt-1">対象: 鈴木 花子 様 / 実習の振り返り</p>
                </div>
              </div>
              
              {/* Mock Task Item 3 */}
              <div className="p-4 hover:bg-slate-50 transition-colors flex items-start gap-4 cursor-pointer">
                <div className="flex flex-col items-center justify-center w-12 h-12 rounded-xl bg-rose-50 text-rose-600 font-bold shrink-0 text-xs">
                  未承認
                </div>
                <div className="flex-1">
                  <div className="flex justify-between items-start">
                    <h3 className="font-bold text-slate-800">昨日の日報承認</h3>
                  </div>
                  <p className="text-sm text-slate-500 mt-1">未承認の日報が3件あります。</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Right Column: Important Notices */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
              <Bell className="text-rose-500" size={22} />
              重要なお知らせ
            </h2>
          </div>

          <div className="space-y-3">
            {/* Notice 1 */}
            <div className="bg-rose-50 border border-rose-100 rounded-xl p-4 flex gap-3 items-start relative overflow-hidden group cursor-pointer">
              <div className="absolute left-0 top-0 bottom-0 w-1 bg-rose-500"></div>
              <AlertCircle className="text-rose-500 shrink-0 mt-0.5" size={20} />
              <div>
                <h4 className="font-bold text-rose-900 text-sm">支援計画の期限警告</h4>
                <p className="text-rose-700 text-xs mt-1 leading-relaxed">
                  高橋様（ID: 1042）の個別支援計画の更新期限が<strong className="font-bold">あと3日</strong>に迫っています。
                </p>
              </div>
            </div>

            {/* Notice 2 */}
            <div className="bg-amber-50 border border-amber-100 rounded-xl p-4 flex gap-3 items-start relative overflow-hidden group cursor-pointer">
              <div className="absolute left-0 top-0 bottom-0 w-1 bg-amber-500"></div>
              <Bell className="text-amber-500 shrink-0 mt-0.5" size={20} />
              <div>
                <h4 className="font-bold text-amber-900 text-sm">新規ヒヤリハット報告</h4>
                <p className="text-amber-700 text-xs mt-1 leading-relaxed">
                  本日1件のヒヤリハット報告が提出されました。確認をお願いします。
                </p>
              </div>
            </div>

            {/* Notice 3 */}
            <div className="bg-white border border-slate-200 rounded-xl p-4 flex gap-3 items-start hover:border-slate-300 transition-colors cursor-pointer">
              <Users className="text-slate-400 shrink-0 mt-0.5" size={20} />
              <div>
                <h4 className="font-bold text-slate-800 text-sm">システムメンテナンス</h4>
                <p className="text-slate-500 text-xs mt-1 leading-relaxed">
                  今週末の土曜深夜2:00〜4:00にかけて、データベースのメンテナンスが行われます。
                </p>
              </div>
            </div>
          </div>
        </section>

      </div>
    </div>
  );
};

export default Dashboard;
