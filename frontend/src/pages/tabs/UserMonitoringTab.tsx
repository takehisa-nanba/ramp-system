import React from 'react';
import { Plus, Clock, FileText, CheckCircle, AlertTriangle } from 'lucide-react';

export const UserMonitoringTab: React.FC = () => {
  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-black text-slate-800">モニタリング</h2>
      </div>

      {/* 1. 次回モニタリング期限 */}
      <div className="bg-amber-50 border-l-4 border-amber-500 p-6 rounded-r-2xl shadow-sm flex items-start gap-4">
        <div className="p-3 bg-amber-100 rounded-xl text-amber-700 mt-1"><AlertTriangle className="w-6 h-6" /></div>
        <div>
          <h3 className="text-sm font-bold text-amber-700 mb-1">次回モニタリング期限</h3>
          <p className="text-2xl font-black text-amber-900">2026年9月上旬 <span className="text-sm font-bold text-amber-700 ml-2">(残り約3ヶ月)</span></p>
          <p className="text-sm font-medium text-amber-800 mt-2">前回の実施から期間が空いています。次回の準備を進めてください。</p>
        </div>
      </div>

      {/* 2. 現在評価対象の計画 */}
      <div>
        <h3 className="text-lg font-black text-slate-800 mb-4 flex items-center gap-2"><FileText className="w-5 h-5 text-indigo-600" /> 現在評価対象の計画</h3>
        <div className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center gap-2 mb-2">
            <span className="bg-emerald-100 text-emerald-700 px-3 py-1 rounded-full text-xs font-bold flex items-center gap-1">
              <CheckCircle className="w-3 h-3" /> 有効 (ACTIVE)
            </span>
            <span className="text-sm font-bold text-slate-500">第3期 計画</span>
          </div>
          <h4 className="text-lg font-black text-slate-800 mb-3">就労に向けた基礎スキルの習得と生活リズムの安定</h4>
          <div className="text-sm font-medium text-slate-600 bg-slate-50 p-3 rounded-xl border border-slate-100">
            この計画に対する日々の支援記録（日報）をもとに、目標の達成度を評価します。
          </div>
        </div>
      </div>

      {/* 3. 新規モニタリング実施 */}
      <div className="pt-2">
        <button className="flex items-center justify-center gap-2 w-full md:w-auto bg-indigo-600 text-white px-6 py-3 rounded-xl font-bold hover:bg-indigo-700 transition-colors shadow-sm text-lg">
          <Plus className="w-6 h-6" /> 新規モニタリング実施
        </button>
      </div>

      {/* 4. 過去のモニタリング履歴 */}
      <div className="pt-4 border-t border-slate-200">
        <h3 className="text-lg font-black text-slate-800 mb-4 flex items-center gap-2"><Clock className="w-5 h-5 text-slate-400" /> 過去のモニタリング履歴</h3>
        <div className="space-y-4">
          <div className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm">
            <div className="flex justify-between items-start mb-3">
              <div>
                <div className="text-xs font-bold text-slate-400 mb-1">実施日: 2026/03/15</div>
                <h4 className="text-md font-bold text-slate-800">第2期 計画の評価</h4>
              </div>
              <span className="text-xs font-bold text-slate-500 bg-white border border-slate-200 px-2 py-1 rounded-lg">記録者: サビ管 鈴木</span>
            </div>
            <p className="text-sm font-medium text-slate-700 mb-3">
              生活リズムは概ね安定してきたが、まだ週3日の通所には波がある。次期計画では引き続き通所の安定化を目標とする。
            </p>
            <button className="text-sm font-bold text-indigo-600 hover:text-indigo-800 underline decoration-indigo-200 underline-offset-4">詳細を見る</button>
          </div>
        </div>
      </div>
    </div>
  );
};
