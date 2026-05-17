import React from 'react';
import { 
  Sun, Moon, CheckCircle2, 
  Target, MessageCircle, Play, LogOut, 
  Loader2, Star, Clock, Hash
} from 'lucide-react';
import type { UserStatus, UserGoal } from '../services/userSupportApi';

interface UserDashboardViewProps {
  userName: string | null;
  status: UserStatus | null;
  goals: UserGoal[];
  loading: boolean;
  formValues: Record<string, any>;
  setFormValues: React.Dispatch<React.SetStateAction<Record<string, any>>>;
  isSubmitting: boolean;
  handlePunch: (type: 'CHECK_IN' | 'CHECK_OUT') => Promise<void>;
  submitLog: (section: 'morning' | 'evening') => Promise<void>;
}

export const UserDashboardView: React.FC<UserDashboardViewProps> = ({
  userName,
  status,
  goals,
  loading,
  formValues,
  setFormValues,
  isSubmitting,
  handlePunch,
  submitLog
}) => {

  const renderFieldInput = (field: any) => {
    const value = formValues[field.id] || '';
    const onChange = (val: any) => setFormValues({ ...formValues, [field.id]: val });

    switch (field.type) {
      case 'score':
        return (
          <div className="flex justify-between gap-2">
            {[1, 2, 3, 4, 5].map((score) => (
              <button
                key={score}
                type="button"
                onClick={() => onChange(score)}
                className={`flex-1 py-4 rounded-2xl border-2 transition-all text-xl font-bold shadow-sm ${
                  value === score ? 'border-indigo-600 bg-indigo-50 scale-105' : 'border-slate-100 bg-white hover:border-indigo-200'
                }`}
              >
                {field.score_style === 'numbers' ? score : (
                  score === 1 ? '😞' : score === 2 ? '😟' : score === 3 ? '😐' : score === 4 ? '🙂' : '😄'
                )}
              </button>
            ))}
          </div>
        );
      case 'text':
        return (
          <textarea 
            value={value}
            onChange={(e) => onChange(e.target.value)}
            className="w-full h-24 p-4 rounded-2xl border-2 border-slate-100 bg-slate-50 focus:bg-white focus:border-indigo-500 outline-none transition-all resize-none text-base"
            placeholder="入力してください..."
          />
        );
      case 'time':
        return (
          <div className="relative">
            <Clock className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
            <input 
              type="time"
              value={value}
              onChange={(e) => onChange(e.target.value)}
              className="w-full p-4 pl-12 rounded-2xl border-2 border-slate-100 bg-slate-50 focus:bg-white focus:border-indigo-500 outline-none transition-all text-lg font-bold text-slate-700"
            />
          </div>
        );
      case 'number':
        return (
          <div className="relative">
            <Hash className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
            <input 
              type="number"
              step="0.1"
              value={value}
              onChange={(e) => onChange(e.target.value)}
              className="w-full p-4 pl-12 rounded-2xl border-2 border-slate-100 bg-slate-50 focus:bg-white focus:border-indigo-500 outline-none transition-all text-lg font-bold text-slate-700"
              placeholder="0.0"
            />
          </div>
        );
      default:
        return null;
    }
  };

  if (loading && !status) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <Loader2 className="animate-spin text-indigo-500 mb-4" size={48} />
        <p className="text-slate-500 font-medium">読み込み中...</p>
      </div>
    );
  }

  const isMorning = status?.attendance_status === 'IDLE';
  const isEvening = status?.attendance_status === 'CLOCKED_IN';
  const isFinished = status?.attendance_status === 'CLOCKED_OUT';
  const logSubmitted = isMorning ? status?.has_morning_log : isEvening ? status?.has_evening_log : false;

  return (
    <div className="flex flex-col h-[calc(100vh-120px)] max-w-4xl mx-auto bg-white rounded-[3rem] shadow-2xl shadow-slate-200 overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-700">
      
      {/* 1. Header Area (Status Summary) */}
      <header className={`p-8 border-b transition-colors duration-500 ${
        isFinished ? 'bg-emerald-50 border-emerald-100' : 'bg-white border-slate-100'
      }`}>
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <h1 className="text-3xl font-black text-slate-800 tracking-tight">
              {isFinished ? 'お疲れ様でした！' : logSubmitted ? '記録完了！' : isMorning ? 'おはようございます！' : '今日も順調ですね！'}
            </h1>
            <p className="text-slate-500 font-bold flex items-center gap-2">
              {userName} さん
              {logSubmitted && <span className="text-xs bg-emerald-500 text-white px-2 py-0.5 rounded-full">STEP 1 完了</span>}
            </p>
          </div>
          
          {/* Right side Icon/Status */}
          <div className="w-16 h-16 rounded-3xl bg-slate-50 flex items-center justify-center shadow-inner">
            {isFinished ? <CheckCircle2 className="text-emerald-500" size={32} /> : 
             isMorning ? <Sun className="text-amber-500" size={32} /> : 
             <Moon className="text-indigo-500" size={32} />}
          </div>
        </div>
      </header>

      {/* 2. Primary Action Bar (Sticky Punch Button) */}
      {logSubmitted && !isFinished && (
        <div className="px-8 py-6 bg-indigo-50 border-b border-indigo-100 animate-in slide-in-from-top-4 duration-500">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-white rounded-xl flex items-center justify-center shadow-sm text-indigo-600">
                <ArrowRightIcon size={24} />
              </div>
              <p className="font-black text-indigo-900">
                記録が終わりました。{isMorning ? '来所（通所）' : '退所'}を打刻してください。
              </p>
            </div>
            
            <button 
              type="button"
              onClick={() => handlePunch(isMorning ? 'CHECK_IN' : 'CHECK_OUT')}
              disabled={loading}
              className={`px-12 py-4 rounded-2xl text-xl font-black shadow-xl transition-all flex items-center gap-3 ${
                isMorning ? 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-indigo-200' : 'bg-rose-600 text-white hover:bg-rose-700 shadow-rose-200'
              }`}
            >
              {isMorning ? <Play size={24} fill="currentColor" /> : <LogOut size={24} />}
              {isMorning ? '通所を打刻する' : '退所を打刻する'}
            </button>
          </div>
        </div>
      )}

      {/* 3. Main Content (Scrollable Field List or Finished Screen) */}
      <div className="flex-1 overflow-y-auto p-8 bg-slate-50/30">
        {isFinished ? (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-6">
            <div className="w-40 h-40 bg-emerald-100 rounded-full flex items-center justify-center text-emerald-600 shadow-inner animate-in zoom-in duration-700">
              <CheckCircle2 size={80} />
            </div>
            <div className="space-y-2">
              <h2 className="text-3xl font-black text-slate-800">本日の活動をすべて完了しました</h2>
              <p className="text-xl text-slate-500 font-medium italic">明日も元気に会いましょう！</p>
            </div>
          </div>
        ) : logSubmitted ? (
          /* Already submitted log but waiting for punch - show summary or just goals */
          <div className="space-y-10">
            <div className="bg-white p-10 rounded-[2rem] border-2 border-emerald-100 text-center space-y-4 shadow-sm">
              <div className="w-20 h-20 bg-emerald-50 text-emerald-500 rounded-full flex items-center justify-center mx-auto">
                <CheckCircle2 size={40} />
              </div>
              <h3 className="text-xl font-black text-slate-800">記録は無事に保存されました</h3>
              <p className="text-slate-500 font-medium">上のボタンから打刻を行ってください。</p>
            </div>
            
            <section className="space-y-6">
              <div className="flex items-center gap-3">
                <Target className="text-indigo-600" size={24} />
                <h2 className="text-xl font-black text-slate-800">今日の目標</h2>
              </div>
              <div className="grid gap-4">
                {goals.map((goal) => (
                  <div key={goal.id} className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm flex items-center gap-4">
                    <Star size={20} className="text-amber-400" fill="currentColor" />
                    <p className="font-bold text-slate-700">{goal.content}</p>
                  </div>
                ))}
              </div>
            </section>
          </div>
        ) : (
          /* Input Form */
          <div className="space-y-10">
            <div className="space-y-8">
              {(isMorning ? status?.log_config?.morning_fields : status?.log_config?.evening_fields)?.map(field => (
                <div key={field.id} className="space-y-3">
                  <label className="text-lg font-black text-slate-700 flex items-center gap-2 pl-1">
                    {field.label}
                    {field.required && <span className="text-[10px] bg-rose-100 text-rose-500 px-2 py-0.5 rounded-full uppercase tracking-widest font-black">必須</span>}
                  </label>
                  <div className="bg-white p-1 rounded-[1.5rem] shadow-sm">
                    {renderFieldInput(field)}
                  </div>
                </div>
              ))}
            </div>

            <button 
              type="button"
              onClick={() => submitLog(isMorning ? 'morning' : 'evening')}
              disabled={isSubmitting}
              className="w-full py-6 bg-slate-900 text-white rounded-3xl text-xl font-black hover:bg-slate-800 transition-all shadow-2xl disabled:opacity-50"
            >
              {isSubmitting ? <Loader2 className="animate-spin mx-auto" /> : '入力を完了して次へ'}
            </button>
            
            {/* Contextual Goals (visible during input) */}
            {isMorning && (
              <section className="p-8 bg-amber-50/50 rounded-[2rem] border border-amber-100/50 space-y-4">
                <h4 className="text-sm font-black text-amber-700 uppercase tracking-widest">昨日の振り返りから</h4>
                <p className="text-amber-900 font-bold leading-relaxed italic">「今日は自分から挨拶をすることを意識します」</p>
              </section>
            )}
          </div>
        )}
      </div>

      {/* 4. Footer Help Bar (Sticky) */}
      {!isFinished && (
        <footer className="px-8 py-4 bg-white border-t border-slate-100 flex items-center justify-between">
          <button type="button" className="flex items-center gap-2 text-slate-400 hover:text-indigo-600 transition-colors text-sm font-bold">
            <MessageCircle size={18} /> スタッフへ相談
          </button>
          <div className="text-[10px] font-black text-slate-300 uppercase tracking-widest">
            {new Date().toLocaleDateString('ja-JP')}
          </div>
        </footer>
      )}

    </div>
  );
};

const ArrowRightIcon = ({ size }: { size: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M5 12h14M12 5l7 7-7 7"/>
  </svg>
);
