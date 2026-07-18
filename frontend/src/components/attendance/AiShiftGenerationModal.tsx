import React, { useState } from 'react';
import { Sparkles, X, Loader2 } from 'lucide-react';

interface Props {
  open: boolean;
  onClose: () => void;
  onGenerate: (instruction: string) => Promise<void>;
  year: number;
  month: number;
}

export const AiShiftGenerationModal: React.FC<Props> = ({ open, onClose, onGenerate, year, month }) => {
  const [instruction, setInstruction] = useState('');
  const [loading, setLoading] = useState(false);

  if (!open) return null;

  const handleGenerate = async () => {
    setLoading(true);
    try {
      await onGenerate(instruction);
      setInstruction('');
      onClose();
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50">
          <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-indigo-600" />
            AIシフト調整アシスタント
          </h2>
          <button 
            onClick={!loading ? onClose : undefined}
            className="text-slate-400 hover:text-slate-600 transition-colors"
            disabled={loading}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6">
          <p className="text-slate-700 font-bold mb-2">
            {year}年{month}月の未確定シフトと最新の基本パターンを比較し、自動で同期します。
          </p>
          <p className="text-sm text-slate-500 mb-6">
            特定の予定を残したい場合や変更したい場合は、AIに自然言語で指示を出してください。（未入力の場合は、すべて最新パターンに同期します）
          </p>

          <div className="mb-4">
            <label className="block text-sm font-bold text-slate-700 mb-2">
              AIへの指示（任意）
            </label>
            <textarea
              autoFocus
              className="w-full border border-slate-300 rounded-xl p-3 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all disabled:opacity-50 disabled:bg-slate-50"
              rows={4}
              placeholder="例: テスト三郎の15日の予定だけはそのまま残して、他は最新パターンにして"
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              disabled={loading}
            />
          </div>

          {loading && (
            <div className="flex items-center gap-3 text-indigo-600 bg-indigo-50 p-3 rounded-lg border border-indigo-100">
              <Loader2 className="w-5 h-5 animate-spin" />
              <span className="text-sm font-bold">AIが最適な調整を考えています...</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-100 bg-slate-50 flex justify-end gap-3">
          <button
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 text-sm font-bold text-slate-600 hover:bg-slate-200 rounded-xl transition-colors disabled:opacity-50"
          >
            キャンセル
          </button>
          <button
            onClick={handleGenerate}
            disabled={loading}
            className="px-6 py-2 text-sm font-bold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {loading ? '処理中...' : '調整を実行する'}
          </button>
        </div>
      </div>
    </div>
  );
};
