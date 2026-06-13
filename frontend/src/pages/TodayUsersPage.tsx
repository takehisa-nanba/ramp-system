import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Users, Clock, CheckCircle, FileEdit, AlertTriangle, ArrowRight } from 'lucide-react';
import { fetchTodayUsers, type TodayUserItem } from '../services/userService';
import { Heading, Text, Label } from '../components/common/Typography';

const TodayUsersPage: React.FC = () => {
  const navigate = useNavigate();
  const [items, setItems] = useState<TodayUserItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchParams, setSearchParams] = useSearchParams();

  const statusParam = searchParams.get('status');
  const selectedFilter = (statusParam === 'missing' || statusParam === 'draft' || statusParam === 'completed')
    ? statusParam
    : 'all';

  const setSelectedFilter = (newFilter: 'all' | 'missing' | 'draft' | 'completed') => {
    const newParams = new URLSearchParams(searchParams);
    if (newFilter === 'all') {
      newParams.delete('status');
    } else {
      newParams.set('status', newFilter);
    }
    setSearchParams(newParams);
  };

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

  // フィルタリングとソート順の定義
  // 1. 日報未作成 (missing)
  // 2. 下書き (draft)
  // 3. 来所中 (CHECKED_IN 且つ completed)
  // 4. 完了 (CHECKED_OUT 且つ completed)
  const filteredAndSortedItems = useMemo(() => {
    let result = [...items];
    if (selectedFilter !== 'all') {
      result = result.filter(item => item.daily_log_status === selectedFilter);
    }

    const getSortWeight = (item: TodayUserItem) => {
      if (item.daily_log_status === 'missing') return 1;
      if (item.daily_log_status === 'draft') return 2;
      if (item.status === 'CHECKED_IN' && item.daily_log_status === 'completed') return 3;
      return 4; // CHECKED_OUT & completed
    };

    return result.sort((a, b) => getSortWeight(a) - getSortWeight(b));
  }, [items, selectedFilter]);

  const stats = useMemo(() => {
    const total = items.length;
    const missing = items.filter(item => item.daily_log_status === 'missing').length;
    const draft = items.filter(item => item.daily_log_status === 'draft').length;
    const completed = items.filter(item => item.daily_log_status === 'completed').length;
    return { total, missing, draft, completed };
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
        <Label variant="badge" className="flex items-center gap-1.5 text-amber-700 bg-amber-50 border border-amber-200 px-3 py-1.5 rounded-full normal-case">
          <AlertTriangle className="w-3.5 h-3.5" /> 支援記録 未作成
        </Label>
      );
    }
    if (item.daily_log_status === 'draft') {
      return (
        <Label variant="badge" className="flex items-center gap-1.5 text-amber-600 bg-amber-50/50 border border-amber-100 px-3 py-1.5 rounded-full normal-case">
          <FileEdit className="w-3.5 h-3.5" /> 支援記録 下書き
        </Label>
      );
    }
    return (
      <Label variant="badge" className="flex items-center gap-1.5 text-emerald-700 bg-emerald-50 border border-emerald-200 px-3 py-1.5 rounded-full normal-case">
        <CheckCircle className="w-3.5 h-3.5" /> 支援記録 完了
      </Label>
    );
  };

  const getAttendanceStatusBadge = (item: TodayUserItem) => {
    if (item.status === 'CHECKED_IN') {
      return (
        <Label variant="badge" className="bg-sky-100 text-sky-700 border border-sky-200 px-2 py-0.5 rounded-md">
          利用中 (来所)
        </Label>
      );
    }
    return (
      <Label variant="badge" className="bg-slate-100 text-slate-500 border border-slate-200 px-2 py-0.5 rounded-md">
        退所済み
      </Label>
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
      navigate(`/users/${item.user_id}/attendance?${params.toString()}`);
    } else {
      navigate(`/users/${item.user_id}/attendance`);
    }
  };

  return (
    <div className="px-4 pb-8 md:px-8 md:pb-12 animate-in fade-in duration-500 max-w-5xl mx-auto">
      <div className="sticky top-0 z-10 bg-white/90 backdrop-blur-md pt-6 pb-4 md:pt-8 md:pb-4 mb-6 border-b border-slate-200">
        <Heading variant="h1" className="flex items-center gap-3">
          <Users className="text-indigo-600 w-8 h-8 md:w-10 md:h-10" />
          本日の利用状況
        </Heading>
        <Text variant="small" className="mt-2">
          本日来所している利用者の打刻実績と、支援記録の登録状況です。未処理の記録から優先して表示されます。
        </Text>
      </div>

      {/* 件数サマリー */}
      {!loading && !error && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8 animate-in fade-in slide-in-from-top-4 duration-300">
          {/* 本日来所 */}
          <div
            onClick={() => setSelectedFilter('all')}
            className={`border rounded-2xl p-4 shadow-sm flex items-center gap-4 cursor-pointer transition-all duration-300 select-none ${
              selectedFilter === 'all'
                ? 'bg-indigo-50 border-indigo-200 ring-2 ring-indigo-500 ring-offset-1 shadow-md scale-[1.02]'
                : 'bg-white border-slate-100 hover:border-slate-200 hover:shadow-md hover:scale-[1.01]'
            }`}
          >
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 transition-colors duration-300 ${
              selectedFilter === 'all' ? 'bg-indigo-600 text-white' : 'bg-indigo-50 text-indigo-600'
            }`}>
              <Users className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs font-black text-slate-400 uppercase tracking-wider">本日来所</p>
              <p className="text-2xl font-black text-slate-800 mt-0.5">{stats.total} <span className="text-sm font-bold text-slate-500">名</span></p>
            </div>
          </div>

          {/* 未作成 */}
          <div
            onClick={() => setSelectedFilter(selectedFilter === 'missing' ? 'all' : 'missing')}
            className={`border rounded-2xl p-4 shadow-sm flex items-center gap-4 cursor-pointer transition-all duration-300 select-none ${
              selectedFilter === 'missing'
                ? 'bg-amber-50 border-amber-200 ring-2 ring-amber-500 ring-offset-1 shadow-md scale-[1.02]'
                : 'bg-white border-slate-100 hover:border-slate-200 hover:shadow-md hover:scale-[1.01]'
            }`}
          >
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 transition-colors duration-300 ${
              selectedFilter === 'missing' ? 'bg-amber-600 text-white' : 'bg-amber-50/80 text-amber-600'
            }`}>
              <AlertTriangle className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs font-black text-slate-400 uppercase tracking-wider">支援記録 未作成</p>
              <p className="text-2xl font-black text-amber-600 mt-0.5">{stats.missing} <span className="text-sm font-bold text-slate-400">件</span></p>
            </div>
          </div>

          {/* 下書き */}
          <div
            onClick={() => setSelectedFilter(selectedFilter === 'draft' ? 'all' : 'draft')}
            className={`border rounded-2xl p-4 shadow-sm flex items-center gap-4 cursor-pointer transition-all duration-300 select-none ${
              selectedFilter === 'draft'
                ? 'bg-blue-50 border-blue-200 ring-2 ring-blue-500 ring-offset-1 shadow-md scale-[1.02]'
                : 'bg-white border-slate-100 hover:border-slate-200 hover:shadow-md hover:scale-[1.01]'
            }`}
          >
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 transition-colors duration-300 ${
              selectedFilter === 'draft' ? 'bg-blue-600 text-white' : 'bg-blue-50 text-blue-600'
            }`}>
              <FileEdit className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs font-black text-slate-400 uppercase tracking-wider">支援記録 下書き</p>
              <p className="text-2xl font-black text-blue-600 mt-0.5">{stats.draft} <span className="text-sm font-bold text-slate-400">件</span></p>
            </div>
          </div>

          {/* 完了 */}
          <div
            onClick={() => setSelectedFilter(selectedFilter === 'completed' ? 'all' : 'completed')}
            className={`border rounded-2xl p-4 shadow-sm flex items-center gap-4 cursor-pointer transition-all duration-300 select-none ${
              selectedFilter === 'completed'
                ? 'bg-emerald-50 border-emerald-200 ring-2 ring-emerald-500 ring-offset-1 shadow-md scale-[1.02]'
                : 'bg-white border-slate-100 hover:border-slate-200 hover:shadow-md hover:scale-[1.01]'
            }`}
          >
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 transition-colors duration-300 ${
              selectedFilter === 'completed' ? 'bg-emerald-600 text-white' : 'bg-emerald-50 text-emerald-600'
            }`}>
              <CheckCircle className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs font-black text-slate-400 uppercase tracking-wider">支援記録 完了</p>
              <p className="text-2xl font-black text-emerald-600 mt-0.5">{stats.completed} <span className="text-sm font-bold text-slate-400">件</span></p>
            </div>
          </div>
        </div>
      )}

      {/* フィルター適用中ステータス表示 */}
      {!loading && !error && selectedFilter !== 'all' && (
        <div className="mb-4 flex items-center justify-between bg-slate-100/80 px-4 py-2.5 rounded-xl border border-slate-200 animate-in fade-in slide-in-from-top-2 duration-200">
          <p className="text-xs font-bold text-slate-600">
            フィルター適用中: <span className="text-slate-800 font-black">
              {selectedFilter === 'missing' && '支援記録 未作成'}
              {selectedFilter === 'draft' && '支援記録 下書き'}
              {selectedFilter === 'completed' && '支援記録 完了'}
            </span> のみ表示中 ({filteredAndSortedItems.length}名 / 全{items.length}名中)
          </p>
          <button
            onClick={() => setSelectedFilter('all')}
            className="text-xs font-black text-indigo-600 hover:text-indigo-700 hover:underline flex items-center gap-1"
          >
            フィルターをクリア
          </button>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center p-12">
          <div className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"></div>
        </div>
      ) : error ? (
        <div className="bg-rose-50 text-rose-600 p-4 rounded-xl font-bold">{error}</div>
      ) : filteredAndSortedItems.length === 0 ? (
        <div className="p-12 text-center text-slate-500 font-bold bg-slate-50 rounded-2xl border border-slate-200 animate-in fade-in duration-200">
          {selectedFilter === 'all' 
            ? '本日チェックインした利用者はいません。' 
            : '該当するステータスの利用者はいません。'}
          {selectedFilter !== 'all' && (
            <button
              onClick={() => setSelectedFilter('all')}
              className="block mx-auto mt-3 text-sm font-black text-indigo-600 hover:underline"
            >
              すべての利用者を表示する
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {filteredAndSortedItems.map((item) => {
            return (
              <div
                key={item.user_id}
                className={`bg-white border p-5 rounded-2xl shadow-sm transition-all flex flex-col md:flex-row md:items-center justify-between gap-4 border-slate-200 hover:border-slate-300 hover:shadow-md`}
              >
                {/* 利用者プロフィール ＆ 打刻時間 */}
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2 flex-wrap">
                    <Heading variant="h3">{item.user_name}</Heading>
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
                    {item.daily_log_status === 'completed' && '支援記録を確認'}
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
