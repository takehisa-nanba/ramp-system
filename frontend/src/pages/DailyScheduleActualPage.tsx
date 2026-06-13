import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { DatePicker, Table } from 'antd';
import dayjs, { Dayjs } from 'dayjs';
import { 
  Users, 
  Clock, 
  CheckCircle, 
  FileEdit, 
  AlertTriangle, 
  ArrowRight,
  Calendar
} from 'lucide-react';
import { fetchDailyScheduleActuals, type DailyScheduleActualItem } from '../services/userService';
import { Heading, Text, Label } from '../components/common/Typography';

export const DailyScheduleActualPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  
  const [targetDate, setTargetDate] = useState<Dayjs>(dayjs());
  const [items, setItems] = useState<DailyScheduleActualItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // フィルタ状態: URLから初期値取得、all / missing / draft / completed / scheduled / cancelled 等
  const filterParam = searchParams.get('filter');
  const selectedFilter = filterParam || 'all';

  const setSelectedFilter = (newFilter: string) => {
    const newParams = new URLSearchParams(searchParams);
    if (newFilter === 'all') {
      newParams.delete('filter');
    } else {
      newParams.set('filter', newFilter);
    }
    setSearchParams(newParams);
  };

  const loadData = async (date: Dayjs) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchDailyScheduleActuals(date.format('YYYY-MM-DD'));
      setItems(res.items);
    } catch (err) {
      console.error(err);
      setError('日別予定・実績の取得に失敗しました。');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData(targetDate);
  }, [targetDate]);

  // KPI計算
  const stats = useMemo(() => {
    return {
      scheduled: items.filter(item => item.is_scheduled).length,
      arrived: items.filter(item => !!item.check_in_at).length,
      missing: items.filter(item => item.daily_log_status === 'missing' && !!item.check_in_at).length,
      draft: items.filter(item => item.daily_log_status === 'draft').length,
      completed: items.filter(item => item.daily_log_status === 'completed').length,
    };
  }, [items]);

  // フィルタとソート
  const filteredAndSortedItems = useMemo(() => {
    let result = [...items];
    if (selectedFilter !== 'all') {
      result = result.filter(item => {
        if (selectedFilter === 'missing') return item.daily_log_status === 'missing' && !!item.check_in_at;
        if (selectedFilter === 'draft') return item.daily_log_status === 'draft';
        if (selectedFilter === 'completed') return item.daily_log_status === 'completed';
        if (selectedFilter === 'arrived') return !!item.check_in_at;
        if (selectedFilter === 'scheduled') return item.is_scheduled;
        return true;
      });
    }

    // ソート順: 未作成 > 下書き > 来所中 > それ以外
    const getSortWeight = (item: DailyScheduleActualItem) => {
      if (item.daily_log_status === 'missing' && !!item.check_in_at) return 1;
      if (item.daily_log_status === 'draft') return 2;
      if (!!item.check_in_at && !item.check_out_at) return 3; // 来所中
      return 4;
    };

    return result.sort((a, b) => getSortWeight(a) - getSortWeight(b));
  }, [items, selectedFilter]);

  const formatTime = (isoString: string | null) => {
    if (!isoString) return '—';
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '—';
    }
  };

  const getLogStatusBadge = (item: DailyScheduleActualItem) => {
    if (!item.check_in_at) {
      return (
        <Label variant="badge" className="bg-slate-100 text-slate-500 border border-slate-200 px-2 py-0.5 rounded-md">
          未来所
        </Label>
      );
    }
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

  const getAttendanceStatusBadge = (item: DailyScheduleActualItem) => {
    if (item.check_in_at && !item.check_out_at) {
      return (
        <Label variant="badge" className="bg-sky-100 text-sky-700 border border-sky-200 px-2 py-0.5 rounded-md">
          利用中 (来所)
        </Label>
      );
    }
    if (item.check_in_at && item.check_out_at) {
      return (
        <Label variant="badge" className="bg-slate-100 text-slate-500 border border-slate-200 px-2 py-0.5 rounded-md">
          退所済み
        </Label>
      );
    }
    if (item.effective_status === 'CANCELLED' || item.schedule_status === 'CANCELLED') {
      return (
        <Label variant="badge" className="bg-rose-50 text-rose-600 border border-rose-200 px-2 py-0.5 rounded-md">
          欠席/キャンセル
        </Label>
      );
    }
    if (item.is_scheduled && !item.check_in_at) {
      return (
        <Label variant="badge" className="bg-orange-50 text-orange-600 border border-orange-200 px-2 py-0.5 rounded-md">
          未来所
        </Label>
      );
    }
    return (
      <Label variant="badge" className="bg-gray-100 text-gray-500 border border-gray-200 px-2 py-0.5 rounded-md">
        予定なし
      </Label>
    );
  };

  const handleAction = (item: DailyScheduleActualItem) => {
    const isTodayOrPast = targetDate.isBefore(dayjs().add(1, 'day'), 'day');
    
    if (!item.check_in_at && !isTodayOrPast) {
      // 未来日等で打刻がない場合は、スケジュールの実績詳細画面へ
      navigate(`/users/${item.user_id}/schedule-actuals`);
      return;
    }

    if (item.daily_log_status === 'missing' || item.daily_log_status === 'draft') {
      const params = new URLSearchParams();
      params.append('date', targetDate.format('YYYY-MM-DD'));
      if (item.attendance_record_id) params.append('attendance_record_id', item.attendance_record_id.toString());
      if (item.check_in_at) params.append('check_in_at', item.check_in_at);
      if (item.check_out_at) params.append('check_out_at', item.check_out_at);
      navigate(`/users/${item.user_id}/attendance?${params.toString()}`);
    } else {
      navigate(`/users/${item.user_id}/attendance`);
    }
  };

  // PC向けテーブル用カラム定義
  const columns = [
    {
      title: '利用者名',
      dataIndex: 'user_name',
      key: 'user_name',
      render: (text: string) => <Text className="font-medium text-slate-800">{text}</Text>
    },
    {
      title: '状態',
      key: 'status',
      render: (_: any, record: DailyScheduleActualItem) => (
        <div className="flex gap-2">
          {getAttendanceStatusBadge(record)}
          {getLogStatusBadge(record)}
        </div>
      )
    },
    {
      title: '予定時間',
      key: 'schedule',
      render: (_: any, record: DailyScheduleActualItem) => {
        if (!record.is_scheduled) return <Text className="text-gray-400">予定なし</Text>;
        const start = record.scheduled_start_time ? record.scheduled_start_time.slice(0, 5) : '';
        const end = record.scheduled_end_time ? record.scheduled_end_time.slice(0, 5) : '';
        return <Text>{`${start} - ${end}`}</Text>;
      }
    },
    {
      title: '実績時間',
      key: 'actual',
      render: (_: any, record: DailyScheduleActualItem) => {
        if (!record.check_in_at) return <Text className="text-gray-400">未打刻</Text>;
        const start = dayjs(record.check_in_at).format('HH:mm');
        const end = record.check_out_at ? dayjs(record.check_out_at).format('HH:mm') : '—';
        return <Text className="font-bold text-slate-700">{`${start} - ${end}`}</Text>;
      }
    },
    {
      title: 'アクション',
      key: 'action',
      render: (_: any, record: DailyScheduleActualItem) => (
        <button
          onClick={(e) => { e.stopPropagation(); handleAction(record); }}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-bold text-xs transition-all ${
            record.daily_log_status === 'missing' && record.check_in_at
              ? 'bg-amber-600 text-white hover:bg-amber-700 shadow-sm'
              : record.daily_log_status === 'draft'
              ? 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-sm'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200 border border-slate-200'
          }`}
        >
          {record.daily_log_status === 'missing' && record.check_in_at ? '記録する' : 
           record.daily_log_status === 'draft' ? '続きから記録' : 
           record.check_in_at ? '支援記録' : '予定詳細'}
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      )
    }
  ];

  return (
    <div className="px-4 pb-8 md:px-8 md:pb-12 animate-in fade-in duration-500 max-w-6xl mx-auto">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-white/90 backdrop-blur-md pt-6 pb-4 md:pt-8 md:pb-4 mb-6 border-b border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <Heading variant="h1" className="flex items-center gap-3">
            <Calendar className="text-indigo-600 w-8 h-8 md:w-10 md:h-10" />
            日別予定・実績
          </Heading>
          <Text variant="small" className="mt-2">
            指定した日付の利用予定、来所状況、および支援記録の登録ステータスを一覧表示します。
          </Text>
        </div>
        <div className="shrink-0 flex items-center bg-slate-50 p-2 rounded-xl border border-slate-200">
          <DatePicker 
            value={targetDate} 
            onChange={(d) => d && setTargetDate(d)} 
            allowClear={false} 
            className="w-40 border-none bg-transparent font-bold text-slate-700"
            size="large"
          />
        </div>
      </div>

      {/* KPIサマリーカード */}
      {!loading && !error && (
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 md:gap-4 mb-8 animate-in fade-in slide-in-from-top-4 duration-300">
          <div
            onClick={() => setSelectedFilter('scheduled')}
            className={`border rounded-2xl p-3 md:p-4 shadow-sm flex items-center gap-3 cursor-pointer transition-all duration-300 select-none ${
              selectedFilter === 'scheduled'
                ? 'bg-slate-100 border-slate-300 ring-2 ring-slate-500 ring-offset-1 shadow-md scale-[1.02]'
                : 'bg-white border-slate-100 hover:border-slate-200 hover:shadow-md hover:scale-[1.01]'
            }`}
          >
            <div className={`w-10 h-10 md:w-12 md:h-12 rounded-xl flex items-center justify-center shrink-0 transition-colors duration-300 ${
              selectedFilter === 'scheduled' ? 'bg-slate-600 text-white' : 'bg-slate-50 text-slate-600'
            }`}>
              <Calendar className="w-5 h-5 md:w-6 md:h-6" />
            </div>
            <div>
              <p className="text-[10px] md:text-xs font-black text-slate-400 uppercase tracking-wider">予定あり</p>
              <p className="text-xl md:text-2xl font-black text-slate-800 mt-0.5">{stats.scheduled} <span className="text-xs md:text-sm font-bold text-slate-500">名</span></p>
            </div>
          </div>

          <div
            onClick={() => setSelectedFilter('arrived')}
            className={`border rounded-2xl p-3 md:p-4 shadow-sm flex items-center gap-3 cursor-pointer transition-all duration-300 select-none ${
              selectedFilter === 'arrived'
                ? 'bg-indigo-50 border-indigo-200 ring-2 ring-indigo-500 ring-offset-1 shadow-md scale-[1.02]'
                : 'bg-white border-slate-100 hover:border-slate-200 hover:shadow-md hover:scale-[1.01]'
            }`}
          >
            <div className={`w-10 h-10 md:w-12 md:h-12 rounded-xl flex items-center justify-center shrink-0 transition-colors duration-300 ${
              selectedFilter === 'arrived' ? 'bg-indigo-600 text-white' : 'bg-indigo-50 text-indigo-600'
            }`}>
              <Users className="w-5 h-5 md:w-6 md:h-6" />
            </div>
            <div>
              <p className="text-[10px] md:text-xs font-black text-slate-400 uppercase tracking-wider">来所済</p>
              <p className="text-xl md:text-2xl font-black text-indigo-600 mt-0.5">{stats.arrived} <span className="text-xs md:text-sm font-bold text-indigo-400">名</span></p>
            </div>
          </div>

          <div
            onClick={() => setSelectedFilter(selectedFilter === 'missing' ? 'all' : 'missing')}
            className={`border rounded-2xl p-3 md:p-4 shadow-sm flex items-center gap-3 cursor-pointer transition-all duration-300 select-none ${
              selectedFilter === 'missing'
                ? 'bg-amber-50 border-amber-200 ring-2 ring-amber-500 ring-offset-1 shadow-md scale-[1.02]'
                : 'bg-white border-slate-100 hover:border-slate-200 hover:shadow-md hover:scale-[1.01]'
            }`}
          >
            <div className={`w-10 h-10 md:w-12 md:h-12 rounded-xl flex items-center justify-center shrink-0 transition-colors duration-300 ${
              selectedFilter === 'missing' ? 'bg-amber-600 text-white' : 'bg-amber-50/80 text-amber-600'
            }`}>
              <AlertTriangle className="w-5 h-5 md:w-6 md:h-6" />
            </div>
            <div>
              <p className="text-[10px] md:text-xs font-black text-slate-400 uppercase tracking-wider">記録未作成</p>
              <p className="text-xl md:text-2xl font-black text-amber-600 mt-0.5">{stats.missing} <span className="text-xs md:text-sm font-bold text-amber-400">件</span></p>
            </div>
          </div>

          <div
            onClick={() => setSelectedFilter(selectedFilter === 'draft' ? 'all' : 'draft')}
            className={`border rounded-2xl p-3 md:p-4 shadow-sm flex items-center gap-3 cursor-pointer transition-all duration-300 select-none ${
              selectedFilter === 'draft'
                ? 'bg-blue-50 border-blue-200 ring-2 ring-blue-500 ring-offset-1 shadow-md scale-[1.02]'
                : 'bg-white border-slate-100 hover:border-slate-200 hover:shadow-md hover:scale-[1.01]'
            }`}
          >
            <div className={`w-10 h-10 md:w-12 md:h-12 rounded-xl flex items-center justify-center shrink-0 transition-colors duration-300 ${
              selectedFilter === 'draft' ? 'bg-blue-600 text-white' : 'bg-blue-50 text-blue-600'
            }`}>
              <FileEdit className="w-5 h-5 md:w-6 md:h-6" />
            </div>
            <div>
              <p className="text-[10px] md:text-xs font-black text-slate-400 uppercase tracking-wider">記録下書き</p>
              <p className="text-xl md:text-2xl font-black text-blue-600 mt-0.5">{stats.draft} <span className="text-xs md:text-sm font-bold text-blue-400">件</span></p>
            </div>
          </div>

          <div
            onClick={() => setSelectedFilter(selectedFilter === 'completed' ? 'all' : 'completed')}
            className={`border rounded-2xl p-3 md:p-4 shadow-sm flex items-center gap-3 cursor-pointer transition-all duration-300 select-none col-span-2 lg:col-span-1 ${
              selectedFilter === 'completed'
                ? 'bg-emerald-50 border-emerald-200 ring-2 ring-emerald-500 ring-offset-1 shadow-md scale-[1.02]'
                : 'bg-white border-slate-100 hover:border-slate-200 hover:shadow-md hover:scale-[1.01]'
            }`}
          >
            <div className={`w-10 h-10 md:w-12 md:h-12 rounded-xl flex items-center justify-center shrink-0 transition-colors duration-300 ${
              selectedFilter === 'completed' ? 'bg-emerald-600 text-white' : 'bg-emerald-50 text-emerald-600'
            }`}>
              <CheckCircle className="w-5 h-5 md:w-6 md:h-6" />
            </div>
            <div>
              <p className="text-[10px] md:text-xs font-black text-slate-400 uppercase tracking-wider">記録完了</p>
              <p className="text-xl md:text-2xl font-black text-emerald-600 mt-0.5">{stats.completed} <span className="text-xs md:text-sm font-bold text-emerald-400">件</span></p>
            </div>
          </div>
        </div>
      )}

      {/* フィルター適用中ステータス表示 */}
      {!loading && !error && selectedFilter !== 'all' && (
        <div className="mb-4 flex items-center justify-between bg-slate-100/80 px-4 py-2.5 rounded-xl border border-slate-200 animate-in fade-in slide-in-from-top-2 duration-200">
          <p className="text-xs font-bold text-slate-600">
            フィルター適用中: <span className="text-slate-800 font-black">
              {selectedFilter === 'scheduled' && '予定あり'}
              {selectedFilter === 'arrived' && '来所済'}
              {selectedFilter === 'missing' && '支援記録 未作成'}
              {selectedFilter === 'draft' && '支援記録 下書き'}
              {selectedFilter === 'completed' && '支援記録 完了'}
            </span> のみ表示 ({filteredAndSortedItems.length}名)
          </p>
          <button
            onClick={() => setSelectedFilter('all')}
            className="text-xs font-black text-indigo-600 hover:text-indigo-700 hover:underline flex items-center gap-1"
          >
            フィルターをクリア
          </button>
        </div>
      )}

      {/* Main Content */}
      {loading ? (
        <div className="flex justify-center p-12">
          <div className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"></div>
        </div>
      ) : error ? (
        <div className="bg-rose-50 text-rose-600 p-4 rounded-xl font-bold">{error}</div>
      ) : filteredAndSortedItems.length === 0 ? (
        <div className="p-12 text-center text-slate-500 font-bold bg-slate-50 rounded-2xl border border-slate-200 animate-in fade-in duration-200">
          該当する利用者は見つかりませんでした。
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
        <div className="animate-in fade-in duration-300">
          {/* テーブル表示 (PC用: md以上で表示) */}
          <div className="hidden md:block bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
            <Table 
              columns={columns} 
              dataSource={filteredAndSortedItems} 
              rowKey="user_id" 
              pagination={false}
              rowClassName="hover:bg-slate-50 transition-colors cursor-pointer"
              onRow={(record) => ({
                onClick: () => navigate(`/users/${record.user_id}/schedule-actuals`),
              })}
            />
          </div>

          {/* カード表示 (スマホ・タブレット用: md未満で表示) */}
          <div className="block md:hidden space-y-4">
            {filteredAndSortedItems.map((item) => (
                <div
                  key={item.user_id}
                  onClick={() => navigate(`/users/${item.user_id}/schedule-actuals`)}
                  className="bg-white border p-4 rounded-2xl shadow-sm transition-all flex flex-col gap-3 border-slate-200 active:bg-slate-50"
                >
                  <div className="flex justify-between items-start">
                    <Heading variant="h3" className="!mb-0 text-slate-800">{item.user_name}</Heading>
                    <div className="flex flex-col items-end gap-1.5">
                      {getAttendanceStatusBadge(item)}
                      {getLogStatusBadge(item)}
                    </div>
                  </div>
                  
                  <div className="flex flex-col gap-1.5 text-sm font-medium text-slate-500 mt-1 bg-slate-50 p-3 rounded-xl border border-slate-100">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5 text-slate-400 text-xs">
                        <Calendar className="w-4 h-4" /> 予定
                      </div>
                      <span className="text-slate-700">
                        {item.is_scheduled ? `${item.scheduled_start_time?.slice(0,5) || ''} - ${item.scheduled_end_time?.slice(0,5) || ''}` : 'なし'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5 text-slate-400 text-xs">
                        <Clock className="w-4 h-4" /> 実績
                      </div>
                      <span className="font-bold text-slate-700">
                        {item.check_in_at ? `${formatTime(item.check_in_at)} - ${item.check_out_at ? formatTime(item.check_out_at) : '—'}` : '未打刻'}
                      </span>
                    </div>
                  </div>

                  <div className="flex justify-end mt-1">
                    <button
                      onClick={(e) => { e.stopPropagation(); handleAction(item); }}
                      className={`flex items-center justify-center gap-2 w-full py-2.5 rounded-xl font-bold text-sm transition-all ${
                        item.daily_log_status === 'missing' && item.check_in_at
                          ? 'bg-amber-600 text-white shadow-sm'
                          : item.daily_log_status === 'draft'
                          ? 'bg-indigo-600 text-white shadow-sm'
                          : 'bg-slate-100 text-slate-600 border border-slate-200'
                      }`}
                    >
                      {item.daily_log_status === 'missing' && item.check_in_at ? '記録する' : 
                       item.daily_log_status === 'draft' ? '続きから記録' : 
                       item.check_in_at ? '支援記録' : '予定詳細'}
                      <ArrowRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
      )}
    </div>
  );
};
