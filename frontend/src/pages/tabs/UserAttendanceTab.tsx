import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Clock, CheckCircle, FileEdit, AlertTriangle, ArrowRight, Calendar, Link as LinkIcon, X, AlertCircle } from 'lucide-react';
import { TimeDurationInput } from '../../components/common/UXFields';
import { 
  fetchUserAttendanceRecords, 
  fetchUserDailyLogs, 
  fetchActivityTags, 
  createDailyLog, 
  type UserAttendanceItem,
  type DailyLogItem,
  type ActivityTag 
} from '../../services/userService';

const LOCATION_TYPE_JA: Record<string, string> = {
  ON_SITE: '施設内支援',
  OFF_SITE_SUPPORT: '施設外支援',
  TRANSITION_PREP: '移行準備',
  OFF_SITE_WORK: '施設外就労',
  AT_HOME: '在宅支援',
};

const statusBadge = (status: string) => {
  switch (status) {
    case 'COMPLETED':
    case 'APPROVED': 
      return <span className="flex items-center gap-1 text-xs font-bold text-emerald-700 bg-emerald-100 px-2 py-1 rounded-full"><CheckCircle className="w-3 h-3" /> 完了</span>;
    case 'DRAFT': 
      return <span className="flex items-center gap-1 text-xs font-bold text-amber-700 bg-amber-100 px-2 py-1 rounded-full"><Clock className="w-3 h-3" /> 下書き</span>;
    default: 
      return <span className="flex items-center gap-1 text-xs font-bold text-slate-600 bg-slate-100 px-2 py-1 rounded-full"><FileEdit className="w-3 h-3" /> {status}</span>;
  }
};

export const UserAttendanceTab: React.FC<{ userId: number }> = ({ userId }) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const dateParam = searchParams.get('date');

  // 実績と日報データ
  const [attendanceRecords, setAttendanceRecords] = useState<UserAttendanceItem[]>([]);
  const [dailyLogs, setDailyLogs] = useState<DailyLogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // モーダルとフォーム状態
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [attendanceInfo, setAttendanceInfo] = useState<{
    recordId: number;
    checkIn: string;
    checkOut?: string;
    date: string;
  } | null>(null);
  const [tags, setTags] = useState<ActivityTag[]>([]);
  const [selectedTagId, setSelectedTagId] = useState<string>('');
  const [logDate, setLogDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [startTime, setStartTime] = useState<string>('10:00');
  const [endTime, setEndTime] = useState<string>('11:00');
  const [notes, setNotes] = useState<string>('');
  const [durationSeconds, setDurationSeconds] = useState<number>(3600);

  // 開始時間・終了時間変更時に所要秒数を自動計算 (ガードレール)
  useEffect(() => {
    const startParts = startTime.split(':').map(Number);
    const endParts = endTime.split(':').map(Number);
    if (startParts.length === 2 && endParts.length === 2) {
      const startSecs = startParts[0] * 3600 + startParts[1] * 60;
      const endSecs = endParts[0] * 3600 + endParts[1] * 60;
      if (endSecs > startSecs) {
        setDurationSeconds(endSecs - startSecs);
      } else {
        setDurationSeconds(0);
      }
    }
  }, [startTime, endTime]);
  
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // データ読み込み
  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [attendanceRes, logsRes] = await Promise.all([
        fetchUserAttendanceRecords(userId),
        fetchUserDailyLogs(userId)
      ]);
      
      setAttendanceRecords(attendanceRes.items);
      setDailyLogs(logsRes.items);
    } catch (err) {
      console.error(err);
      setError('実績・記録データの取得に失敗しました。');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [userId]);

  // クエリパラメータに date がある場合、自動的にその日付でモーダルを開く
  useEffect(() => {
    if (dateParam) {
      setLogDate(dateParam);
      
      const recordId = searchParams.get('attendance_record_id');
      const checkInAt = searchParams.get('check_in_at');
      const checkOutAt = searchParams.get('check_out_at');
      
      if (recordId && checkInAt) {
        setAttendanceInfo({
          recordId: Number(recordId),
          date: dateParam,
          checkIn: checkInAt,
          checkOut: checkOutAt || undefined,
        });
        
        try {
          const ci = new Date(checkInAt);
          const formattedCI = ci.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' });
          setStartTime(formattedCI);
          
          if (checkOutAt) {
            const co = new Date(checkOutAt);
            const formattedCO = co.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' });
            setEndTime(formattedCO);
          } else {
            const co = new Date(ci.getTime() + 60 * 60 * 1000);
            const formattedCO = co.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' });
            setEndTime(formattedCO);
          }
        } catch (e) {
          console.error('打刻時間のパースに失敗しました', e);
        }
      }
      
      handleOpenModal();
      
      const newParams = new URLSearchParams(searchParams);
      newParams.delete('date');
      newParams.delete('attendance_record_id');
      newParams.delete('check_in_at');
      newParams.delete('check_out_at');
      setSearchParams(newParams, { replace: true });
    }
  }, [dateParam, searchParams, setSearchParams]);

  // モーダル制御
  const handleOpenModal = async () => {
    setIsModalOpen(true);
    setFormError(null);
    try {
      const allTags = await fetchActivityTags();
      const directTags = allTags.filter(t => t.is_direct_support);
      setTags(directTags);
      if (directTags.length > 0) {
        setSelectedTagId(directTags[0].id.toString());
      }
    } catch (err) {
      console.error(err);
      setFormError('支援区分の取得に失敗しました。');
    }
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setNotes('');
    setFormError(null);
    setLogDate(new Date().toISOString().split('T')[0]);
    setAttendanceInfo(null);
    setStartTime('10:00');
    setEndTime('11:00');
    setDurationSeconds(3600);
  };

  const handleAction = (item: UserAttendanceItem) => {
    // 既存の日報を検索
    const associatedLog = dailyLogs.find(log => log.log_date === item.date);

    if (associatedLog) {
      // 完了または下書きの日報がすでに存在する場合、その日報を確認・編集
      // 本来は編集画面だが、MVPでは既存の記録を表示 or 下書きならモーダルで開く
      if (item.daily_log_status === 'draft') {
        // 下書きがある場合はモーダルで開き、内容をフォームに復元する
        setLogDate(item.date);
        setAttendanceInfo({
          recordId: item.attendance_record_id,
          date: item.date,
          checkIn: item.check_in_at || '',
          checkOut: item.check_out_at || undefined,
        });

        // フォームを初期化
        setNotes(associatedLog.support_content_notes || '');
        if (associatedLog.activities && associatedLog.activities.length > 0) {
          const act = associatedLog.activities[0];
          setStartTime(act.start_time || '10:00');
          setEndTime(act.end_time || '11:00');
          setDurationSeconds(act.duration_seconds || 3600);
        }
        
        handleOpenModal();
      } else {
        // 完了済みの場合：履歴セクションにスクロールするか、ポップアップで知らせる
        const logElement = document.getElementById(`daily-log-${associatedLog.id}`);
        if (logElement) {
          logElement.scrollIntoView({ behavior: 'smooth' });
          logElement.classList.add('ring-2', 'ring-indigo-500');
          setTimeout(() => {
            logElement.classList.remove('ring-2', 'ring-indigo-500');
          }, 2000);
        } else {
          alert('下部の日報履歴より「完了」日報を確認できます。');
        }
      }
    } else {
      // 日報がないため新規作成
      setLogDate(item.date);
      setAttendanceInfo({
        recordId: item.attendance_record_id,
        date: item.date,
        checkIn: item.check_in_at || '',
        checkOut: item.check_out_at || undefined,
      });

      try {
        if (item.check_in_at) {
          const ci = new Date(item.check_in_at);
          const formattedCI = ci.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' });
          setStartTime(formattedCI);
          
          if (item.check_out_at) {
            const co = new Date(item.check_out_at);
            const formattedCO = co.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' });
            setEndTime(formattedCO);
          } else {
            const co = new Date(ci.getTime() + 60 * 60 * 1000);
            const formattedCO = co.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' });
            setEndTime(formattedCO);
          }
        }
      } catch (e) {
        console.error(e);
      }
      handleOpenModal();
    }
  };

  const handleSubmit = async (status: 'DRAFT' | 'COMPLETED') => {
    if (!selectedTagId) {
      setFormError('支援区分を選択してください。');
      return;
    }
    
    const startParts = startTime.split(':').map(Number);
    const endParts = endTime.split(':').map(Number);
    const startSecs = startParts[0] * 3600 + startParts[1] * 60;
    const endSecs = endParts[0] * 3600 + endParts[1] * 60;

    if (endSecs <= startSecs) {
      setFormError('終了時間は開始時間より後の時間に設定してください。日跨ぎの活動記録はサポートされていません。');
      return;
    }

    if (durationSeconds < 0 || durationSeconds > 86400) {
      setFormError('活動時間は0秒以上24時間（86400秒）以下で指定してください。');
      return;
    }

    try {
      setFormSubmitting(true);
      setFormError(null);

      const startTimeISO = `${logDate}T${startTime}:00+09:00`;
      const endTimeISO = `${logDate}T${endTime}:00+09:00`;

      await createDailyLog({
        tag_id: Number(selectedTagId),
        user_id: userId,
        start_time: startTimeISO,
        end_time: endTimeISO,
        duration_seconds: durationSeconds,
        notes: notes,
        log_status: status,
        attendance_record_id: attendanceInfo?.recordId || undefined
      });

      handleCloseModal();
      loadData(); // 実績と日報を再リロード
    } catch (err: any) {
      console.error(err);
      const errMsg = err?.response?.data?.msg || '日報の登録に失敗しました。';
      setFormError(errMsg);
    } finally {
      setFormSubmitting(false);
    }
  };

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
            <CheckCircle className="w-3.5 h-3.5" /> 支援記録 完了
          </span>
        );
      case 'draft':
        return (
          <span className="flex items-center gap-1 text-xs font-bold text-amber-600 bg-amber-50/50 border border-amber-100 px-2.5 py-1 rounded-full">
            <FileEdit className="w-3.5 h-3.5" /> 支援記録 下書き
          </span>
        );
      case 'missing':
      default:
        return (
          <span className="flex items-center gap-1 text-xs font-bold text-rose-700 bg-rose-50 border border-rose-200 px-2.5 py-1 rounded-full">
            <AlertTriangle className="w-3.5 h-3.5" /> 支援記録 未作成
          </span>
        );
    }
  };

  if (loading && attendanceRecords.length === 0) {
    return <div className="flex justify-center p-12"><div className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" /></div>;
  }
  if (error) {
    return <div className="bg-rose-50 text-rose-600 p-4 rounded-xl font-bold flex items-center gap-2"><AlertTriangle className="w-5 h-5" />{error}</div>;
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      
      {/* 1. 実績一覧セクション */}
      <div className="space-y-4">
        <div>
          <h2 className="text-xl font-black text-slate-800 flex items-center gap-2">
            <Calendar className="w-6 h-6 text-indigo-600" />
            利用実績と記録状況
          </h2>
          <p className="text-sm text-slate-500 mt-1 font-medium">客観的な来所・退所打刻と、それに対応する支援記録の作成状態です。実績行から直接記録を作成できます。</p>
        </div>

        {attendanceRecords.length === 0 ? (
          <div className="bg-slate-50 text-slate-500 p-8 rounded-2xl text-center font-bold border border-slate-200">
            利用実績が登録されていません。
          </div>
        ) : (
          <div className="space-y-3">
            {attendanceRecords.map(item => (
              <div key={item.date} className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm hover:shadow-md transition-shadow flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2 flex-wrap">
                    <div className="text-sm font-black text-indigo-600">{item.date}</div>
                    {getLogStatusBadge(item.daily_log_status)}
                  </div>
                  <div className="flex gap-6 text-sm font-medium text-slate-500">
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
                  {/* 予定と実績の支援区分の比較 */}
                  <div className="mt-3 flex flex-wrap gap-4 text-xs font-semibold text-slate-500 border-t border-slate-100 pt-3">
                    <div className="flex items-center gap-1.5">
                      <span className="text-slate-400 font-medium">予定支援区分:</span>
                      <span className={`px-2 py-0.5 rounded-md font-bold ${
                        item.is_scheduled 
                          ? 'bg-slate-100 text-slate-700' 
                          : 'bg-slate-50 text-slate-400'
                      }`}>
                        {item.is_scheduled 
                          ? (LOCATION_TYPE_JA[item.scheduled_location_type || ''] || item.scheduled_location_type || '施設内支援') 
                          : '予定なし'}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-slate-400 font-medium">実績支援区分:</span>
                      <span className={`px-2 py-0.5 rounded-md font-bold ${
                        item.actual_location_type 
                          ? 'bg-indigo-50 text-indigo-700' 
                          : 'bg-rose-50 text-rose-600'
                      }`}>
                        {item.actual_location_type 
                          ? (LOCATION_TYPE_JA[item.actual_location_type] || item.actual_location_type) 
                          : '実績未確定（日報未完了）'}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="shrink-0">
                  <button
                    onClick={() => handleAction(item)}
                    className={`flex items-center gap-2 px-4 py-2.5 rounded-xl font-bold text-xs transition-all ${
                      item.daily_log_status === 'missing'
                        ? 'bg-amber-600 text-white hover:bg-amber-700 shadow-sm'
                        : item.daily_log_status === 'draft'
                        ? 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-sm'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200 border border-slate-200'
                    }`}
                  >
                    {item.daily_log_status === 'missing' && 'この実績の支援記録を作成'}
                    {item.daily_log_status === 'draft' && '続きから記録する'}
                    {item.daily_log_status === 'completed' && '支援記録を確認'}
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 2. 日報履歴タイムラインセクション */}
      <div className="border-t border-slate-200 pt-8 space-y-6">
        <div>
          <h2 className="text-xl font-black text-slate-800 flex items-center gap-2">
            <LinkIcon className="w-5 h-5 text-indigo-600" />
            支援記録履歴
          </h2>
          <p className="text-sm text-slate-500 mt-1 font-medium">作成された支援記録のタイムラインです。</p>
        </div>

        {dailyLogs.length === 0 ? (
          <div className="bg-slate-50 text-slate-500 p-8 rounded-2xl text-center font-bold border border-slate-200">
            まだ支援記録が登録されていません。
          </div>
        ) : (
          <div className="space-y-4 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-200 before:to-transparent">
            {dailyLogs.map(log => (
              <div 
                key={log.id} 
                id={`daily-log-${log.id}`} 
                className="relative flex items-start gap-4 group transition-all duration-300 rounded-2xl"
              >
                <div className="flex items-center justify-center w-10 h-10 rounded-full border-4 border-white bg-indigo-100 text-indigo-600 shadow shrink-0 z-10 mt-1">
                  <Clock className="w-4 h-4" />
                </div>
                <div className="flex-1 bg-white p-5 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-all">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <div className="text-sm font-black text-indigo-600">{log.log_date}</div>
                      <div className="text-xs font-bold text-slate-400 mt-0.5">{log.location_type}</div>
                    </div>
                    {statusBadge(log.log_status)}
                  </div>
                  <p className="text-slate-700 font-medium text-sm mb-4 leading-relaxed whitespace-pre-wrap">{log.support_content_notes}</p>
                  {log.activities.length > 0 && (
                    <div className="bg-slate-50 rounded-xl p-3 mb-4">
                      <div className="flex items-start gap-2">
                        <LinkIcon className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                        <div className="w-full">
                          <div className="text-xs font-bold text-slate-400 mb-1">活動記録</div>
                          {log.activities.map(act => {
                            const showDuration = () => {
                              if (!act.duration_seconds) return '';
                              const h = Math.floor(act.duration_seconds / 3600);
                              const m = Math.floor((act.duration_seconds % 3600) / 60);
                              const s = act.duration_seconds % 60;
                              return ` (${h > 0 ? `${h}時間` : ''}${m}分${s}秒)`;
                            };
                            return (
                              <div key={act.id} className="text-sm font-bold text-slate-700 flex justify-between gap-4">
                                <span>{act.support_content}{showDuration()}</span>
                                <span className="text-slate-400 text-xs font-medium whitespace-nowrap">{act.start_time}〜{act.end_time}</span>
                              </div>
                            );
                          })}
                          <div className="text-xs font-bold text-slate-500 mt-1">
                            記録者: {log.activities[0]?.supporter_name ?? '—'}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 新規支援記録作成モーダル */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center z-[100] p-4 animate-in fade-in duration-200">
          <div className="bg-white rounded-[2rem] shadow-2xl border border-slate-200 max-w-lg w-full overflow-hidden flex flex-col max-h-[90vh] animate-in zoom-in-95 duration-200">
            {/* ヘッダー */}
            <div className="p-6 border-b border-slate-100 flex items-center justify-between">
              <h3 className="text-xl font-black text-slate-800">新規支援記録の作成</h3>
              <button 
                onClick={handleCloseModal}
                className="p-2 hover:bg-slate-100 rounded-xl transition-colors text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* コンテンツ */}
            <div className="p-6 overflow-y-auto space-y-4 flex-1">
              {/* 対象日の利用実績カード */}
              {attendanceInfo && (
                <div className="bg-indigo-50 border border-indigo-100 rounded-2xl p-4 flex flex-col gap-1.5 shadow-inner animate-in slide-in-from-top-2 duration-300">
                  <h4 className="text-xs font-black text-indigo-600 flex items-center gap-1.5 uppercase tracking-wider">
                    <Clock className="w-3.5 h-3.5" /> 対象日の利用実績と紐付け
                  </h4>
                  <div className="text-sm font-black text-slate-800">
                    実績日: {attendanceInfo.date}
                  </div>
                  <div className="flex gap-4 text-xs font-bold text-slate-500">
                    <div>来所: <span className="text-indigo-600 font-black">{new Date(attendanceInfo.checkIn).toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' })}</span></div>
                    {attendanceInfo.checkOut && (
                      <div>退所: <span className="text-indigo-600 font-black">{new Date(attendanceInfo.checkOut).toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' })}</span></div>
                    )}
                  </div>
                </div>
              )}

              {formError && (
                <div className="bg-rose-50 text-rose-600 p-4 rounded-xl font-bold flex items-start gap-2 text-sm border border-rose-200">
                  <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
                  <div>{formError}</div>
                </div>
              )}

              {/* 支援区分 */}
              <div>
                <label className="block text-xs font-bold text-slate-400 mb-1">支援区分 (必須)</label>
                <select
                  value={selectedTagId}
                  onChange={(e) => setSelectedTagId(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-sm font-bold text-slate-700 focus:outline-none focus:border-indigo-500 transition-colors"
                >
                  {tags.map(t => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
              </div>

              {/* 日付選択 */}
              <div>
                <label className="block text-xs font-bold text-slate-400 mb-1">支援日付</label>
                <input
                  type="date"
                  value={logDate}
                  onChange={(e) => setLogDate(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-sm font-bold text-slate-700 focus:outline-none focus:border-indigo-500 transition-colors"
                />
              </div>

              {/* 時間帯 */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-400 mb-1">開始時間</label>
                  <input
                    type="time"
                    value={startTime}
                    onChange={(e) => setStartTime(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-sm font-bold text-slate-700 focus:outline-none focus:border-indigo-500 transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-400 mb-1">終了時間</label>
                  <input
                    type="time"
                    value={endTime}
                    onChange={(e) => setEndTime(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-sm font-bold text-slate-700 focus:outline-none focus:border-indigo-500 transition-colors"
                  />
                </div>
              </div>

              {/* 活動所要時間 */}
              <TimeDurationInput
                label="活動所要時間"
                totalSeconds={durationSeconds}
                onChange={(secs) => setDurationSeconds(secs)}
                className="mt-2"
              />

              {/* 支援記録 */}
              <div>
                <label className="block text-xs font-bold text-slate-400 mb-1">支援記録 (自由記述)</label>
                <textarea
                  placeholder="支援の具体的な内容や様子を入力してください"
                  rows={4}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-sm font-bold text-slate-700 focus:outline-none focus:border-indigo-500 transition-colors resize-none"
                />
              </div>
            </div>

            {/* フッター */}
            <div className="p-6 border-t border-slate-100 bg-slate-50/50 flex gap-3 justify-end">
              <button
                disabled={formSubmitting}
                onClick={() => handleSubmit('DRAFT')}
                className="px-5 py-2.5 bg-slate-200 hover:bg-slate-300 text-slate-700 rounded-xl font-bold text-sm transition-colors disabled:opacity-50"
              >
                下書き保存
              </button>
              <button
                disabled={formSubmitting}
                onClick={() => handleSubmit('COMPLETED')}
                className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold text-sm transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {formSubmitting && <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />}
                記録を完了する
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
