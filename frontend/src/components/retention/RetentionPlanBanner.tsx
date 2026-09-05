// frontend/src/components/retention/RetentionPlanBanner.tsx

import React, { useState } from 'react';
import type { SupportPlan, SupportPlanSummary, DeadlineStatusCode } from '../../services/jobRetentionApi';
import { Target, Calendar, AlertTriangle, AlertCircle, Clock, CheckCircle2, History, ChevronDown, ChevronUp, Plus, Edit3 } from 'lucide-react';

interface Props {
  plan?: SupportPlanSummary | SupportPlan | null;
  onOpenReviewModal: () => void;
  historyPlans?: SupportPlan[];
  onLoadHistory?: () => void;
  compact?: boolean;
}

export const RetentionPlanBanner: React.FC<Props> = ({
  plan,
  onOpenReviewModal,
  historyPlans,
  onLoadHistory,
  compact = false,
}) => {
  const [showHistory, setShowHistory] = useState(false);

  const getStatusBadge = (status: DeadlineStatusCode, daysDiff: number) => {
    switch (status) {
      case 'NORMAL':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            見直し期限まで あと{daysDiff}日
          </span>
        );
      case 'APPROACHING':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-300 animate-pulse">
            <Clock className="w-3.5 h-3.5 text-amber-600" />
            見直し期限間近（あと{daysDiff}日）
          </span>
        );
      case 'DUE_TODAY':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-orange-100 text-orange-900 border border-orange-400">
            <AlertCircle className="w-3.5 h-3.5 text-orange-600" />
            本日が見直し期限です
          </span>
        );
      case 'OVERDUE_WITHIN_MONTH':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-50 text-rose-800 border border-rose-300">
            <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
            期限超過（{Math.abs(daysDiff)}日超過・当月中見直し要）
          </span>
        );
      case 'OVERDUE_BILLING_RISK':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-red-600 text-white border border-red-700 shadow-sm">
            <AlertTriangle className="w-3.5 h-3.5 text-white" />
            見直し期限大幅超過（請求リスク・要見直し）
          </span>
        );
      default:
        return null;
    }
  };

  // 未作成時
  if (!plan) {
    return (
      <div className={`p-4 rounded-2xl border bg-amber-50/60 border-amber-200 ${compact ? 'text-xs' : ''}`}>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-start gap-2.5">
            <div className="p-1.5 bg-amber-100 text-amber-800 rounded-lg shrink-0 mt-0.5">
              <AlertCircle className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 rounded-md text-[11px] font-bold bg-amber-200 text-amber-900">
                  支援計画未作成
                </span>
                <span className="text-xs text-amber-900 font-semibold">
                  有効な就労定着支援計画が登録されていません
                </span>
              </div>
              <p className="text-xs text-amber-800/80 mt-1">
                本人の生の声や支援記録の登録は継続できますが、支援方針を明確にするため支援計画を作成してください。
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onOpenReviewModal}
            className="px-3.5 py-2 bg-amber-700 hover:bg-amber-800 text-white text-xs font-bold rounded-xl shadow-sm flex items-center justify-center gap-1.5 transition-all self-start sm:self-auto shrink-0"
          >
            <Plus className="w-3.5 h-3.5" />
            計画を作成する
          </button>
        </div>
      </div>
    );
  }

  // 作成済み・常時表示
  const handleToggleHistory = () => {
    if (!showHistory && onLoadHistory) {
      onLoadHistory();
    }
    setShowHistory(!showHistory);
  };

  return (
    <div className={`rounded-2xl border transition-all ${
      plan.deadline_status === 'OVERDUE_BILLING_RISK'
        ? 'bg-rose-50/70 border-rose-300'
        : plan.deadline_status === 'OVERDUE_WITHIN_MONTH'
        ? 'bg-orange-50/70 border-orange-300'
        : plan.deadline_status === 'APPROACHING' || plan.deadline_status === 'DUE_TODAY'
        ? 'bg-amber-50/70 border-amber-300'
        : 'bg-indigo-50/50 border-indigo-100'
    } p-4`}>
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="space-y-1.5 flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-bold bg-indigo-100 text-indigo-800">
              <Target className="w-3 h-3 text-indigo-600" />
              支援計画 第{plan.version}版
            </span>
            {getStatusBadge(plan.deadline_status, plan.days_diff)}
            <span className="text-xs text-slate-500 flex items-center gap-1">
              <Calendar className="w-3.5 h-3.5 text-slate-400" />
              次回見直し期限: <strong className="text-slate-700">{plan.next_review_deadline}</strong>
              <span className="text-[11px] text-slate-400">(暦上6か月上限)</span>
            </span>
          </div>

          <div className="text-slate-800 font-medium text-xs sm:text-sm bg-white/80 p-2.5 rounded-xl border border-slate-200/60 leading-relaxed">
            <span className="text-[11px] font-bold text-indigo-600 mr-2 block sm:inline">現在の支援目標・方針:</span>
            {plan.overall_support_goal}
          </div>

          {plan.review_reason && (
            <div className="text-[11px] text-slate-500">
              見直し契機: <span className="text-slate-700">{plan.review_reason}</span>
              {plan.review_date && <span>（{plan.review_date}）</span>}
            </div>
          )}
        </div>

        <div className="flex items-center gap-2 self-start md:self-center shrink-0">
          {onLoadHistory && (
            <button
              type="button"
              onClick={handleToggleHistory}
              className="px-2.5 py-1.5 text-xs text-slate-600 hover:text-slate-900 bg-white/80 hover:bg-white border border-slate-200 rounded-xl flex items-center gap-1 transition-all"
            >
              <History className="w-3.5 h-3.5 text-slate-500" />
              履歴
              {showHistory ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>
          )}

          <button
            type="button"
            onClick={onOpenReviewModal}
            className="px-3.5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl shadow-sm flex items-center gap-1.5 transition-all"
          >
            <Edit3 className="w-3.5 h-3.5" />
            計画を見直す
          </button>
        </div>
      </div>

      {/* 過去版履歴アコーディオン */}
      {showHistory && historyPlans && (
        <div className="mt-3 pt-3 border-t border-slate-200/70 space-y-2">
          <span className="text-[11px] font-bold text-slate-500 block">過去の支援計画（版履歴）</span>
          {historyPlans.length <= 1 ? (
            <div className="text-xs text-slate-400 py-1">過去の版はありません（初版のみ）。</div>
          ) : (
            historyPlans.filter(p => p.id !== plan.id).map(p => (
              <div key={p.id} className="p-2.5 bg-white rounded-xl text-xs border border-slate-100 space-y-1">
                <div className="flex justify-between items-center text-[11px] text-slate-400">
                  <span className="font-bold text-slate-600">第{p.version}版 (ARCHIVED)</span>
                  <span>見直し日: {p.review_date || p.start_date}</span>
                </div>
                <p className="text-slate-700">{p.overall_support_goal}</p>
                {p.review_reason && (
                  <p className="text-[11px] text-slate-500">契機: {p.review_reason}</p>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};
