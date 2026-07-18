import React, { useState, useEffect } from 'react';
import { X, Clock, Trash2 } from 'lucide-react';
import dayjs from 'dayjs';

interface Props {
  open: boolean;
  onClose: () => void;
  onSave: (data: any) => Promise<void>;
  onDelete?: () => Promise<void>;
  shift?: any; // existing shift if any
  supporterId: number;
  supporterName: string;
  targetDate: string; // YYYY-MM-DD
}

export const ManualShiftEditModal: React.FC<Props> = ({ 
  open, onClose, onSave, onDelete, shift, supporterId, supporterName, targetDate 
}) => {
  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime] = useState('');
  const [breakMinutes, setBreakMinutes] = useState(0);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) {
      if (shift) {
        setStartTime(shift.planned_start_time ? dayjs(shift.planned_start_time).format('HH:mm') : '');
        setEndTime(shift.planned_end_time ? dayjs(shift.planned_end_time).format('HH:mm') : '');
        setBreakMinutes(shift.planned_break_minutes || 0);
      } else {
        setStartTime('09:00');
        setEndTime('18:00');
        setBreakMinutes(60);
      }
    }
  }, [open, shift]);

  if (!open) return null;

  const handleSave = async () => {
    if (!startTime || !endTime) {
      alert("開始時間と終了時間を入力してください");
      return;
    }
    setLoading(true);
    try {
      await onSave({
        supporter_id: supporterId,
        target_date: targetDate,
        start_time: startTime,
        end_time: endTime,
        break_minutes: breakMinutes
      });
      onClose();
    } catch (e: any) {
      console.error(e);
      alert(e.response?.data?.msg || "エラーが発生しました");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!onDelete) return;
    if (!window.confirm("このシフトを削除しますか？")) return;
    
    setLoading(true);
    try {
      await onDelete();
      onClose();
    } catch (e: any) {
      console.error(e);
      alert(e.response?.data?.msg || "エラーが発生しました");
    } finally {
      setLoading(false);
    }
  };

  const dateStr = dayjs(targetDate).format('YYYY年M月D日');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50">
          <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
            <Clock className="w-5 h-5 text-indigo-600" />
            シフトの個別編集
          </h2>
          <button 
            onClick={!loading ? onClose : undefined}
            className="text-slate-400 hover:text-slate-600 transition-colors"
            disabled={loading}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6">
          <div className="mb-4 p-3 bg-slate-50 rounded-lg text-sm border border-slate-100">
            <div><span className="text-slate-500">対象者:</span> <span className="font-bold text-slate-700">{supporterName}</span></div>
            <div><span className="text-slate-500">日付:</span> <span className="font-bold text-slate-700">{dateStr}</span></div>
          </div>

          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-bold text-slate-700 mb-1">開始時間</label>
              <input
                type="time"
                value={startTime}
                onChange={e => setStartTime(e.target.value)}
                disabled={loading}
                className="w-full border border-slate-300 rounded-lg p-2 text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-bold text-slate-700 mb-1">終了時間</label>
              <input
                type="time"
                value={endTime}
                onChange={e => setEndTime(e.target.value)}
                disabled={loading}
                className="w-full border border-slate-300 rounded-lg p-2 text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
              />
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-bold text-slate-700 mb-1">休憩（分）</label>
            <input
              type="number"
              value={breakMinutes}
              onChange={e => setBreakMinutes(parseInt(e.target.value) || 0)}
              disabled={loading}
              className="w-full border border-slate-300 rounded-lg p-2 text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
            />
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-100 bg-slate-50 flex justify-between items-center gap-3">
          {shift && onDelete ? (
            <button
              onClick={handleDelete}
              disabled={loading}
              className="px-3 py-2 text-sm font-bold text-rose-600 hover:bg-rose-100 rounded-xl transition-colors disabled:opacity-50 flex items-center gap-1"
            >
              <Trash2 className="w-4 h-4" /> 削除
            </button>
          ) : <div></div>}
          
          <div className="flex gap-2">
            <button
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 text-sm font-bold text-slate-600 hover:bg-slate-200 rounded-xl transition-colors disabled:opacity-50"
            >
              キャンセル
            </button>
            <button
              onClick={handleSave}
              disabled={loading}
              className="px-6 py-2 text-sm font-bold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl transition-colors disabled:opacity-50"
            >
              保存する
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
