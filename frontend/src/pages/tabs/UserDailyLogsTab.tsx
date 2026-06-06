import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Clock, CheckCircle, FileEdit, Plus, Link as LinkIcon, AlertCircle, X } from 'lucide-react';
import { 
  fetchUserDailyLogs, 
  fetchActivityTags, 
  createDailyLog, 
  type DailyLogItem, 
  type ActivityTag 
} from '../../services/userService';

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

export const UserDailyLogsTab: React.FC<{ userId: number }> = ({ userId }) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const dateParam = searchParams.get('date');

  const [items, setItems] = useState<DailyLogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // モーダルとフォーム状態
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [tags, setTags] = useState<ActivityTag[]>([]);
  const [selectedTagId, setSelectedTagId] = useState<string>('');
  const [logDate, setLogDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [startTime, setStartTime] = useState<string>('10:00');
  const [endTime, setEndTime] = useState<string>('11:00');
  const [notes, setNotes] = useState<string>('');
  
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const loadDailyLogs = () => {
    setLoading(true);
    setError(null);
    fetchUserDailyLogs(userId)
      .then(res => setItems(res.items))
      .catch(() => setError('日報の取得に失敗しました。'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadDailyLogs();
  }, [userId]);

  // クエリパラメータに date がある場合、自動的にその日付でモーダルを開く
  useEffect(() => {
    if (dateParam) {
      setLogDate(dateParam);
      handleOpenModal();
      
      const newParams = new URLSearchParams(searchParams);
      newParams.delete('date');
      setSearchParams(newParams, { replace: true });
    }
  }, [dateParam, searchParams, setSearchParams]);

  // モーダルを開いたときにタグ一覧を取得
  const handleOpenModal = async () => {
    setIsModalOpen(true);
    setFormError(null);
    try {
      const allTags = await fetchActivityTags();
      // 直接支援タグのみに絞り込む
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
  };

  const handleSubmit = async (status: 'DRAFT' | 'COMPLETED') => {
    if (!selectedTagId) {
      setFormError('支援区分を選択してください。');
      return;
    }
    
    // 時間差分の計算
    const startParts = startTime.split(':').map(Number);
    const endParts = endTime.split(':').map(Number);
    const duration = (endParts[0] * 60 + endParts[1]) - (startParts[0] * 60 + startParts[1]);

    if (duration <= 0) {
      setFormError('終了時間は開始時間より後の時間に設定してください。');
      return;
    }

    try {
      setFormSubmitting(true);
      setFormError(null);

      // ISO 日時文字列の構築 (タイムゾーン+09:00を明示)
      const startTimeISO = `${logDate}T${startTime}:00+09:00`;
      const endTimeISO = `${logDate}T${endTime}:00+09:00`;

      await createDailyLog({
        tag_id: Number(selectedTagId),
        user_id: userId,
        start_time: startTimeISO,
        end_time: endTimeISO,
        duration_minutes: duration,
        notes: notes,
        log_status: status
      });

      handleCloseModal();
      loadDailyLogs(); // 一覧リロード
    } catch (err: any) {
      console.error(err);
      const errMsg = err?.response?.data?.msg || '日報の登録に失敗しました。';
      setFormError(errMsg);
    } finally {
      setFormSubmitting(false);
    }
  };

  if (loading && items.length === 0) return <div className="flex justify-center p-12"><div className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" /></div>;
  if (error) return <div className="bg-rose-50 text-rose-600 p-4 rounded-xl font-bold flex items-center gap-2"><AlertCircle className="w-5 h-5" />{error}</div>;

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-black text-slate-800">日報履歴</h2>
        <button 
          onClick={handleOpenModal}
          className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-xl font-bold hover:bg-indigo-700 transition-colors shadow-sm"
        >
          <Plus className="w-5 h-5" /> 新規日報作成
        </button>
      </div>

      {items.length === 0 ? (
        <div className="bg-slate-50 text-slate-500 p-8 rounded-2xl text-center font-bold border border-slate-200">
          まだ日報が記録されていません。
        </div>
      ) : (
        <div className="space-y-4 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-200 before:to-transparent">
          {items.map(log => (
            <div key={log.id} className="relative flex items-start gap-4 group">
              <div className="flex items-center justify-center w-10 h-10 rounded-full border-4 border-white bg-indigo-100 text-indigo-600 shadow shrink-0 z-10 mt-1">
                <Clock className="w-4 h-4" />
              </div>
              <div className="flex-1 bg-white p-5 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow">
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
                        {log.activities.map(act => (
                          <div key={act.id} className="text-sm font-bold text-slate-700 flex justify-between gap-4">
                            <span>{act.support_content}</span>
                            <span className="text-slate-400 text-xs font-medium whitespace-nowrap">{act.start_time}〜{act.end_time}</span>
                          </div>
                        ))}
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

      {/* 新規日報作成モーダル */}
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
