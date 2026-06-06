import React from 'react';
import { MessageSquare, Plus, Users, Calendar } from 'lucide-react';

export const UserCaseConferenceTab: React.FC = () => {
  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-black text-slate-800">ケース会議</h2>
        <button className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-xl font-bold hover:bg-indigo-700 transition-colors shadow-sm">
          <Plus className="w-5 h-5" /> 新規ケース会議を記録
        </button>
      </div>

      {/* 次回予定 */}
      <div className="bg-indigo-50 border border-indigo-100 p-5 rounded-2xl flex items-start gap-4">
        <div className="p-3 bg-white rounded-xl text-indigo-600 shadow-sm"><Calendar className="w-6 h-6" /></div>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-bold text-indigo-600 bg-indigo-100 px-2 py-0.5 rounded">予定</span>
            <h3 className="text-lg font-black text-slate-800">次期計画策定に向けた関係者会議</h3>
          </div>
          <p className="text-sm font-bold text-slate-600 mb-2">2026/06/10 14:00 - 15:00</p>
          <div className="flex items-center gap-1 text-xs font-medium text-slate-500">
            <Users className="w-3 h-3" /> 参加予定: 鈴木(サビ管)、山田(支援員)、佐藤(相談支援専門員)
          </div>
        </div>
      </div>

      {/* 過去の会議録 */}
      <div>
        <h3 className="text-lg font-black text-slate-800 mb-4 flex items-center gap-2"><MessageSquare className="w-5 h-5 text-slate-400" /> 過去の会議録</h3>
        <div className="space-y-4">
          <div className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm">
            <div className="flex justify-between items-start mb-3">
              <div>
                <div className="text-xs font-bold text-slate-400 mb-1">開催日: 2026/03/20</div>
                <h4 className="text-md font-bold text-slate-800">第3期計画に向けた評価会議</h4>
              </div>
              <span className="text-xs font-bold text-slate-500 bg-white border border-slate-200 px-2 py-1 rounded-lg">記録者: サビ管 鈴木</span>
            </div>
            <div className="text-xs font-bold text-slate-500 mb-3 flex items-center gap-1">
              <Users className="w-3 h-3" /> 参加者: 鈴木(サビ管)、山田(支援員)
            </div>
            <div className="space-y-2 mb-4">
              <div>
                <span className="text-xs font-bold text-slate-400">協議内容のサマリ</span>
                <p className="text-sm font-medium text-slate-700 bg-slate-50 p-2 rounded-lg mt-1">生活リズムの安定が最優先。作業訓練は無理のない範囲で進める方針で一致。</p>
              </div>
            </div>
            <button className="text-sm font-bold text-indigo-600 hover:text-indigo-800 underline decoration-indigo-200 underline-offset-4">詳細を見る</button>
          </div>
        </div>
      </div>
    </div>
  );
};
