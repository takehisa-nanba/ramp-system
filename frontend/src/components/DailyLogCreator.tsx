import React, { useState, useEffect } from 'react';
import { 
  Plus, Check, Clock, Edit2, Trash2, 
  FileText, Send, Users, Loader2, MessageSquare,
  AlertTriangle, ChevronRight, Activity, Zap
} from 'lucide-react';
import { dailyLogApi } from '../services/dailyLogApi';
import type { TimelineEntry } from '../services/dailyLogApi';

const DailyLogCreator: React.FC = () => {
  const [activities, setActivities] = useState<TimelineEntry[]>([]);
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchTimeline = async () => {
      try {
        const data = await dailyLogApi.getTodayTimeline();
        setActivities(data);
      } catch (err) {
        console.error('Failed to fetch timeline:', err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchTimeline();
  }, []);

  const handleSubmit = () => {
    setIsSubmitting(true);
    setTimeout(() => {
      setIsSubmitting(false);
      setSuccess(true);
    }, 1500);
  };

  if (success) {
    return (
      <div className="flex flex-col items-center justify-center h-[70vh] animate-in zoom-in duration-500">
        <div className="w-24 h-24 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mb-6 shadow-inner">
          <Check size={48} strokeWidth={3} />
        </div>
        <h2 className="text-3xl font-black text-slate-800 mb-2">日報を提出しました</h2>
        <p className="text-slate-500 font-medium mb-8">お疲れ様でした。本日の業務記録が正常に保存されました。</p>
        <button 
          onClick={() => setSuccess(false)}
          className="px-8 py-3 bg-slate-900 text-white font-bold rounded-xl shadow-lg hover:scale-105 transition-all"
        >
          記録画面に戻る
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-120px)] bg-white rounded-[2.5rem] shadow-xl border border-slate-200 overflow-hidden animate-in fade-in duration-500">
      
      {/* 1. Sticky Header */}
      <header className="px-8 py-6 border-b border-slate-100 flex items-center justify-between bg-white z-10 shrink-0">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-indigo-50 text-indigo-600 rounded-2xl shadow-inner">
            <FileText size={24} />
          </div>
          <div>
            <h1 className="text-2xl font-black text-slate-800 tracking-tight flex items-center gap-2">
              日報作成（業務記録）
            </h1>
            <p className="text-sm text-slate-500 font-medium">トラッカーと連携した自動タイムライン構築</p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          <div className="hidden md:flex flex-col items-end mr-4">
            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Selected Date</p>
            <p className="text-sm font-black text-slate-700">{new Date().toLocaleDateString('ja-JP', { month: 'long', day: 'numeric', weekday: 'short' })}</p>
          </div>
          <button 
            onClick={handleSubmit} disabled={isSubmitting || activities.length === 0}
            className="px-8 py-3 bg-slate-900 text-white rounded-xl font-bold hover:bg-slate-800 shadow-xl transition-all flex items-center gap-2 disabled:opacity-50"
          >
            {isSubmitting ? <Loader2 className="animate-spin" size={18} /> : <Send size={18} />}
            日報を提出する
          </button>
        </div>
      </header>

      {/* 2. Scrollable Body (Split View) */}
      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden bg-slate-50/30">
        
        {/* Left Pane: Timeline (Main) */}
        <div className="flex-1 overflow-y-auto p-8 custom-scrollbar border-r border-slate-100">
          <div className="max-w-3xl mx-auto space-y-8">
            <div className="flex items-center justify-between mb-2">
               <h3 className="text-sm font-black text-slate-400 uppercase tracking-widest flex items-center gap-2">
                 <Clock size={16} /> Activity Timeline
               </h3>
               <button className="flex items-center gap-1.5 px-4 py-1.5 bg-white border border-slate-200 text-slate-600 rounded-full text-xs font-bold hover:bg-slate-50 transition-all shadow-sm">
                 <Plus size={14} /> 手動追加
               </button>
            </div>

            <div className="relative border-l-2 border-slate-200 ml-3 pl-8 space-y-10 pb-8">
              {isLoading ? (
                <div className="flex flex-col items-center py-20 text-slate-400">
                  <Loader2 className="animate-spin mb-4" size={32} />
                  <p className="font-bold">活動データを読み込み中...</p>
                </div>
              ) : activities.length === 0 ? (
                <div className="text-center py-20 bg-white/50 rounded-3xl border-2 border-dashed border-slate-100">
                  <Activity size={48} className="mx-auto text-slate-200 mb-4" />
                  <p className="text-slate-400 font-bold">本日の活動記録はまだありません</p>
                </div>
              ) : (
                activities.map((activity, idx) => (
                  <div key={idx} className="relative group animate-in slide-in-from-left-4 duration-500" style={{ animationDelay: `${idx * 100}ms` }}>
                    <div className={`absolute -left-[41px] top-0 w-6 h-6 rounded-full border-4 border-white shadow-md ${activity.type === 'support' ? 'bg-emerald-500' : 'bg-slate-400'}`} />
                    
                    <div className="bg-white p-6 rounded-3xl border border-slate-100 shadow-sm group-hover:shadow-md group-hover:border-indigo-100 transition-all flex flex-col sm:flex-row sm:items-start justify-between gap-6">
                      <div className="space-y-3">
                        <div className="flex items-center gap-3">
                          <span className="text-sm font-mono font-black text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-md">{activity.startTime} - {activity.endTime}</span>
                          <span className={`text-[10px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full ${activity.type === 'support' ? 'bg-emerald-50 text-emerald-600' : 'bg-slate-100 text-slate-500'}`}>
                            {activity.type === 'support' ? '直接支援' : '間接業務'}
                          </span>
                        </div>
                        <h4 className="text-lg font-black text-slate-800">{activity.title}</h4>
                        {activity.user && (
                          <p className="text-sm font-bold text-slate-500 flex items-center gap-1.5">
                            <Users size={14} className="text-slate-400" /> {activity.user}
                          </p>
                        )}
                        {activity.notes && (
                           <p className="text-sm text-slate-600 leading-relaxed p-4 bg-slate-50 rounded-2xl border border-slate-100 italic">
                             {activity.notes}
                           </p>
                        )}
                      </div>
                      
                      <div className="flex sm:flex-col gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button className="p-2.5 bg-slate-50 text-slate-400 hover:text-indigo-600 hover:bg-white hover:shadow-sm rounded-xl transition-all"><Edit2 size={16} /></button>
                        <button className="p-2.5 bg-slate-50 text-slate-400 hover:text-rose-500 hover:bg-white hover:shadow-sm rounded-xl transition-all"><Trash2 size={16} /></button>
                      </div>
                    </div>
                  </div>
                ))
              )}

              <div className="relative opacity-40 group">
                <div className="absolute -left-[41px] top-0 w-6 h-6 rounded-full border-4 border-white bg-indigo-400 animate-pulse" />
                <div className="bg-white/50 p-6 rounded-3xl border border-dashed border-slate-200 flex items-center gap-4">
                  <Zap size={20} className="text-indigo-400" />
                  <span className="text-sm font-black text-slate-400">リアルタイム・トラッカー待機中...</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Pane: Summary Form (Sticky Context) */}
        <div className="w-full lg:w-[400px] bg-white border-l border-slate-100 flex flex-col shrink-0">
          <div className="flex-1 overflow-y-auto p-8 space-y-8">
            <h3 className="text-sm font-black text-slate-400 uppercase tracking-widest flex items-center gap-2">
              <MessageSquare size={16} /> 総括・特記事項
            </h3>
            
            <div className="space-y-6">
              <div className="space-y-3">
                <label className="text-xs font-black text-slate-500 uppercase ml-1">本日の所感・引き継ぎ</label>
                <textarea 
                  className="w-full h-48 p-5 bg-slate-50 border border-slate-100 rounded-[2rem] focus:bg-white focus:border-indigo-500 outline-none transition-all resize-none text-sm leading-relaxed"
                  placeholder="支援のポイントや、明日への伝達事項を入力..."
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                />
              </div>

              <div className="space-y-4">
                <label className="text-xs font-black text-slate-500 uppercase ml-1">Flagged Events</label>
                <div className="space-y-3">
                  <label className="flex items-center gap-3 p-4 bg-slate-50 border border-slate-100 rounded-2xl cursor-pointer hover:bg-rose-50 hover:border-rose-100 transition-all group">
                    <div className="w-6 h-6 rounded-lg bg-white border border-slate-200 flex items-center justify-center group-hover:border-rose-300">
                      <input type="checkbox" className="w-3 h-3 rounded text-rose-500 border-none focus:ring-0" />
                    </div>
                    <div className="flex items-center gap-2 text-slate-700 font-bold text-sm">
                       <AlertTriangle size={16} className="text-rose-400" /> ヒヤリハット報告
                    </div>
                  </label>
                  <label className="flex items-center gap-3 p-4 bg-slate-50 border border-slate-100 rounded-2xl cursor-pointer hover:bg-indigo-50 hover:border-indigo-100 transition-all group">
                    <div className="w-6 h-6 rounded-lg bg-white border border-slate-200 flex items-center justify-center group-hover:border-indigo-300">
                      <input type="checkbox" className="w-3 h-3 rounded text-indigo-500 border-none focus:ring-0" />
                    </div>
                    <div className="flex items-center gap-2 text-slate-700 font-bold text-sm">
                       <Zap size={16} className="text-indigo-400" /> 支援計画の変更提案
                    </div>
                  </label>
                </div>
              </div>
            </div>
          </div>

          <footer className="p-8 bg-slate-50 border-t border-slate-100 space-y-4">
             <div className="flex items-center justify-between text-[10px] font-black text-slate-400 uppercase tracking-widest">
               <span>Draft Auto-saved</span>
               <span>18:30:15</span>
             </div>
             <button 
                onClick={handleSubmit} disabled={isSubmitting || activities.length === 0}
                className="w-full py-4 bg-slate-900 text-white rounded-2xl font-black hover:bg-slate-800 transition-all shadow-xl flex items-center justify-center gap-2 disabled:opacity-50"
             >
               日報を提出する <ChevronRight size={18} />
             </button>
          </footer>
        </div>
      </div>
    </div>
  );
};

export default DailyLogCreator;
