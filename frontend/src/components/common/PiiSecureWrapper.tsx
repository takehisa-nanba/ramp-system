import React, { useState, useEffect, useRef } from 'react';
import { Eye, EyeOff, Loader2, Clock } from 'lucide-react';
import apiClient from '../../services/apiClient';

interface PiiSecureWrapperProps {
  userId: number;
  piiType: 'phone' | 'email' | 'address' | 'name' | 'bank_account';
  fallbackText?: string;
}

export const PiiSecureWrapper: React.FC<PiiSecureWrapperProps> = ({
  userId,
  piiType,
  fallbackText = '••••••••'
}) => {
  const [decryptedValue, setDecryptedValue] = useState<string | null>(null);
  const [isRevealed, setIsRevealed] = useState(false);
  const [isLogging, setIsLogging] = useState(false);
  const [timeLeft, setTimeLeft] = useState(0);
  const timerRef = useRef<any | null>(null);

  const startAutoMaskTimer = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    setTimeLeft(20); // 20 seconds before auto masking
    timerRef.current = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          if (timerRef.current) clearInterval(timerRef.current);
          setIsRevealed(false);
          setDecryptedValue(null);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const handleReveal = async () => {
    if (isRevealed) {
      setIsRevealed(false);
      setDecryptedValue(null);
      if (timerRef.current) clearInterval(timerRef.current);
      return;
    }

    const reason = window.prompt("個人情報を閲覧する理由を入力してください（10文字以上、監査ログに記録されます）:");
    if (!reason) return;

    if (reason.length < 10) {
      alert("閲覧理由は10文字以上で入力してください。");
      return;
    }

    setIsLogging(true);
    try {
      const res = await apiClient.post<{ value: string }>(`/users/${userId}/decrypt-pii`, {
        pii_type: piiType,
        reason
      });
      setDecryptedValue(res.data.value);
      setIsRevealed(true);
      startAutoMaskTimer();
    } catch (err: any) {
      const msg = err.response?.data?.msg || '復号権限がありません。';
      alert(msg);
    } finally {
      setIsLogging(false);
    }
  };

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-3 bg-slate-50 px-4 py-2.5 rounded-2xl border border-slate-100 font-medium w-full max-w-md transition-all shadow-inner hover:bg-slate-100/50">
      <div className="flex-1 flex items-center justify-between gap-3">
        <span className={isRevealed ? 'text-slate-800 font-mono text-sm tracking-wide break-all' : 'text-slate-400 select-none tracking-widest font-bold'}>
          {isRevealed ? decryptedValue : fallbackText}
        </span>
        
        <button 
          type="button" 
          onClick={handleReveal} 
          disabled={isLogging}
          className="p-1.5 bg-white text-indigo-600 hover:text-indigo-800 disabled:opacity-50 transition-all rounded-xl border border-slate-100 shadow-sm hover:shadow-md shrink-0"
          title={isRevealed ? "非表示にする" : "閲覧理由を入力して表示"}
        >
          {isLogging ? (
            <Loader2 size={16} className="animate-spin text-slate-400" />
          ) : isRevealed ? (
            <EyeOff size={16} />
          ) : (
            <Eye size={16} />
          )}
        </button>
      </div>

      {isRevealed && timeLeft > 0 && (
        <div className="flex items-center gap-1.5 px-3 py-1 bg-amber-50 text-amber-700 rounded-full border border-amber-100 text-[10px] font-black uppercase tracking-widest animate-in fade-in shrink-0 self-start sm:self-auto">
          <Clock size={12} className="animate-pulse" />
          再マスクまで {timeLeft}秒
        </div>
      )}
    </div>
  );
};
