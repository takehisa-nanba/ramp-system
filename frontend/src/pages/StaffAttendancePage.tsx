// frontend/src/pages/StaffAttendancePage.tsx

import React, { useState } from 'react';
import { Heading } from '../components/common/Typography';
import { Calendar, Play, FileEdit, CheckCircle } from 'lucide-react';
import { attendanceApi } from '../services/attendanceApi';

export const StaffAttendancePage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);

  const handleGenerateShifts = async () => {
    setLoading(true);
    try {
      const res = await attendanceApi.generateShifts(new Date().getFullYear(), selectedMonth);
      alert(`シフトを ${res.count} 件生成しました。`);
    } catch (e: any) {
      alert(e.response?.data?.msg || 'エラーが発生しました');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <Heading level={1} className="mb-6 flex items-center gap-3">
        <Calendar className="w-8 h-8 text-indigo-600" />
        勤怠・シフト詳細画面
      </Heading>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        {/* 基本シフト・一括生成 */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200">
          <Heading level={3} className="mb-4 flex items-center gap-2">
            <Play className="w-5 h-5 text-emerald-600" />
            シフトの自動生成
          </Heading>
          <p className="text-sm text-slate-500 mb-4">
            登録されている「曜日ごとの基本シフトパターン」に基づいて、指定した月のシフトを一括生成します。
          </p>
          <div className="flex gap-4 items-center">
            <select 
              value={selectedMonth} 
              onChange={e => setSelectedMonth(Number(e.target.value))}
              className="px-4 py-2 border rounded-xl"
            >
              {[...Array(12)].map((_, i) => (
                <option key={i+1} value={i+1}>{i+1}月</option>
              ))}
            </select>
            <button 
              onClick={handleGenerateShifts}
              disabled={loading}
              className="px-6 py-2 bg-emerald-600 text-white font-bold rounded-xl hover:bg-emerald-700 disabled:opacity-50"
            >
              {loading ? '生成中...' : '当月のシフトを自動生成する'}
            </button>
          </div>
        </div>

        {/* 申請アクション */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200">
          <Heading level={3} className="mb-4 flex items-center gap-2">
            <FileEdit className="w-5 h-5 text-indigo-600" />
            打刻修正・休暇の申請
          </Heading>
          <p className="text-sm text-slate-500 mb-4">
            一般スタッフは、自身の打刻実績や予定を勝手に書き換えることはできません。
            修正や休暇の取得を希望する場合は、こちらから申請（Decision要求）を行ってください。
          </p>
          <button 
            onClick={() => alert('申請フォームモーダル（未実装）')}
            className="px-6 py-2 bg-indigo-600 text-white font-bold rounded-xl hover:bg-indigo-700"
          >
            新規修正申請を作成する
          </button>
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="p-4 bg-slate-50 border-b flex justify-between items-center">
          <h2 className="font-bold text-slate-700 text-lg">月間タイムカード (予定と実績の比較)</h2>
          <span className="text-sm text-slate-500 px-3 py-1 bg-white rounded border">
            表示中のスタッフ: 全体
          </span>
        </div>
        <div className="p-8 text-center text-slate-400">
          <Calendar className="w-16 h-16 mx-auto mb-4 opacity-20" />
          <p>月間カレンダーおよび日別の予定/実績データグリッドがここに表示されます。<br/>
          （管理者の場合は直接編集ボタンが表示されます）</p>
        </div>
      </div>
    </div>
  );
};

export default StaffAttendancePage;
