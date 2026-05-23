import React, { useState } from 'react';
import { X, Loader2, Calendar, CheckCircle2 } from 'lucide-react';
import { updateUserStatus, type StatusMaster } from '../../services/userService';

interface StatusTransitionModalProps {
  isOpen: boolean;
  onClose: () => void;
  userId: number;
  userName: string;
  targetStatuses: StatusMaster[]; // The statuses they can transition to
  title: string;
  description: string;
  requireStartDate?: boolean;
  requireEndDate?: boolean;
  onSuccess: () => void;
}

export const StatusTransitionModal: React.FC<StatusTransitionModalProps> = ({
  isOpen,
  onClose,
  userId,
  userName,
  targetStatuses,
  title,
  description,
  requireStartDate = false,
  requireEndDate = false,
  onSuccess
}) => {
  const [selectedStatusId, setSelectedStatusId] = useState<number | ''>(targetStatuses.length === 1 ? targetStatuses[0].id : '');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedStatusId) {
      setError('ステータスを選択してください。');
      return;
    }
    if (requireStartDate && !startDate) {
      setError('利用開始日を入力してください。');
      return;
    }
    if (requireEndDate && !endDate) {
      setError('利用終了日を入力してください。');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await updateUserStatus(userId, {
        status_id: Number(selectedStatusId),
        service_start_date: startDate || undefined,
        service_end_date: endDate || undefined
      });
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.msg || err.message || '更新に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white rounded-3xl w-full max-w-md shadow-2xl overflow-hidden flex flex-col animate-in zoom-in-95 duration-200">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
          <div>
            <h2 className="text-sm font-black text-slate-800">{title}</h2>
            <p className="text-[10px] text-slate-400 font-bold mt-0.5">{userName} さんのステータスを更新します</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-slate-200 rounded-full text-slate-400 transition-colors">
            <X size={16} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {error && (
            <div className="p-3 bg-rose-50 text-rose-600 text-xs font-bold rounded-xl border border-rose-100">
              {error}
            </div>
          )}
          
          <p className="text-xs text-slate-600 font-bold leading-relaxed">{description}</p>

          <div className="space-y-4">
            {targetStatuses.length > 1 ? (
              <div className="space-y-1.5">
                <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">移行先ステータス</label>
                <select
                  value={selectedStatusId}
                  onChange={(e) => setSelectedStatusId(Number(e.target.value))}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-xs font-bold text-slate-700 outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                  required
                >
                  <option value="" disabled>選択してください</option>
                  {targetStatuses.map(s => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
              </div>
            ) : null}

            {requireStartDate && (
              <div className="space-y-1.5">
                <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
                  <Calendar size={12} />
                  利用開始日
                </label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-xs font-bold text-slate-700 outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                  required
                />
              </div>
            )}

            {requireEndDate && (
              <div className="space-y-1.5">
                <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
                  <Calendar size={12} />
                  利用終了日
                </label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-xs font-bold text-slate-700 outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                  required
                />
              </div>
            )}
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-bold text-slate-500 hover:bg-slate-100 rounded-xl transition-colors"
            >
              キャンセル
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-2 px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-black shadow-sm shadow-indigo-500/30 transition-all disabled:opacity-50"
            >
              {loading ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
              更新する
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
