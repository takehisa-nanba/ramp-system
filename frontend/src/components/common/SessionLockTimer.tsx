import React, { useState, useEffect, useCallback } from 'react';
import { Lock, RefreshCw, AlertTriangle, ShieldCheck } from 'lucide-react';

export const SessionLockTimer: React.FC = () => {
  const SESSION_TIMEOUT = 600; // 10 minutes (600 seconds)
  const [timeLeft, setTimeLeft] = useState(SESSION_TIMEOUT);
  const [isLocked, setIsLocked] = useState(false);
  const [password, setPassword] = useState('');
  const [passwordError, setPasswordError] = useState('');

  const resetTimer = useCallback(() => {
    if (!isLocked) {
      setTimeLeft(SESSION_TIMEOUT);
    }
  }, [isLocked]);

  // Watch mouse and keyboard activity to auto-extend session
  useEffect(() => {
    const handleActivity = () => {
      resetTimer();
    };

    window.addEventListener('mousemove', handleActivity);
    window.addEventListener('keydown', handleActivity);
    window.addEventListener('mousedown', handleActivity);

    return () => {
      window.removeEventListener('mousemove', handleActivity);
      window.removeEventListener('keydown', handleActivity);
      window.removeEventListener('mousedown', handleActivity);
    };
  }, [resetTimer]);

  // Start countdown
  useEffect(() => {
    if (isLocked) return;

    const timer = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          setIsLocked(true);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [isLocked]);

  const handleExtend = () => {
    resetTimer();
  };

  const handleUnlock = (e: React.FormEvent) => {
    e.preventDefault();
    // Simulate unlock (would typically call backend validation endpoint)
    if (password === 'password' || password === 'password123' || password.length > 5) {
      setIsLocked(false);
      setTimeLeft(SESSION_TIMEOUT);
      setPassword('');
      setPasswordError('');
    } else {
      setPasswordError('無効なパスワードです。');
    }
  };

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  const isWarning = timeLeft <= 60; // 1 minute or less remaining

  return (
    <>
      {/* 1. Header Timer Badge */}
      {!isLocked && (
        <div className={`flex items-center gap-2.5 px-4 py-2 rounded-2xl border transition-all duration-300 font-bold text-xs shrink-0 select-none shadow-sm
          ${isWarning 
            ? 'bg-rose-50 border-rose-200 text-rose-600 animate-pulse' 
            : 'bg-indigo-50/50 backdrop-blur-md border-indigo-100 text-indigo-700 hover:bg-indigo-50'
          }`}
        >
          <Lock size={12} className={isWarning ? 'animate-bounce' : ''} />
          <span>PIIセッションロック: <span className="font-mono text-sm">{formatTime(timeLeft)}</span></span>
          <button 
            type="button" 
            onClick={handleExtend}
            className={`p-1 rounded-lg hover:bg-white transition-all shadow-sm shrink-0 border border-transparent hover:border-slate-100
              ${isWarning ? 'text-rose-700' : 'text-indigo-600'}`}
            title="セッションを延長"
          >
            <RefreshCw size={12} />
          </button>
        </div>
      )}

      {/* 2. Full-screen Lock Overlay */}
      {isLocked && (
        <div className="fixed inset-0 bg-slate-900/90 backdrop-blur-2xl z-[9999] flex items-center justify-center p-4 animate-in fade-in duration-500">
          <div className="bg-white rounded-[2.5rem] p-8 max-w-md w-full border border-slate-100 shadow-2xl text-center space-y-6 animate-in zoom-in-95 duration-300">
            <div className="w-20 h-20 bg-rose-50 border border-rose-100 text-rose-500 rounded-3xl flex items-center justify-center mx-auto shadow-inner">
              <Lock size={36} className="animate-pulse" />
            </div>
            
            <div className="space-y-2">
              <h2 className="text-2xl font-black text-slate-800 tracking-tight">セッション自動ロック</h2>
              <p className="text-sm text-slate-500 font-medium leading-relaxed">
                セキュリティ保護のため、10分間操作がないため個人情報アクセスセッションがロックされました。再認証してください。
              </p>
            </div>

            <form onSubmit={handleUnlock} className="space-y-4 text-left">
              <div className="space-y-1.5">
                <label className="text-xs font-black text-slate-400 uppercase tracking-widest pl-1">パスワード</label>
                <input 
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="ログインパスワードを入力"
                  className="w-full px-5 py-4 bg-slate-50 rounded-2xl border border-slate-100 focus:outline-none focus:bg-white focus:ring-2 focus:ring-indigo-500 transition-all font-mono font-black"
                  required
                />
              </div>

              {passwordError && (
                <div className="flex items-center gap-2 p-3 bg-rose-50 border border-rose-100 text-rose-700 rounded-xl text-xs font-bold animate-in shake">
                  <AlertTriangle size={14} className="shrink-0" />
                  <span>{passwordError}</span>
                </div>
              )}

              <button 
                type="submit"
                className="w-full py-4 bg-slate-900 hover:bg-slate-800 text-white rounded-2xl font-bold tracking-wide transition-all shadow-lg flex items-center justify-center gap-2 mt-2"
              >
                <ShieldCheck size={18} />
                ロック解除
              </button>
            </form>
          </div>
        </div>
      )}
    </>
  );
};
