import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Users, Clock, CheckCircle, FileEdit, AlertTriangle, ArrowRight } from 'lucide-react';
import { fetchTodayUsers, type TodayUserItem } from '../services/userService';

const TodayUsersPage: React.FC = () => {
  const navigate = useNavigate();
  const [items, setItems] = useState<TodayUserItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadTodayUsers = async () => {
      try {
        setLoading(true);
        const res = await fetchTodayUsers();
        setItems(res.items);
      } catch (err) {
        console.error(err);
        setError('本日の利用状況の取得に失敗しました。');
      } finally {
        setLoading(false);
      }
    };
    loadTodayUsers();
  }, []);

  // ソート順の定義
  // 1. 日報未作成 (missing)
  // 2. 下書き (draft)
  // 3. 来所中 (CHECKED_IN 且つ completed)
  // 4. 完了 (CHECKED_OUT 且つ completed)
  const sortedItems = useMemo(() => {
    const getSortWeight = (item: TodayUserItem) => {
      if (item.daily_log_status === 'missing') return 1;
      if (item.daily_log_status === 'draft') return 2;
      if (item.status === 'CHECKED_IN' && item.daily_log_status === 'completed') return 3;
      return 4; // CHECKED_OUT & completed
    };

    return [...items].sort((a, b) => getSortWeight(a) - getSortWeight(b));
  }, [items]);

  const formatTime = (isoString: string | null) => {
    if (!isoString) return '—';
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '—';
    }
  };

  const getStatusBadge = (item: TodayUserItem) => {
    if (item.daily_log_status === 'missing') {
      return (
        <span className="flex items-center gap-1.5 text-xs font-bold text-amber-700 bg-amber-50 border border-amber-200 px-3 py-1.5 rounded-full">
          <AlertTriangle className="w-3.5 h-3.5" /> 日報 未作成
        </span>
      );
    }
    if (item.daily_log_status === 'draft') {
      return (
        <span className="flex items-center gap-1.5 text-xs font-bold text-amber-600 bg-amber-50/50 border border-amber-100 px-3 py-1.5 rounded-full">
          <FileEdit className="w-3.5 h-3.5" /> 日報 下書き
        </span>
      );
    }
    return (
      <span className="flex items-center gap-1.5 text-xs font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-3 py-1.5 rounded-full">
        <CheckCircle className="w-3.5 h-3.5" /> 日報 完了
      </span>
    );
  };

  const getAttendanceStatusBadge = (item: TodayUserItem) => {
    if (item.status === 'CHECKED_IN') {
      return (
        <span className="text-[10px] font-black tracking-wider uppercase bg-sky-100 text-sky-700 border border-sky-200 px-2 py-0.5 rounded-md">
          利用中 (来所)
        </span>
      );
    }
    return (
      <span className="text-[10px] font-black tracking-wider uppercase bg-slate-100 text-slate-500 border border-slate-200 px-2 py-0.5 rounded-md">
        退所済み
      </span>
    );
  };

  const handleAction = (item: TodayUserItem) => {
    const todayStr = new Date().toISOString().split('T')[0];
    if (item.daily_log_status === 'missing' || item.daily_log_status === 'draft') {
      const params = new URLSearchParams();
      params.append('date', todayStr);
      params.append('attendance_record_id', item.attendance_record_id.toString());
      if (item.check_in_at) params.append('check_in_at', item.check_in_at);
      if (item.check_out_at) params.append('check_out_at', item.check_out_at);
      navigate(`/users/${item.user_id}/daily-logs?${params.toString()}`);
    } else {
      navigate(`/users/${item.user_id}/daily-logs`);
    }
  };

  return (
    <div className="p-6 md:p-8 animate-in fade-in duration-500 max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-black text-slate-800 tracking-tight flex items-center gap-3">
          <Users className="text-indigo-600 w-8 h-8" />
          本日の利用状況
        </h1>
        <p className="text-slate-500 mt-2 font-medium">
          本日来所している利用者の打刻実績と、日報の記録状況です。未処理の記録から優先して表示されます。
        </p>
      </div>

      {loading ? (
        <div className="flex justify-center p-12">
          <div className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"></div>
        </div>
      ) : error ? (
        <div className="bg-rose-50 text-rose-600 p-4 rounded-xl font-bold">{error}</div>
      ) : sortedItems.length === 0 ? (
        <div className="p-12 text-center text-slate-500 font-bold bg-slate-50 rounded-2xl border border-slate-200">
          本日チェックインした利用者はいません。
        </div>
      ) : (
        <div className="space-y-4">
          {sortedItems.map((item) => {
            return (
              <div
                key={item.user_id}
                className={`bg-white border p-5 rounded-2xl shadow-sm transition-all flex flex-col md:flex-row md:items-center justify-between gap-4 border-slate-200 hover:border-slate-300 hover:shadow-md`}
              >
                {/* 利用者プロフィール ＆ 打刻時間 */}
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2 flex-wrap">
                    <h2 className="text-lg font-black text-slate-800">{item.user_name}</h2>
                    {getAttendanceStatusBadge(item)}
                    {getStatusBadge(item)}
                  </div>
                  
                  <div className="flex gap-6 text-sm font-medium text-slate-500 mt-1">
                    <div className="flex items-center gap-1.5">
                      <Clock className="w-4 h-4 text-slate-400" />
                      <span>来所:</span>
                      <span className="font-bold text-slate-700">{formatTime(item.check_in_at)}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Clock className="w-4 h-4 text-slate-400" />
                      <span>退所:</span>
                      <span className="font-bold text-slate-700">{formatTime(item.check_out_at)}</span>
                    </div>
                  </div>
                </div>

                {/* 操作アクションボタン */}
                <div className="shrink-0 flex items-center justify-end">
                  <button
                    onClick={() => handleAction(item)}
                    className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-sm transition-all ${
                      item.daily_log_status === 'missing'
                        ? 'bg-amber-600 text-white hover:bg-amber-700 shadow-sm'
                        : item.daily_log_status === 'draft'
                        ? 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-sm'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200 border border-slate-200'
                    }`}
                  >
                    {item.daily_log_status === 'missing' && '記録する'}
                    {item.daily_log_status === 'draft' && '続きから記録'}
                    {item.daily_log_status === 'completed' && '日報を確認'}
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default TodayUsersPage;
