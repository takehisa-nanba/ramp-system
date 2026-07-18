// frontend/src/pages/StaffAttendancePage.tsx

import React, { useState, useEffect, useMemo } from 'react';
import { Heading } from '../components/common/Typography';
import { Calendar, Play, FileEdit } from 'lucide-react';
import { attendanceApi, type ShiftRecord } from '../services/attendanceApi';
import dayjs from 'dayjs';
import { AiShiftGenerationModal } from '../components/attendance/AiShiftGenerationModal';
import { useAuth } from '../context/AuthContext';
import { ManualShiftEditModal } from '../components/attendance/ManualShiftEditModal';
import StaffTimecardWidget from '../components/dashboard/StaffTimecardWidget';

export const StaffAttendancePage: React.FC = () => {
  const { user } = useAuth();
  const isManager = user?.roleScopes?.some(s => ['SYSTEM', 'CORPORATE'].includes(s)) ?? false;
  const [loading, setLoading] = useState(false);
  const [shiftsLoading, setShiftsLoading] = useState(false);
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [shifts, setShifts] = useState<ShiftRecord[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [manualEditData, setManualEditData] = useState<{ open: boolean; shift?: ShiftRecord; supporterId: number; supporterName: string; targetDate: string } | null>(null);

  const loadShifts = async () => {
    setShiftsLoading(true);
    try {
      const res = await attendanceApi.getShifts(selectedYear, selectedMonth);
      setShifts(res.items);
    } catch (e) {
      console.error("Failed to load shifts", e);
    } finally {
      setShiftsLoading(false);
    }
  };

  useEffect(() => {
    loadShifts();
  }, [selectedYear, selectedMonth]);

  const handleGenerateClick = () => {
    setIsModalOpen(true);
  };

  const handleGenerateShifts = async (instruction: string) => {
    setLoading(true);
    try {
      const res = await attendanceApi.generateShifts(selectedYear, selectedMonth, undefined, instruction);
      alert(`シフトを ${res.count} 件生成・調整しました。`);
    } catch (e: any) {
      alert(e.response?.data?.msg || 'エラーが発生しました');
    } finally {
      setLoading(false);
      loadShifts();
    }
  };

  const handleCellClick = (supporterId: number, supporterName: string, day: number, shift?: ShiftRecord) => {
    if (!isManager) return; // Non-managers cannot edit shifts
    // If the shift is confirmed, we prevent editing visually or in API
    if (shift && shift.is_confirmed) {
      alert("確定済みのシフト（またはタイムカードが存在する日）は手動で変更できません。");
      return;
    }
    const dStr = day.toString().padStart(2, '0');
    const targetDate = `${selectedYear}-${selectedMonth.toString().padStart(2, '0')}-${dStr}`;
    setManualEditData({
      open: true,
      shift,
      supporterId,
      supporterName,
      targetDate
    });
  };

  const handleManualSave = async (data: any) => {
    if (manualEditData?.shift) {
      await attendanceApi.updateManualShift(manualEditData.shift.id, {
        start_time: data.start_time,
        end_time: data.end_time,
        break_minutes: data.break_minutes
      });
    } else {
      await attendanceApi.createManualShift(data);
    }
    loadShifts();
  };

  const handleManualDelete = async () => {
    if (manualEditData?.shift) {
      await attendanceApi.deleteManualShift(manualEditData.shift.id);
      loadShifts();
    }
  };

  const daysInMonth = useMemo(() => new Date(selectedYear, selectedMonth, 0).getDate(), [selectedYear, selectedMonth]);
  const daysArray = useMemo(() => Array.from({ length: daysInMonth }, (_, i) => i + 1), [daysInMonth]);

  const shiftsBySupporter = useMemo(() => {
    const grouped: Record<string, { supporter_id: number; name: string; job_title: string; employment_type: string; shifts: Record<number, ShiftRecord> }> = {};
    shifts.forEach(s => {
      const key = `${s.supporter_id}_${s.job_title}`;
      if (!grouped[key]) {
        grouped[key] = { supporter_id: s.supporter_id, name: s.supporter_name, job_title: s.job_title, employment_type: s.employment_type, shifts: {} };
      }
      const day = dayjs(s.target_date).date();
      grouped[key].shifts[day] = s;
    });
    
    return Object.values(grouped).sort((a, b) => {
      if (a.supporter_id !== b.supporter_id) return a.supporter_id - b.supporter_id;
      return a.job_title.localeCompare(b.job_title);
    });
  }, [shifts]);

  const getDayOfWeekStr = (day: number) => {
    const d = new Date(selectedYear, selectedMonth - 1, day);
    const dow = d.getDay();
    return ['日', '月', '火', '水', '木', '金', '土'][dow];
  };
  
  const getDayOfWeekColor = (day: number) => {
    const d = new Date(selectedYear, selectedMonth - 1, day);
    const dow = d.getDay();
    if (dow === 0) return 'text-rose-500 bg-rose-50/30';
    if (dow === 6) return 'text-blue-500 bg-blue-50/30';
    return 'text-slate-500';
  };

  return (
    <div className="p-8 max-w-[1600px] mx-auto">
      <Heading variant="h1" className="mb-6 flex items-center gap-3">
        <Calendar className="w-8 h-8 text-indigo-600" />
        勤怠・シフト詳細画面
      </Heading>
      
      {/* タイムカード（打刻）ウィジェット */}
      <StaffTimecardWidget />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* 基本シフト・一括生成 */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200">
          <Heading variant="h3" className="mb-4 flex items-center gap-2">
            <Calendar className="w-5 h-5 text-emerald-600" />
            {isManager ? 'シフトの自動生成' : '表示月の選択'}
          </Heading>
          
          {isManager && (
            <>
              <p className="text-sm text-slate-500 mb-2">
                登録されている「曜日ごとの基本シフトパターン」に基づいて、指定した月のシフトを一括生成します。
              </p>
              <div className="text-xs text-indigo-600 bg-indigo-50 p-2 rounded mb-4">
                💡 <strong>使い分けのヒント：</strong><br/>
                大幅な予定変更や複雑な調整は「AIシフト生成」をお使いください。<br/>
                「この人だけ今日休みにしたい」「時間をずらしたい」といった軽微な変更は、下の表のセルを直接クリックして手動で素早く変更できます。
              </div>
            </>
          )}

          <div className="flex flex-wrap gap-4 items-center">
            <select 
              value={selectedYear} 
              onChange={e => setSelectedYear(Number(e.target.value))}
              className="px-4 py-2 border rounded-xl font-bold"
            >
              {[...Array(5)].map((_, i) => {
                const y = new Date().getFullYear() - 2 + i;
                return <option key={y} value={y}>{y}年</option>;
              })}
            </select>
            <select 
              value={selectedMonth} 
              onChange={e => setSelectedMonth(Number(e.target.value))}
              className="px-4 py-2 border rounded-xl font-bold"
            >
              {[...Array(12)].map((_, i) => (
                <option key={i+1} value={i+1}>{i+1}月</option>
              ))}
            </select>
            
            {isManager && (
              <button 
                onClick={handleGenerateClick}
                disabled={loading}
                className="px-6 py-2 bg-emerald-600 text-white font-bold rounded-xl hover:bg-emerald-700 disabled:opacity-50 flex items-center gap-2"
              >
                <Play className="w-4 h-4" />
                {loading ? '処理中...' : '当月のシフトを自動生成する'}
              </button>
            )}
          </div>
        </div>

        {/* 申請アクション */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200">
          <Heading variant="h3" className="mb-4 flex items-center gap-2">
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
        
        {shiftsLoading ? (
          <div className="p-8 text-center text-slate-500 font-bold">読み込み中...</div>
        ) : shifts.length === 0 ? (
          <div className="p-8 text-center text-slate-400">
            <Calendar className="w-16 h-16 mx-auto mb-4 opacity-20" />
            <p>この月のシフト予定はまだ作成されていません。</p>
          </div>
        ) : (
          <div className="overflow-x-auto relative">
            <table className="w-full text-left text-sm text-slate-600 border-collapse">
              <thead className="bg-slate-50 text-slate-500 font-bold border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3 sticky left-0 z-20 bg-slate-50 border-r border-b border-slate-200 min-w-[140px] shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)]">職員名</th>
                  {daysArray.map(d => (
                    <th key={d} className={`px-2 py-2 min-w-[70px] text-center border-r border-slate-100 ${getDayOfWeekColor(d)}`}>
                      <div className="text-[15px] font-black">{d}</div>
                      <div className="text-[10px] opacity-70 mt-0.5">{getDayOfWeekStr(d)}</div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {shiftsBySupporter.map((staff, idx) => (
                  <tr key={idx} className="group hover:bg-indigo-50/30 transition-colors">
                    <td className="px-4 py-3 sticky left-0 z-10 bg-white border-r border-slate-200 group-hover:bg-indigo-50/50 transition-colors shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)]">
                      <div className="font-bold text-slate-700">{staff.name}</div>
                      <div className="flex flex-wrap gap-1.5 items-center mt-1.5">
                        <span className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded font-bold break-keep">{staff.job_title}</span>
                        <span className="text-[10px] bg-indigo-50 text-indigo-600 border border-indigo-100 px-1.5 py-0.5 rounded font-bold break-keep">{staff.employment_type}</span>
                      </div>
                    </td>
                    {daysArray.map(d => {
                      const shift = staff.shifts[d];
                      const isWeekend = new Date(selectedYear, selectedMonth - 1, d).getDay() === 0 || new Date(selectedYear, selectedMonth - 1, d).getDay() === 6;
                      return (
                        <td 
                          key={d} 
                          className={`px-2 py-2 text-center border-r border-slate-100 align-middle ${isWeekend ? 'bg-slate-50/50' : ''} hover:bg-indigo-50 cursor-pointer transition-colors`}
                          onClick={() => handleCellClick(staff.supporter_id, staff.name, d, shift)}
                        >
                          {shift ? (
                            <div className={`flex flex-col items-center justify-center gap-0.5 py-1.5 rounded-lg border ${shift.is_confirmed ? 'bg-indigo-50 border-indigo-100' : 'bg-white border-slate-200'}`}>
                              <div className="text-[11px] font-black tracking-tighter text-slate-700">
                                {shift.planned_start_time ? dayjs(shift.planned_start_time).format('HH:mm') : '-'}
                              </div>
                              <div className="text-[10px] text-slate-300 leading-none">|</div>
                              <div className="text-[11px] font-black tracking-tighter text-slate-700">
                                {shift.planned_end_time ? dayjs(shift.planned_end_time).format('HH:mm') : '-'}
                              </div>
                              {shift.is_confirmed && <div className="text-[9px] text-indigo-500 font-black scale-90 mt-1">確定</div>}
                            </div>
                          ) : (
                            <div className="text-slate-200 text-xs">-</div>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <AiShiftGenerationModal
        open={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onGenerate={handleGenerateShifts}
        year={selectedYear}
        month={selectedMonth}
      />

      {manualEditData && (
        <ManualShiftEditModal
          open={manualEditData.open}
          onClose={() => setManualEditData(null)}
          onSave={handleManualSave}
          onDelete={manualEditData.shift ? handleManualDelete : undefined}
          shift={manualEditData.shift}
          supporterId={manualEditData.supporterId}
          supporterName={manualEditData.supporterName}
          targetDate={manualEditData.targetDate}
        />
      )}
    </div>
  );
};

export default StaffAttendancePage;
