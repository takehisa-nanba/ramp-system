import React, { useState } from 'react';
import { Search } from 'lucide-react';
import { usePostalLookup } from '../../hooks/usePostalLookup';

interface UXFieldProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  className?: string;
  error?: string;
}

/**
 * 汎用入力コンポーネント。
 * RAMP共通のプレミアムデザインシステム（丸角、Indigoリング、太字ラベル）を踏襲。
 * useAutoKana から提供される inputProps をそのままスプレッド展開できます。
 */
export const UXField: React.FC<UXFieldProps> = ({
  label,
  className = '',
  error,
  type = 'text',
  ...props
}) => {
  return (
    <label className={`block ${className}`}>
      <span className="block text-xs font-black text-slate-500 mb-1">{label}</span>
      <input
        type={type}
        className={`w-full h-10 px-3 rounded-xl border bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm transition-all ${
          error ? 'border-rose-300 focus:ring-rose-500' : 'border-slate-200'
        }`}
        {...props}
      />
      {error && <span className="block text-xs font-bold text-rose-500 mt-1">{error}</span>}
    </label>
  );
};

interface PostalAddressFieldProps {
  postalLabel?: string;
  addressLabel?: string;
  postalValue: string;
  addressValue: string;
  onPostalChange: (val: string) => void;
  onAddressChange: (val: string) => void;
  className?: string;
  postalPlaceholder?: string;
  addressPlaceholder?: string;
}

/**
 * 郵便番号から住所を自動検索・補完する共通住所入力コンポーネント。
 * 郵便番号（7桁）の横に「住所検索」ボタンを配置し、API呼び出し結果を自動で住所欄に補完します。
 */
export const PostalAddressField: React.FC<PostalAddressFieldProps> = ({
  postalLabel = '郵便番号',
  addressLabel = '住所',
  postalValue,
  addressValue,
  onPostalChange,
  onAddressChange,
  className = '',
  postalPlaceholder = '例: 1000001',
  addressPlaceholder = '東京都千代田区...',
}) => {
  const { lookupAddress, loading, error: lookupError } = usePostalLookup();
  const [localError, setLocalError] = useState<string | null>(null);

  const handleSearch = async () => {
    setLocalError(null);
    const cleanZip = postalValue.replace(/[^\d]/g, '');
    if (cleanZip.length !== 7) {
      setLocalError('郵便番号は7桁の数字で入力してください。');
      return;
    }

    const res = await lookupAddress(cleanZip);
    if (res) {
      onAddressChange(res);
    } else {
      setLocalError('住所の取得に失敗しました。郵便番号を確認してください。');
    }
  };

  return (
    <div className={`grid md:grid-cols-3 gap-4 items-end ${className}`}>
      {/* 郵便番号入力 & 検索ボタン */}
      <div className="md:col-span-1">
        <span className="block text-xs font-black text-slate-500 mb-1">{postalLabel}</span>
        <div className="flex gap-2">
          <input
            type="text"
            value={postalValue}
            placeholder={postalPlaceholder}
            onChange={(e) => onPostalChange(e.target.value)}
            className="flex-1 h-10 px-3 rounded-xl border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm transition-all"
          />
          <button
            type="button"
            onClick={handleSearch}
            disabled={loading}
            className="h-10 px-3 rounded-xl bg-indigo-50 border border-indigo-200 text-indigo-600 font-bold hover:bg-indigo-100 disabled:opacity-50 transition-colors flex items-center justify-center gap-1 text-xs shrink-0"
          >
            <Search size={14} />
            {loading ? '検索中...' : '住所検索'}
          </button>
        </div>
      </div>

      {/* 住所入力 */}
      <div className="md:col-span-2">
        <label className="block">
          <span className="block text-xs font-black text-slate-500 mb-1">{addressLabel}</span>
          <input
            type="text"
            value={addressValue}
            placeholder={addressPlaceholder}
            onChange={(e) => onAddressChange(e.target.value)}
            className="w-full h-10 px-3 rounded-xl border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm transition-all"
          />
        </label>
      </div>

      {(localError || lookupError) && (
        <div className="md:col-span-3 text-xs font-bold text-rose-500 mt-1">
          {localError || lookupError}
        </div>
      )}
    </div>
  );
};

interface TimeDurationInputProps {
  label: string;
  totalSeconds: number;
  onChange: (totalSeconds: number) => void;
  className?: string;
  error?: string;
}

/**
 * バックエンドの総秒数を、フロントエンドで時間・分・秒に分解して表示・編集するコンポーネント。
 * 入力された時間・分・秒は自動的に総秒数に再変換されて onChange に返されます。
 */
export const TimeDurationInput: React.FC<TimeDurationInputProps> = ({
  label,
  totalSeconds,
  onChange,
  className = '',
  error,
}) => {
  // 総秒数から時間・分・秒に分解する
  const hoursVal = Math.floor((totalSeconds || 0) / 3600);
  const minutesVal = Math.floor(((totalSeconds || 0) % 3600) / 60);
  const secondsVal = (totalSeconds || 0) % 60;

  const handleTimeChange = (type: 'hours' | 'minutes' | 'seconds', valStr: string) => {
    const val = parseInt(valStr, 10) || 0;
    
    let nextHours = hoursVal;
    let nextMinutes = minutesVal;
    let nextSeconds = secondsVal;

    if (type === 'hours') nextHours = val;
    if (type === 'minutes') nextMinutes = val;
    if (type === 'seconds') nextSeconds = val;

    // 総秒数に再変換
    const nextTotalSeconds = nextHours * 3600 + nextMinutes * 60 + nextSeconds;
    onChange(nextTotalSeconds);
  };

  return (
    <div className={`block ${className}`}>
      <span className="block text-xs font-black text-slate-500 mb-1">{label}</span>
      <div className="flex items-center gap-2">
        {/* 時間 */}
        <div className="flex items-center gap-1">
          <input
            type="number"
            min="0"
            value={hoursVal}
            onChange={(e) => handleTimeChange('hours', e.target.value)}
            className="w-16 h-10 px-2 rounded-xl border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm text-center font-bold"
          />
          <span className="text-xs font-bold text-slate-500">時間</span>
        </div>

        {/* 分 */}
        <div className="flex items-center gap-1">
          <input
            type="number"
            min="0"
            max="59"
            value={minutesVal}
            onChange={(e) => handleTimeChange('minutes', e.target.value)}
            className="w-16 h-10 px-2 rounded-xl border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm text-center font-bold"
          />
          <span className="text-xs font-bold text-slate-500">分</span>
        </div>

        {/* 秒 */}
        <div className="flex items-center gap-1">
          <input
            type="number"
            min="0"
            max="59"
            value={secondsVal}
            onChange={(e) => handleTimeChange('seconds', e.target.value)}
            className="w-16 h-10 px-2 rounded-xl border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm text-center font-bold"
          />
          <span className="text-xs font-bold text-slate-500">秒</span>
        </div>
      </div>
      {error && <span className="block text-xs font-bold text-rose-500 mt-1">{error}</span>}
    </div>
  );
};
