import React, { useState, useEffect } from 'react';
import { Plus, Check, Clock, Edit2, Trash2, Calendar, FileText, Send, Users } from 'lucide-react';
import { dailyLogApi } from '../services/dailyLogApi';
import type { TimelineEntry } from '../services/dailyLogApi';

// =================================================================
// DailyLogCreator (日報作成画面 / タイムラインUI)
// =================================================================
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
    // Mock API call
    setTimeout(() => {
      setIsSubmitting(false);
      setSuccess(true);
    }, 1500);
  };

  if (success) {
    return (
      <div className="flex flex-col items-center justify-center h-[70vh] animate-in zoom-in duration-500">
        <div className="w-24 h-24 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mb-6">
          <Check size={48} strokeWidth={3} />
        </div>
        <h2 className="text-2xl font-bold text-slate-800 mb-2">日報を提出しました！</h2>
        <p className="text-slate-500 mb-8">お疲れ様でした。本日の業務記録が保存されました。</p>
        <button 
          onClick={() => setSuccess(false)}
          className="px-6 py-2 bg-slate-100 hover:bg-slate-200 text-slate-600 font-medium rounded-lg transition-colors"
        >
          記録画面に戻る
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-in fade-in duration-500">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <FileText className="text-indigo-500" />
            日報（活動記録）作成
          </h1>
          <p className="text-slate-500 text-sm mt-1">トラッカーで記録した活動が自動的に反映されます。</p>
        </div>
        <div className="bg-indigo-50 text-indigo-700 px-4 py-2 rounded-lg font-medium flex items-center gap-2 border border-indigo-100">
          <Calendar size={18} />
          {new Date().toLocaleDateString('ja-JP')}
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: Timeline */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="font-bold text-slate-800 flex items-center gap-2">
                <Clock className="text-slate-400" size={20} />
                本日のタイムライン
              </h2>
              <button className="text-sm text-indigo-600 hover:text-indigo-700 font-medium flex items-center gap-1">
                <Plus size={16} /> ブロックを追加
              </button>
            </div>

            <div className="relative border-l-2 border-slate-100 ml-4 space-y-8 pb-4">
              {isLoading ? (
                <div className="text-center py-12">
                  <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
                  <p className="text-slate-500 text-sm">活動実績を読み込み中...</p>
                </div>
              ) : activities.length === 0 ? (
                <div className="text-center py-12 bg-slate-50/50 rounded-2xl border border-dashed border-slate-200 ml-6">
                  <p className="text-slate-400 text-sm">本日の活動記録はまだありません。</p>
                </div>
              ) : (
                activities.map((activity, idx) => (
                  <div key={idx} className="relative pl-6 group">
                    {/* Timeline Dot */}
                    <div className={`absolute -left-[9px] top-1 w-4 h-4 rounded-full border-2 border-white shadow-sm ${activity.type === 'support' ? 'bg-emerald-400' : 'bg-slate-300'}`}></div>
                    
                    {/* Activity Content */}
                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-sm font-mono font-bold text-slate-600">{activity.startTime} - {activity.endTime}</span>
                          {activity.type === 'support' && (
                            <span className="px-2 py-0.5 bg-emerald-50 text-emerald-600 text-xs font-bold rounded">直接支援</span>
                          )}
                          {activity.type === 'office' && (
                            <span className="px-2 py-0.5 bg-slate-100 text-slate-600 text-xs font-bold rounded">間接業務</span>
                          )}
                        </div>
                        <h3 className="font-bold text-slate-800 text-lg">{activity.title}</h3>
                        {activity.user && (
                          <p className="text-sm text-slate-500 mt-1 flex items-center gap-1">
                            <Users size={14} /> 対象: {activity.user}
                          </p>
                        )}
                        {activity.notes && (
                           <p className="text-sm text-slate-500 mt-2 italic bg-slate-50 p-2 rounded-lg border border-slate-100">
                             {activity.notes}
                           </p>
                        )}
                      </div>
                      
                      {/* Actions (visible on hover) */}
                      <div className="opacity-0 group-hover:opacity-100 transition-opacity flex gap-2">
                        <button className="p-2 text-slate-400 hover:text-indigo-600 bg-slate-50 hover:bg-indigo-50 rounded-lg transition-colors">
                          <Edit2 size={16} />
                        </button>
                        <button className="p-2 text-slate-400 hover:text-rose-600 bg-slate-50 hover:bg-rose-50 rounded-lg transition-colors">
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              )}
              
              {!isLoading && (
                <div className="relative pl-6 opacity-50">
                  <div className="absolute -left-[9px] top-1 w-4 h-4 rounded-full border-2 border-white bg-indigo-400 animate-pulse"></div>
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-mono font-bold text-slate-400">リアルタイム</span>
                    <span className="text-sm text-indigo-600 font-medium">トラッカー待機中...</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Submission Form */}
        <div className="space-y-6">
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
            <h2 className="font-bold text-slate-800 mb-4">総括・特記事項</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-bold text-slate-600 mb-2">本日の所感・引き継ぎ事項</label>
                <textarea 
                  className="w-full border border-slate-200 rounded-xl p-3 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none min-h-[120px]"
                  placeholder="本日の支援で気になった点や、明日への引き継ぎ事項を入力してください..."
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                ></textarea>
              </div>

              <div>
                <label className="block text-sm font-bold text-slate-600 mb-2">特記事項フラグ</label>
                <div className="space-y-2">
                  <label className="flex items-center gap-2 p-2 border border-slate-100 rounded-lg hover:bg-slate-50 cursor-pointer transition-colors">
                    <input type="checkbox" className="rounded text-indigo-600 focus:ring-indigo-500" />
                    <span className="text-sm font-medium text-slate-700">ヒヤリハット報告あり</span>
                  </label>
                  <label className="flex items-center gap-2 p-2 border border-slate-100 rounded-lg hover:bg-slate-50 cursor-pointer transition-colors">
                    <input type="checkbox" className="rounded text-indigo-600 focus:ring-indigo-500" />
                    <span className="text-sm font-medium text-slate-700">支援計画の変更提案あり</span>
                  </label>
                </div>
              </div>
            </div>

            <div className="mt-8 pt-6 border-t border-slate-100">
              <button 
                onClick={handleSubmit}
                disabled={isSubmitting || activities.length === 0}
                className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 px-4 rounded-xl shadow-md hover:shadow-lg transition-all disabled:opacity-50"
              >
                {isSubmitting ? (
                  <span className="animate-pulse">送信中...</span>
                ) : (
                  <>
                    <Send size={18} />
                    日報を提出する
                  </>
                )}
              </button>
              <p className="text-center text-xs text-slate-400 mt-3">提出後も当日は修正可能です</p>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};

export default DailyLogCreator;
