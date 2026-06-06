import React from 'react';
import { FileText, Target, Calendar, CheckCircle, Plus, History } from 'lucide-react';

export const UserSupportPlanTab: React.FC<{ userId: number }> = () => {
  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-black text-slate-800">個別支援計画</h2>
        <button className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-xl font-bold hover:bg-indigo-700 transition-colors shadow-sm">
          <Plus className="w-5 h-5" /> 次期計画を作成
        </button>
      </div>

      {/* 現在有効な計画 (ACTIVE) */}
      <div className="bg-white border-2 border-emerald-100 p-6 rounded-2xl shadow-sm relative overflow-hidden">
        <div className="absolute top-0 left-0 w-2 h-full bg-emerald-500"></div>
        <div className="flex justify-between items-start mb-6">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="bg-emerald-100 text-emerald-700 px-3 py-1 rounded-full text-xs font-bold flex items-center gap-1">
                <CheckCircle className="w-3 h-3" /> 有効 (ACTIVE)
              </span>
              <span className="text-sm font-bold text-slate-500">第3期 計画</span>
            </div>
            <h3 className="text-2xl font-black text-slate-800">就労に向けた基礎スキルの習得と生活リズムの安定</h3>
          </div>
          <div className="text-right">
            <div className="text-xs font-bold text-slate-400 mb-1">計画期間</div>
            <div className="text-sm font-bold text-slate-700">2026/04/01 〜 2026/09/30</div>
          </div>
        </div>

        {/* 支援方針 */}
        <div className="mb-6">
          <h4 className="text-sm font-bold text-slate-400 mb-2 flex items-center gap-2"><FileText className="w-4 h-4" /> 総合的な支援方針</h4>
          <p className="text-slate-700 font-medium bg-slate-50 p-4 rounded-xl leading-relaxed">
            生活リズムを安定させ、週3日の通所を継続することを最初の目標とします。
            また、PCスキルの基礎を習得し、将来的な就労移行に向けた準備を進めます。
            本人のペースを尊重し、スモールステップで成功体験を積めるよう支援を行います。
          </p>
        </div>

        {/* 短期目標 */}
        <div className="mb-6">
          <h4 className="text-sm font-bold text-slate-400 mb-2 flex items-center gap-2"><Target className="w-4 h-4" /> 短期目標・支援内容</h4>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="border border-slate-200 rounded-xl p-4 hover:border-indigo-200 hover:shadow-sm transition-all">
              <div className="text-indigo-600 font-black mb-2">1. PC操作の基礎習得</div>
              <div className="space-y-3">
                <div>
                  <div className="text-xs font-bold text-slate-400">本人の希望</div>
                  <div className="text-sm font-medium text-slate-700">タイピングができるようになりたい。</div>
                </div>
                <div>
                  <div className="text-xs font-bold text-slate-400">具体的な支援内容</div>
                  <div className="text-sm font-medium text-slate-700">タイピングソフトを用いた1日30分の練習。週1回の進捗確認。</div>
                </div>
              </div>
            </div>
            <div className="border border-slate-200 rounded-xl p-4 hover:border-indigo-200 hover:shadow-sm transition-all">
              <div className="text-indigo-600 font-black mb-2">2. 生活リズムの安定化</div>
              <div className="space-y-3">
                <div>
                  <div className="text-xs font-bold text-slate-400">本人の希望</div>
                  <div className="text-sm font-medium text-slate-700">休まずに通えるようになりたい。</div>
                </div>
                <div>
                  <div className="text-xs font-bold text-slate-400">具体的な支援内容</div>
                  <div className="text-sm font-medium text-slate-700">毎朝のバイタルチェック。週3日の通所リズムの確立。</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 次回モニタリング予定 */}
        <div className="bg-amber-50 border border-amber-100 rounded-xl p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-amber-200 p-2 rounded-lg text-amber-700"><Calendar className="w-5 h-5" /></div>
            <div>
              <div className="text-xs font-bold text-amber-700">次回モニタリング予定</div>
              <div className="text-sm font-black text-amber-900">2026年9月上旬</div>
            </div>
          </div>
          <button className="text-sm font-bold text-amber-700 hover:text-amber-800 underline decoration-amber-300 underline-offset-4 transition-colors">
            予定をカレンダーに追加
          </button>
        </div>
      </div>

      {/* 計画履歴 */}
      <div>
        <h3 className="text-lg font-black text-slate-800 mb-4 flex items-center gap-2"><History className="w-5 h-5 text-slate-400" /> 計画履歴</h3>
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th className="p-4 text-xs font-black text-slate-500 uppercase">ステータス</th>
                <th className="p-4 text-xs font-black text-slate-500 uppercase">期間</th>
                <th className="p-4 text-xs font-black text-slate-500 uppercase">作成者</th>
                <th className="p-4 text-xs font-black text-slate-500 uppercase">アクション</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              <tr className="hover:bg-slate-50 transition-colors">
                <td className="p-4">
                  <span className="text-xs font-bold text-slate-500 bg-slate-100 px-2 py-1 rounded-full">過去 (ARCHIVED)</span>
                </td>
                <td className="p-4 text-sm font-bold text-slate-700">2025/10/01 〜 2026/03/31</td>
                <td className="p-4 text-sm font-medium text-slate-600">鈴木 管理者</td>
                <td className="p-4">
                  <button className="text-sm font-bold text-indigo-600 hover:text-indigo-800">詳細を見る</button>
                </td>
              </tr>
              <tr className="hover:bg-slate-50 transition-colors">
                <td className="p-4">
                  <span className="text-xs font-bold text-slate-500 bg-slate-100 px-2 py-1 rounded-full">過去 (ARCHIVED)</span>
                </td>
                <td className="p-4 text-sm font-bold text-slate-700">2025/04/01 〜 2025/09/30</td>
                <td className="p-4 text-sm font-medium text-slate-600">鈴木 管理者</td>
                <td className="p-4">
                  <button className="text-sm font-bold text-indigo-600 hover:text-indigo-800">詳細を見る</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
};
