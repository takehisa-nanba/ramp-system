import React, { useState, useEffect } from 'react';
import { jobRetentionApi } from '../../services/jobRetentionApi';
import type { SupportPlan, SupportPlanSummary } from '../../services/jobRetentionApi';
import { X, Target, AlertTriangle, AlertCircle, Save, History } from 'lucide-react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  contractId: number;
  userName: string;
  activePlan?: SupportPlanSummary | SupportPlan | null;
  onSaved: (newPlan: SupportPlan) => void;
}

/**
 * 暦上のnか月後を計算するヘルパー（Pythonの relativedelta(months=n) と同等）
 * 例: 2026-08-31 + 6 months -> 2027-02-28
 */
export const addCalendarMonths = (dateStr: string, months: number): string => {
  if (!dateStr) return '';
  const [y, m, d] = dateStr.split('-').map(Number);
  const targetMonthIndex = m - 1 + months;
  const targetYear = y + Math.floor(targetMonthIndex / 12);
  const targetMonth = ((targetMonthIndex % 12) + 12) % 12 + 1;

  const lastDayOfTargetMonth = new Date(targetYear, targetMonth, 0).getDate();
  const clampedDay = Math.min(d, lastDayOfTargetMonth);

  return `${targetYear}-${String(targetMonth).padStart(2, '0')}-${String(clampedDay).padStart(2, '0')}`;
};

export const RetentionPlanReviewModal: React.FC<Props> = ({
  isOpen,
  onClose,
  contractId,
  userName,
  activePlan,
  onSaved,
}) => {
  const isReview = Boolean(activePlan);
  const today = new Date().toISOString().split('T')[0];

  const [reviewDate, setReviewDate] = useState(today);
  const [overallGoal, setOverallGoal] = useState('');
  const [reviewReason, setReviewReason] = useState('');
  const [deadline, setDeadline] = useState('');
  const [maxDeadline, setMaxDeadline] = useState('');

  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // 初期化
  useEffect(() => {
    if (isOpen) {
      const initialDate = today;
      setReviewDate(initialDate);
      const calculatedMax = addCalendarMonths(initialDate, 6);
      setMaxDeadline(calculatedMax);
      setDeadline(calculatedMax);

      if (isReview && activePlan) {
        setOverallGoal(activePlan.overall_support_goal || '');
        setReviewReason('');
      } else {
        setOverallGoal('');
        setReviewReason('初回策定');
      }
      setErrorMsg(null);
    }
  }, [isOpen, activePlan, isReview]);

  // 基準日変更時に最大期限を再計算
  const handleReviewDateChange = (newDate: string) => {
    setReviewDate(newDate);
    if (newDate) {
      const newMax = addCalendarMonths(newDate, 6);
      setMaxDeadline(newMax);
      // もし現在の期限が空、または旧最大値と同じなら新しい最大値に追従
      if (!deadline || deadline === maxDeadline || deadline > newMax) {
        setDeadline(newMax);
      }
    }
  };

  if (!isOpen) return null;

  // バリデーション
  const isOverdueMax = Boolean(deadline && maxDeadline && deadline > maxDeadline);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!overallGoal.trim()) {
      setErrorMsg('「全体支援目標」は必須です。');
      return;
    }
    if (!reviewDate) {
      setErrorMsg('「見直し基準日」は必須です。');
      return;
    }
    if (!deadline) {
      setErrorMsg('「次回見直し期限」は必須です。');
      return;
    }
    if (isOverdueMax) {
      setErrorMsg(`次回見直し期限は基準日（${reviewDate}）から暦上6か月（${maxDeadline}）以内である必要があります。`);
      return;
    }
    if (isReview && !reviewReason.trim()) {
      setErrorMsg('随時見直しを行う際は、「見直しの理由・契機」を必ず記録してください。');
      return;
    }

    try {
      setSubmitting(true);
      setErrorMsg(null);
      const res = await jobRetentionApi.createOrReviewSupportPlan(contractId, {
        overall_support_goal: overallGoal.trim(),
        review_date: reviewDate,
        start_date: reviewDate,
        review_reason: reviewReason.trim(),
        next_review_deadline: deadline,
      });

      onSaved(res.plan);
      onClose();
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.msg || '支援計画の登録・見直しに失敗しました。');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white w-full max-w-2xl rounded-2xl shadow-xl border border-slate-100 flex flex-col overflow-hidden my-6">
        {/* モーダルヘッダー */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-gradient-to-r from-indigo-50/50 to-white">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-indigo-100 text-indigo-700 rounded-xl">
              <Target className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-800 flex items-center gap-2">
                {isReview ? `就労定着支援計画の随時見直し（第${(activePlan?.version || 1) + 1}版作成）` : '就労定着支援計画の新規策定'}
              </h2>
              <p className="text-xs text-slate-500">
                対象者: <span className="font-semibold text-slate-700">{userName}</span>
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-all"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* フォーム本文 */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5 overflow-y-auto max-h-[75vh]">
          {errorMsg && (
            <div className="p-3.5 bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded-xl flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* 見直し時の現在目標参照 */}
          {isReview && activePlan && (
            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200/80 text-xs space-y-1.5">
              <div className="flex items-center justify-between text-slate-500 font-semibold text-[11px]">
                <span className="flex items-center gap-1">
                  <History className="w-3.5 h-3.5 text-slate-400" />
                  現在の計画（第{activePlan.version}版）
                </span>
                <span>見直し期限: {activePlan.next_review_deadline}</span>
              </div>
              <p className="text-slate-700 leading-relaxed font-medium">
                {activePlan.overall_support_goal}
              </p>
              <p className="text-[11px] text-slate-400">
                ※見直しが完了すると、第{activePlan.version}版は履歴（ARCHIVED）として保存され、新しい版がACTIVEになります。
              </p>
            </div>
          )}

          {/* 全体支援目標 */}
          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1.5">
              全体支援目標・支援方針 <span className="text-rose-500">*</span>
            </label>
            <p className="text-[11px] text-slate-400 mb-2">
              本人の就労定着に向けた大まかな中長期目標、自律的対処を促進するための方針を記載します。（初月の月次支援目標の初期提案値にも連動します）
            </p>
            <textarea
              value={overallGoal}
              onChange={(e) => setOverallGoal(e.target.value)}
              rows={4}
              placeholder="例: 体調・疲労の自力モニタリングを習慣化し、業務量増加時も自力で上司に報告・相談できる体制を構築する。"
              className="w-full p-3 text-xs rounded-xl border border-slate-200 focus:ring-2 focus:ring-indigo-500 leading-relaxed"
              required
            />
          </div>

          {/* 基準日 & 次回見直し期限 (6か月上限) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1.5">
                見直し基準日 <span className="text-rose-500">*</span>
              </label>
              <div className="relative">
                <input
                  type="date"
                  value={reviewDate}
                  onChange={(e) => handleReviewDateChange(e.target.value)}
                  className="w-full p-2.5 text-xs rounded-xl border border-slate-200 focus:ring-2 focus:ring-indigo-500"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1.5">
                次回見直し期限（上限: 基準日+6か月） <span className="text-rose-500">*</span>
              </label>
              <div className="relative">
                <input
                  type="date"
                  value={deadline}
                  max={maxDeadline}
                  onChange={(e) => setDeadline(e.target.value)}
                  className={`w-full p-2.5 text-xs rounded-xl border focus:ring-2 ${
                    isOverdueMax
                      ? 'border-rose-300 bg-rose-50/50 focus:ring-rose-500 text-rose-800'
                      : 'border-slate-200 focus:ring-2 focus:ring-indigo-500'
                  }`}
                  required
                />
              </div>
              <div className="mt-1 text-[11px] text-slate-400 flex items-center justify-between">
                <span>最大上限: {maxDeadline || '—'}</span>
                <button
                  type="button"
                  onClick={() => setDeadline(maxDeadline)}
                  className="text-indigo-600 hover:text-indigo-800 font-semibold"
                >
                  6か月後に設定
                </button>
              </div>
              {isOverdueMax && (
                <div className="mt-1 text-[11px] font-bold text-rose-600 flex items-center gap-1">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  上限（{maxDeadline}）を超過しています
                </div>
              )}
            </div>
          </div>

          {/* 見直しの理由・契機 */}
          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1.5">
              見直しの理由・契機 {isReview ? <span className="text-rose-500">* (随時見直し時は必須)</span> : <span className="text-slate-400 font-normal">(任意)</span>}
            </label>
            <p className="text-[11px] text-slate-400 mb-1.5">
              「業務量増加」「部署異動」「本人の体調改善」「定期見直し」など、計画を更新した背景を記録します。
            </p>
            <input
              type="text"
              value={reviewReason}
              onChange={(e) => setReviewReason(e.target.value)}
              placeholder={isReview ? "例: 担当業務の拡大に伴い、相談手順の再整理が必要となったため" : "例: 就労定着支援の開始に伴う初回策定"}
              className="w-full p-2.5 text-xs rounded-xl border border-slate-200 focus:ring-2 focus:ring-indigo-500"
              required={isReview}
            />
          </div>

          {/* フッターアクション */}
          <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
            <p className="text-[11px] text-slate-400">
              ※随時見直しはいつでも実施可能です。6か月は放置できる最大期間です。
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 bg-slate-100 hover:bg-slate-200 rounded-xl transition-all"
              >
                キャンセル
              </button>
              <button
                type="submit"
                disabled={submitting || isOverdueMax}
                className="px-5 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-sm flex items-center gap-1.5 transition-all disabled:opacity-50"
              >
                <Save className="w-4 h-4" />
                {submitting ? '保存中...' : isReview ? '見直しを確定する' : '計画を策定する'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
