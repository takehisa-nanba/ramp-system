import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Clock, CheckCircle, FileEdit, AlertTriangle, ArrowRight, Calendar } from 'lucide-react';
import { fetchUserAttendanceRecords, type UserAttendanceItem } from '../../services/userService';

export const UserAttendanceTab: React.FC<{ userId: number }> = ({ userId }) => {
  const navigate = useNavigate();
  const [items, setItems] = useState<UserAttendanceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadAttendanceRecords = () => {
    setLoading(true);
    setError(null);
    fetchUserAttendanceRecords(userId)
      .then(res => setItems(res.items))
      .catch(() => setError('利用実績の取得に失敗しました。'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadAttendanceRecords();
  }, [userId]);

  const formatTime = (isoString: string | null) => {
    if (!isoString) return '—';
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '—';
    }
  };

  const getLogStatusBadge = (status: 'missing' | 'draft' | 'completed') => {
    switch (status) {
      case 'completed':
        return (
          <span className="flex items-center gap-1 text-xs font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-full">
            <CheckCircle className="w-3.5 h-3.5" /> 日報 完了
          </span>
        );
      case 'draft':
        return (
          <span className="flex items-center gap-1 text-xs font-bold text-amber-600 bg-amber-50/50 border border-amber-100 px-2.5 py-1 rounded-full">
            <FileEdit className="w-3.5 h-3.5" /> 日報 下書き
          </span>
        );
      case 'missing':
      default:
        return (
          <span className="flex items-center gap-1 text-xs font-bold text-amber-700 bg-amber-50 border border-amber-200 px-2.5 py-1 rounded-full">
            <AlertTriangle className="w-3.5 h-3.5" /> 日報 未作成
          </span>
        );
    }
  };

  const handleAction = (item: UserAttendanceItem) => {
    if (item.daily_log_status === 'missing' || item.daily_log_status === 'draft') {
      const params = new URLSearchParams();
      params.append('date', item.date);
      params.append('attendance_record_id', item.attendance_record_id.toString());
      if (item.check_in_at) params.append('check_in_at', item.check_in_at);
      if (item.check_out_at) params.append('check_out_at', item.check_out_at);
      navigate(`/users/${userId}/daily-logs?${params.toString()}`);
    } else {
      navigate(`/users/${userId}/daily-logs`);
    }
  };

  if (loading && items.length === 0) return <div className="flex justify-center p-12"><div className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" /></div>;
  if (error) return <div className="bg-rose-50 text-rose-600 p-4 rounded-xl font-bold flex items-center gap-2"><AlertTriangle className="w-5 h-5" />{error}</div>;

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-black text-slate-800 flex items-center gap-2">
            <Calendar className="w-6 h-6 text-indigo-600" />
            利用実績一覧
          </h2>
          <p className="text-sm text-slate-500 mt-1 font-medium">客観的な来所・退所打刻の実績と、対応する日報の作成状況です。</p>
        </div>
      </div>

      {items.length === 0 ? (
        <div className="bg-slate-50 text-slate-500 p-8 rounded-2xl text-center font-bold border border-slate-200">
          利用実績が登録されていません。
        </div>
      ) : (
        <div className="space-y-4">
          {items.map(item => (
            <div key={item.date} className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm hover:shadow-md transition-shadow flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2 flex-wrap">
                  <div className="text-sm font-black text-indigo-600">{item.date}</div>
                  {getLogStatusBadge(item.daily_log_status)}
                </div>
                <div className="flex gap-6 text-sm font-medium text-slate-500">
                  <div className="flex items-center gap-1.5">
                    <Clock className="w-4 h-4 text-slate-400" />
                    <span>来所時間:</span>
                    <span className="font-bold text-slate-700">{formatTime(item.check_in_at)}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Clock className="w-4 h-4 text-slate-400" />
                    <span>退所時間:</span>
                    <span className="font-bold text-slate-700">{formatTime(item.check_out_at)}</span>
                  </div>
                </div>
              </div>

              <div className="shrink-0">
                <button
                  onClick={() => handleAction(item)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl font-bold text-xs transition-all ${
                    item.daily_log_status === 'missing'
                      ? 'bg-amber-600 text-white hover:bg-amber-700 shadow-sm'
                      : item.daily_log_status === 'draft'
                      ? 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-sm'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200 border border-slate-200'
                  }`}
                >
                  {item.daily_log_status === 'missing' && 'この実績の日報を作成'}
                  {item.daily_log_status === 'draft' && '下書きから日報を作成'}
                  {item.daily_log_status === 'completed' && '日報を確認'}
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
