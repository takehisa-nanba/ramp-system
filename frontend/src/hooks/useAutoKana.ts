import { useState, useRef, useEffect } from 'react';
import type { ChangeEvent, CompositionEvent } from 'react';

// ひらがな -> カタカナへの変換ユーティリティ
const toKatakana = (str: string): string => {
  return str.replace(/[\u3041-\u3096]/g, (match) => {
    return String.fromCharCode(match.charCodeAt(0) + 0x60);
  });
};

export interface UseAutoKanaResult {
  value: string;
  setValue: (val: string) => void;
  kana: string;
  setKana: (val: string) => void;
  isManual: boolean;
  setIsManual: (val: boolean) => void;
  hasJapanese: boolean;
  inputProps: {
    value: string;
    onChange: (e: ChangeEvent<HTMLInputElement>) => void;
    onCompositionUpdate: (e: CompositionEvent<HTMLInputElement>) => void;
    onCompositionEnd: (e: CompositionEvent<HTMLInputElement>) => void;
  };
  kanaInputProps: {
    value: string;
    onChange: (e: ChangeEvent<HTMLInputElement>) => void;
  };
  reset: () => void;
}

export const useAutoKana = (
  initialValue: string = '',
  initialKana: string = '',
  onChangeCallbacks?: {
    onValueChange?: (val: string) => void;
    onKanaChange?: (kana: string) => void;
  }
): UseAutoKanaResult => {
  const [value, setValue] = useState(initialValue);
  const [kana, setKana] = useState(initialKana);
  const [isManual, setIsManual] = useState(false);

  // 漢字フィールドの入力値に日本語（ひらがな、カタカナ、漢字）が含まれているか判定
  const hasJapanese = /[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9faf]/.test(value);

  // IME未確定中のふりがなバッファ
  const compositionValRef = useRef('');
  const prevValueRef = useRef(initialValue);

  // 初期値の同期
  useEffect(() => {
    setValue(initialValue);
    prevValueRef.current = initialValue;
  }, [initialValue]);

  useEffect(() => {
    setKana(initialKana);
    if (initialKana) {
      setIsManual(true); // 既存データがある場合は手動編集扱いにして自動上書きを保護
    } else {
      setIsManual(false);
    }
  }, [initialKana]);

  // カナに入力可能な文字のみを抽出するフィルタリング
  const filterKana = (str: string): string => {
    if (hasJapanese) {
      // 日本語の姓名が入力されている場合：英字はロック（ひらがな、カタカナ、長音、スペースのみ許可）
      return str.replace(/[^\u3040-\u309f\u30a0-\u30ff\u30fc\s]/g, '');
    } else {
      // 日本語以外の姓名（アルファベット等）の場合：英字も解放
      return str.replace(/[^\u3040-\u309f\u30a0-\u30ff\u30fc\sa-zA-Z]/g, '');
    }
  };

  // 漢字フィールドの変更ハンドラ
  const handleValueChange = (e: ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setValue(val);
    if (onChangeCallbacks?.onValueChange) {
      onChangeCallbacks.onValueChange(val);
    }

    // 値がクリアされたらリセット
    if (!val) {
      setKana('');
      setIsManual(false);
      prevValueRef.current = '';
      compositionValRef.current = '';
      if (onChangeCallbacks?.onKanaChange) {
        onChangeCallbacks.onKanaChange('');
      }
      return;
    }

    // 非IME直接入力時のカナ補完フォールバック
    if (!isManual) {
      const prev = prevValueRef.current;
      if (val.length > prev.length) {
        const added = val.slice(prev.length);
        // 入力値自体が最初からかなである場合
        if (/^[\u3040-\u309f\u30a0-\u30ff]+$/.test(added)) {
          const newKana = filterKana(kana + toKatakana(added));
          setKana(newKana);
          if (onChangeCallbacks?.onKanaChange) {
            onChangeCallbacks.onKanaChange(newKana);
          }
        }
      }
    }
    prevValueRef.current = val;
  };

  // IME未確定中イベント
  const handleCompositionUpdate = (e: CompositionEvent<HTMLInputElement>) => {
    if (isManual) return;
    const data = e.data;
    // ローマ字入力や確定前ひらがな/カタカナを検知
    if (/^[\u3040-\u309f\u30a0-\u30ff\u0020-\u007e\uff61-\uff9f]+$/.test(data)) {
      // ローマ字の中間入力（a, s, k等）を除去して、ひらがな・カタカナ部分のみを抽出
      const kanaOnly = data.replace(/[a-zA-Z]/g, '');
      if (kanaOnly) {
        compositionValRef.current = toKatakana(kanaOnly);
      }
    }
  };

  // IME確定イベント
  const handleCompositionEnd = () => {
    if (isManual) {
      compositionValRef.current = '';
      return;
    }
    if (compositionValRef.current) {
      const newKana = filterKana(kana + compositionValRef.current);
      setKana(newKana);
      if (onChangeCallbacks?.onKanaChange) {
        onChangeCallbacks.onKanaChange(newKana);
      }
    }
    compositionValRef.current = '';
    prevValueRef.current = value;
  };

  // カナフィールドの変更ハンドラ (手動編集＆フィルタリング適用)
  const handleKanaChange = (e: ChangeEvent<HTMLInputElement>) => {
    setIsManual(true); // 手動編集フラグを立てて自動補完をロック
    const filtered = filterKana(e.target.value);
    setKana(filtered);
    if (onChangeCallbacks?.onKanaChange) {
      onChangeCallbacks.onKanaChange(filtered);
    }
  };

  const reset = () => {
    setValue('');
    setKana('');
    setIsManual(false);
    prevValueRef.current = '';
    compositionValRef.current = '';
    if (onChangeCallbacks?.onValueChange) onChangeCallbacks.onValueChange('');
    if (onChangeCallbacks?.onKanaChange) onChangeCallbacks.onKanaChange('');
  };

  return {
    value,
    setValue: (val: string) => {
      setValue(val);
      prevValueRef.current = val;
      if (!val) {
        setKana('');
        setIsManual(false);
      }
    },
    kana,
    setKana: (val: string) => {
      const filtered = filterKana(val);
      setKana(filtered);
      setIsManual(true);
    },
    isManual,
    setIsManual,
    hasJapanese,
    inputProps: {
      value,
      onChange: handleValueChange,
      onCompositionUpdate: handleCompositionUpdate,
      onCompositionEnd: handleCompositionEnd,
    },
    kanaInputProps: {
      value: kana,
      onChange: handleKanaChange,
    },
    reset,
  };
};
