import React, { useEffect, useState } from 'react';
import type { MyPageTodayResponse } from '../services/userMyPageApi';
import { getMyPageToday, postMyPageAttendance, postMyPageDailyLog } from '../services/userMyPageApi';

const UserMyPage: React.FC = () => {
  const [data, setData] = useState<MyPageTodayResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  
  // Form State
  const [physicalScore, setPhysicalScore] = useState<number>(3);
  const [sleepScore, setSleepScore] = useState<number>(3);
  const [evaluation, setEvaluation] = useState<string>('');
  const [savingLog, setSavingLog] = useState(false);
  const [hasSavedLog, setHasSavedLog] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const res = await getMyPageToday();
      setData(res);
      setPhysicalScore(res.daily_log.physical_condition_score || 3);
      setSleepScore(res.daily_log.sleep_quality_score || 3);
      setEvaluation(res.daily_log.user_self_evaluation || '');
      setHasSavedLog(res.daily_log.user_self_evaluation !== null);
    } catch (err: unknown) {
      setError('データの取得に失敗しました。');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleAttendance = async (type: 'CHECK_IN' | 'CHECK_OUT') => {
    try {
      await postMyPageAttendance(type);
      setSuccessMsg(type === 'CHECK_IN' ? '通所を記録しました！' : '退所を記録しました！お疲れ様でした。');
      await fetchData(); // Refresh data
      
      // hide success msg after 3 seconds
      setTimeout(() => setSuccessMsg(null), 3000);
    } catch (err) {
      setError('打刻に失敗しました。');
      setTimeout(() => setError(null), 3000);
    }
  };

  const handleSaveDailyLog = async () => {
    try {
      setSavingLog(true);
      await postMyPageDailyLog({
        physical_condition_score: physicalScore,
        sleep_quality_score: sleepScore,
        user_self_evaluation: evaluation,
      });
      setSuccessMsg('日報を保存しました！');
      setHasSavedLog(true);
      await fetchData();
      
      setTimeout(() => setSuccessMsg(null), 3000);
    } catch (err) {
      setError('保存に失敗しました。');
      setTimeout(() => setError(null), 3000);
    } finally {
      setSavingLog(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="p-8">
        <div className="bg-red-50 text-red-600 p-4 rounded-xl border border-red-100">
          データが見つかりません
        </div>
      </div>
    );
  }

  const { attendance } = data;
  const canCheckIn = !attendance.checked_in;
  const canCheckOut = attendance.checked_in && !attendance.checked_out;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      
      {successMsg && (
        <div className="bg-emerald-50 text-emerald-700 p-4 rounded-xl border border-emerald-200 font-bold flex items-center justify-between animate-in fade-in slide-in-from-top-4">
          {successMsg}
        </div>
      )}
      
      {error && (
        <div className="bg-red-50 text-red-600 p-4 rounded-xl border border-red-200 font-bold flex items-center justify-between animate-in fade-in slide-in-from-top-4">
          {error}
        </div>
      )}

      <div>
        <h1 className="text-2xl font-black text-slate-800 tracking-tight">マイページ</h1>
        <p className="text-slate-500 mt-1 text-sm font-medium">毎日の打刻と振り返りを行いましょう</p>
      </div>

      {/* Attendance Section */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 shadow-xl shadow-slate-200/40 border border-slate-100">
        <h2 className="text-lg font-black text-slate-800 mb-6 flex items-center gap-2">
          今日の打刻
        </h2>
        
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          <div>
            <button
              disabled={!canCheckIn}
              onClick={() => handleAttendance('CHECK_IN')}
              className={`w-full py-6 sm:py-8 rounded-2xl text-xl font-black transition-all duration-300 ${
                canCheckIn 
                  ? 'bg-gradient-to-br from-indigo-500 to-indigo-600 text-white shadow-lg shadow-indigo-200 hover:shadow-indigo-300 hover:-translate-y-1 active:translate-y-0 active:scale-95' 
                  : 'bg-slate-100 text-slate-400 cursor-not-allowed border-2 border-slate-200'
              }`}
            >
              通所する
            </button>
            {attendance.check_in_time && (
              <p className="text-center text-sm font-bold text-slate-500 mt-3">
                打刻時間: {new Date(attendance.check_in_time).toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' })}
              </p>
            )}
          </div>

          <div>
            <button
              disabled={!canCheckOut}
              onClick={() => handleAttendance('CHECK_OUT')}
              className={`w-full py-6 sm:py-8 rounded-2xl text-xl font-black transition-all duration-300 ${
                canCheckOut 
                  ? 'bg-gradient-to-br from-rose-500 to-rose-600 text-white shadow-lg shadow-rose-200 hover:shadow-rose-300 hover:-translate-y-1 active:translate-y-0 active:scale-95' 
                  : 'bg-slate-100 text-slate-400 cursor-not-allowed border-2 border-slate-200'
              }`}
            >
              退所する
            </button>
            {attendance.check_out_time && (
              <p className="text-center text-sm font-bold text-slate-500 mt-3">
                打刻時間: {new Date(attendance.check_out_time).toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' })}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Daily Log Section */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 shadow-xl shadow-slate-200/40 border border-slate-100">
        <h2 className="text-lg font-black text-slate-800 mb-6 flex items-center gap-2">
          今日の日報・振り返り
        </h2>
        
        <div className="space-y-8">
          <div>
            <label className="block text-sm font-bold text-slate-700 mb-4">今日の体調（1:悪い 〜 5:良い）</label>
            <div className="flex justify-between items-center px-2">
              {[1, 2, 3, 4, 5].map((val) => (
                <button
                  key={val}
                  onClick={() => setPhysicalScore(val)}
                  className={`w-12 h-12 rounded-full font-black text-lg transition-all duration-200 ${
                    physicalScore === val 
                      ? 'bg-indigo-600 text-white shadow-md shadow-indigo-200 scale-110' 
                      : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
                  }`}
                >
                  {val}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-bold text-slate-700 mb-4">昨晩の睡眠（1:眠れなかった 〜 5:よく眠れた）</label>
            <div className="flex justify-between items-center px-2">
              {[1, 2, 3, 4, 5].map((val) => (
                <button
                  key={val}
                  onClick={() => setSleepScore(val)}
                  className={`w-12 h-12 rounded-full font-black text-lg transition-all duration-200 ${
                    sleepScore === val 
                      ? 'bg-indigo-600 text-white shadow-md shadow-indigo-200 scale-110' 
                      : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
                  }`}
                >
                  {val}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-bold text-slate-700 mb-2">今日の振り返り・特記事項</label>
            <textarea
              rows={4}
              className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-colors resize-none placeholder-slate-400"
              placeholder="今日頑張ったこと、困ったことなどを自由に書いてください。"
              value={evaluation}
              onChange={(e) => setEvaluation(e.target.value)}
            />
          </div>

          <div className="pt-2">
            <button 
              disabled={savingLog}
              onClick={handleSaveDailyLog}
              className="w-full sm:w-auto px-8 py-3.5 bg-slate-900 text-white font-bold rounded-xl hover:bg-slate-800 transition-colors shadow-lg shadow-slate-900/20 disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {savingLog ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                  保存中...
                </>
              ) : hasSavedLog ? '日報を修正する' : '日報を保存する'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UserMyPage;
