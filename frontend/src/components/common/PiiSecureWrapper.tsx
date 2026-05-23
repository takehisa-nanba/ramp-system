import React, { useState, useEffect, useRef } from 'react';
import { Eye, EyeOff, Clock } from 'lucide-react';

interface PiiSecureWrapperProps {
  value: string;
  fallbackText?: string;
}

export const PiiSecureWrapper: React.FC<PiiSecureWrapperProps> = ({
  value,
  fallbackText = '••••••••'
}) => {
  const [isRevealed, setIsRevealed] = useState(false);
  const [timeLeft, setTimeLeft] = useState(0);

  const timerRef = useRef<any | null>(null);

  const startAutoMaskTimer = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    setTimeLeft(20); // 20秒後に自動マスク化
    timerRef.current = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          if (timerRef.current) clearInterval(timerRef.current);
          setIsRevealed(false);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const handleRevealToggle = () => {
    if (isRevealed) {
      setIsRevealed(false);
      if (timerRef.current) clearInterval(timerRef.current);
      return;
    }

    // すでに復号された値をプロパティとして持っているため、
    // API呼び出しもダイアログも不要で、瞬時（0ms）にトグル表示！
    setIsRevealed(true);
    startAutoMaskTimer();
  };

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  // 利用者が切り替わった（valueが変わった）場合は自動で非表示に戻す
  useEffect(() => {
    setIsRevealed(false);
    if (timerRef.current) clearInterval(timerRef.current);
  }, [value]);

  return (
    <div className="relative w-full max-w-md">
      <div className="flex items-center justify-between gap-3 bg-slate-50 px-4 py-2.5 rounded-2xl border border-slate-100 font-medium w-full transition-all shadow-inner hover:bg-slate-100/50">
        
        {/* 左側: 値の表示 */}
        <span className={`flex-1 min-w-0 font-bold truncate ${
          isRevealed ? 'text-slate-800 font-mono text-sm tracking-wide' : 'text-slate-400 select-none tracking-widest'
        }`}>
          {isRevealed ? value : fallbackText}
        </span>
        
        {/* 右側: カウントダウン ＋ 目のボタン（ボタン位置固定） */}
        <div className="flex items-center gap-2 shrink-0">
          {isRevealed && timeLeft > 0 && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 bg-amber-50 text-amber-700 rounded-full border border-amber-100 text-[9px] font-black tracking-wider animate-in fade-in slide-in-from-right-1 duration-200">
              <Clock size={10} className="animate-pulse" />
              <span>あと{timeLeft}秒</span>
            </div>
          )}
          
          <button 
            type="button" 
            onClick={handleRevealToggle}
            className="p-1.5 bg-white text-indigo-600 hover:text-indigo-800 disabled:opacity-50 transition-all rounded-xl border border-slate-100 shadow-sm hover:shadow-md shrink-0 w-8 h-8 flex items-center justify-center"
            title={isRevealed ? "非表示にする" : "クリックして表示"}
          >
            {isRevealed ? (
              <EyeOff size={14} />
            ) : (
              <Eye size={14} />
            )}
          </button>
        </div>

      </div>
    </div>
  );
};
