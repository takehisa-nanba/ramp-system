import React, { useState, useEffect } from 'react';
import { Play, Square, Timer, X, Users, ChevronDown, AlertTriangle } from 'lucide-react';
import { dailyLogApi } from '../services/dailyLogApi';
import type { ActivityTag, UserSummary } from '../services/dailyLogApi';

// =================================================================
// ActivityTracker (活動トラッカー / Floating Widget)
// =================================================================
const ActivityTracker: React.FC = () => {
  const [isTracking, setIsTracking] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [startTime, setStartTime] = useState<Date | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  
  // Tags & Users from API
  const [tags, setTags] = useState<ActivityTag[]>([]);
  const [users, setUsers] = useState<UserSummary[]>([]);
  const [selectedTagId, setSelectedTagId] = useState<number | null>(null);
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    // マスターデータのロード
    const loadMasters = async () => {
      try {
        const [tagsData, usersData] = await Promise.all([
          dailyLogApi.getTags(),
          dailyLogApi.getUsers()
        ]);
        setTags(tagsData);
        setUsers(usersData);
      } catch (err) {
        console.error('Failed to load masters:', err);
      }
    };
    loadMasters();
  }, []);

  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | null = null;
    if (isTracking) {
      interval = setInterval(() => {
        setSeconds((s) => s + 1);
      }, 1000);
    } else if (!isTracking && seconds !== 0) {
      if (interval) clearInterval(interval);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isTracking, seconds]);

  const formatTime = (totalSeconds: number) => {
    const hours = Math.floor(totalSeconds / 3600);
    const mins = Math.floor((totalSeconds % 3600) / 60);
    const secs = totalSeconds % 60;
    return `${hours > 0 ? hours + ':' : ''}${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const selectedTag = tags.find(t => t.id === selectedTagId);
  const isDirectSupport = selectedTag?.is_direct_support || false;
  
  // バリデーション: 直接支援タグの場合、利用者選択が必須
  const canStart = selectedTagId !== null && (!isDirectSupport || selectedUserId !== null);

  const handleStartStop = async () => {
    if (isTracking) {
      // 停止と保存
      setIsLoading(true);
      setErrorMessage(null);
      try {
        const endTime = new Date();
        await dailyLogApi.logActivity({
          tag_id: selectedTagId!,
          user_id: selectedUserId || undefined,
          start_time: startTime!.toISOString(),
          end_time: endTime.toISOString(),
          duration_minutes: Math.ceil(seconds / 60),
          notes: ''
        });
        setIsTracking(false);
        setSeconds(0);
        setStartTime(null);
        // 保存成功したらリセット（タグと利用者は残しても良いが、一旦リセット）
        setSelectedTagId(null);
        setSelectedUserId(null);
      } catch (err: any) {
        let errorMsg = '活動の保存に失敗しました';
        if (err.response?.data?.message) {
          errorMsg = err.response.data.message;
        } else if (err.response?.data?.error) {
          errorMsg = err.response.data.error;
        }
        setErrorMessage(errorMsg);
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    } else {
      // 開始
      setStartTime(new Date());
      setIsTracking(true);
      setErrorMessage(null);
    }
  };

  const handleReset = () => {
    setIsTracking(false);
    setSeconds(0);
    setStartTime(null);
    setSelectedTagId(null);
    setSelectedUserId(null);
    setErrorMessage(null);
  };

  if (!isOpen && !isTracking) {
    return (
      <button 
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 bg-indigo-600 hover:bg-indigo-700 text-white rounded-full p-4 shadow-lg hover:shadow-indigo-500/30 transition-all flex items-center justify-center group z-50"
      >
        <Timer size={24} />
        <span className="max-w-0 overflow-hidden group-hover:max-w-xs transition-all duration-300 ease-in-out whitespace-nowrap group-hover:ml-2 group-hover:pr-2 font-medium">
          活動を記録
        </span>
      </button>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 w-80 bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden z-50 animate-in slide-in-from-bottom-5 fade-in duration-300">
      {/* Header */}
      <div className={`px-4 py-3 flex items-center justify-between transition-colors ${isTracking ? 'bg-emerald-50' : 'bg-slate-50 border-b border-slate-100'}`}>
        <div className="flex items-center gap-2">
          {isTracking ? (
            <div className="flex h-3 w-3 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
            </div>
          ) : (
            <Timer size={16} className="text-slate-400" />
          )}
          <span className={`font-bold text-sm ${isTracking ? 'text-emerald-700' : 'text-slate-600'}`}>
            {isTracking ? '記録中...' : '新しい活動'}
          </span>
        </div>
        <button 
          onClick={() => setIsOpen(false)} 
          disabled={isTracking}
          className="text-slate-400 hover:text-slate-600 p-1 rounded-md hover:bg-slate-200/50 disabled:opacity-30"
        >
          <X size={16} />
        </button>
      </div>

      {/* Body */}
      <div className="p-4 space-y-4">
        {/* Tag Selection */}
        <div className="space-y-1.5">
          <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider ml-1">活動タグ</label>
          <div className="relative">
            <select 
              value={selectedTagId || ''} 
              onChange={(e) => setSelectedTagId(Number(e.target.value) || null)}
              disabled={isTracking}
              className="w-full appearance-none bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 outline-none transition-all pr-10"
            >
              <option value="">活動を選択...</option>
              {tags.map(tag => (
                <option key={tag.id} value={tag.id}>{tag.name}</option>
              ))}
            </select>
            <ChevronDown size={16} className="absolute right-3 top-2.5 text-slate-400 pointer-events-none" />
          </div>
        </div>

        {/* User Selection (Conditionally rendered) */}
        {isDirectSupport && (
          <div className="space-y-1.5 animate-in fade-in slide-in-from-top-2 duration-300">
            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider ml-1">対象の利用者</label>
            <div className="relative">
              <select 
                value={selectedUserId || ''} 
                onChange={(e) => setSelectedUserId(Number(e.target.value) || null)}
                disabled={isTracking}
                className="w-full appearance-none bg-emerald-50/50 border border-emerald-100 rounded-xl px-3 py-2 text-sm focus:ring-2 focus:ring-emerald-500 outline-none transition-all pr-10"
              >
                <option value="">利用者を選択...</option>
                {users.map(user => (
                  <option key={user.id} value={user.id}>{user.display_name}</option>
                ))}
              </select>
              <Users size={16} className="absolute right-3 top-2.5 text-emerald-400 pointer-events-none" />
            </div>
          </div>
        )}

        {/* エラーメッセージ（重複警告など）の極上デザイン表示 */}
        {errorMessage && (
          <div className="bg-rose-50 border border-rose-100 text-rose-800 p-3.5 rounded-xl text-xs font-bold leading-normal animate-shake flex items-start gap-2">
            <AlertTriangle size={16} className="text-rose-500 shrink-0 mt-0.5" />
            <div className="flex-1">
              <span className="block font-black text-rose-950 mb-0.5">登録できませんでした</span>
              <span className="text-[11px] leading-relaxed">{errorMessage}</span>
            </div>
            <button 
              onClick={() => setErrorMessage(null)} 
              className="text-rose-400 hover:text-rose-600 font-bold ml-1 text-sm shrink-0"
            >
              ×
            </button>
          </div>
        )}

        <div className="flex items-center justify-between pt-2">
          <div className={`text-3xl font-mono tracking-tight font-light ${isTracking ? 'text-slate-800' : 'text-slate-400'}`}>
            {formatTime(seconds)}
          </div>
          
          <div className="flex gap-2">
            {!isTracking && seconds > 0 && (
               <button 
                 onClick={handleReset}
                 className="p-3 text-slate-500 bg-slate-100 hover:bg-slate-200 rounded-full transition-colors"
               >
                 <X size={20} />
               </button>
            )}
            <button 
              onClick={handleStartStop}
              disabled={!canStart || isLoading}
              className={`p-3 rounded-full text-white shadow-md transition-all disabled:opacity-30 disabled:shadow-none ${
                isTracking 
                  ? 'bg-rose-500 hover:bg-rose-600 hover:shadow-rose-500/30' 
                  : 'bg-emerald-500 hover:bg-emerald-600 hover:shadow-emerald-500/30'
              }`}
            >
              {isLoading ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : isTracking ? (
                <Square size={20} fill="currentColor" />
              ) : (
                <Play size={20} fill="currentColor" className="ml-0.5" />
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ActivityTracker;
