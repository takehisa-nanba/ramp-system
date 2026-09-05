// frontend/src/pages/JobRetentionActionModal.tsx

import React, { useState, useEffect } from 'react';
import { jobRetentionApi } from '../services/jobRetentionApi';
import { X, Calendar, Building2, UserCheck, Shuffle, Save } from 'lucide-react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  contractId: number;
  userName: string;
  onSaved: () => void;
}

export const JobRetentionActionModal: React.FC<Props> = ({
  isOpen,
  onClose,
  contractId,
  userName,
  onSaved
}) => {
  const today = new Date().toISOString().split('T')[0];
  const [actionDate, setActionDate] = useState(today);

  // 複数支援種別フラグ
  const [hasUserInterview, setHasUserInterview] = useState(true);
  const [interviewMethod, setInterviewMethod] = useState<'FACE_TO_FACE' | 'ONLINE' | 'PHONE'>('FACE_TO_FACE');
  const [hasCompanyVisit, setHasCompanyVisit] = useState(true);
  const [hasCoordination, setHasCoordination] = useState(false);
  const [hasOtherSupport, setHasOtherSupport] = useState(false);

  // 内容
  const [confirmedSituation, setConfirmedSituation] = useState('');
  const [providedSupport, setProvidedSupport] = useState('');
  const [userActionObserved, setUserActionObserved] = useState('');
  const [staffInterventionBoundary, setStaffInterventionBoundary] = useState('');
  const [nextStep, setNextStep] = useState('');

  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // 入力途中のセッション一時保存
  const draftKey = `retention_action_draft_${contractId}`;

  useEffect(() => {
    if (isOpen) {
      const saved = sessionStorage.getItem(draftKey);
      if (saved) {
        try {
          const p = JSON.parse(saved);
          setActionDate(p.actionDate || today);
          setHasUserInterview(p.hasUserInterview ?? true);
          setInterviewMethod(p.interviewMethod || 'FACE_TO_FACE');
          setHasCompanyVisit(p.hasCompanyVisit ?? true);
          setHasCoordination(p.hasCoordination ?? false);
          setHasOtherSupport(p.hasOtherSupport ?? false);
          setConfirmedSituation(p.confirmedSituation || '');
          setProvidedSupport(p.providedSupport || '');
          setUserActionObserved(p.userActionObserved || '');
          setStaffInterventionBoundary(p.staffInterventionBoundary || '');
          setNextStep(p.nextStep || '');
        } catch (e) {
          console.error(e);
        }
      }
    }
  }, [isOpen, contractId]);

  useEffect(() => {
    if (!isOpen) return;
    const data = {
      actionDate,
      hasUserInterview,
      interviewMethod,
      hasCompanyVisit,
      hasCoordination,
      hasOtherSupport,
      confirmedSituation,
      providedSupport,
      userActionObserved,
      staffInterventionBoundary,
      nextStep
    };
    sessionStorage.setItem(draftKey, JSON.stringify(data));
  }, [isOpen, actionDate, hasUserInterview, interviewMethod, hasCompanyVisit, hasCoordination, hasOtherSupport, confirmedSituation, providedSupport, userActionObserved, staffInterventionBoundary, nextStep]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!confirmedSituation.trim() || !providedSupport.trim()) {
      setErrorMsg('「確認した状況」と「実際に行った支援」は必須です。');
      return;
    }

    try {
      setSubmitting(true);
      setErrorMsg(null);
      await jobRetentionApi.recordAction(contractId, {
        action_date: actionDate,
        has_user_interview: hasUserInterview,
        interview_method: hasUserInterview ? interviewMethod : undefined,
        has_company_visit: hasCompanyVisit,
        has_coordination: hasCoordination,
        has_other_support: hasOtherSupport,
        confirmed_situation: confirmedSituation,
        provided_support: providedSupport,
        user_action_observed: userActionObserved,
        staff_intervention_boundary: staffInterventionBoundary,
        next_step: nextStep
      });

      sessionStorage.removeItem(draftKey);
      onSaved();
      onClose();
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.msg || '保存に失敗しました。');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-white w-full max-w-2xl rounded-2xl shadow-xl overflow-hidden my-8">
        {/* ヘッダー */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
          <div>
            <h2 className="text-base font-bold text-slate-800">
              支援実施記録の登録
            </h2>
            <p className="text-xs text-slate-500">対象利用者: <span className="font-semibold text-slate-700">{userName}</span></p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100">
            <X className="w-5 h-5" />
          </button>
        </div>

        {errorMsg && (
          <div className="mx-6 mt-4 p-3 bg-rose-50 border border-rose-200 text-rose-750 text-xs rounded-xl">
            {errorMsg}
          </div>
        )}

        {/* フォーム */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4 text-sm">
          {/* 日付 */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1 flex items-center gap-1.5">
              <Calendar className="w-4 h-4 text-indigo-600" />
              実施日
            </label>
            <input
              type="date"
              value={actionDate}
              onChange={(e) => setActionDate(e.target.value)}
              className="w-full px-3 py-2 border border-slate-200 rounded-xl text-xs focus:ring-2 focus:ring-indigo-500"
              required
            />
          </div>

          {/* 実施種別（複数選択可能） */}
          <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
            <span className="block text-xs font-semibold text-slate-700 mb-2">
              実施した支援内容（複数該当する場合はすべて選択）
            </span>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
              <label className="flex items-center gap-2 p-2 bg-white rounded-lg border border-slate-200 cursor-pointer hover:border-indigo-300 text-xs">
                <input
                  type="checkbox"
                  checked={hasCompanyVisit}
                  onChange={(e) => setHasCompanyVisit(e.target.checked)}
                  className="rounded text-indigo-600"
                />
                <Building2 className="w-4 h-4 text-indigo-600" />
                <span>企業訪問・職場観察</span>
              </label>

              <label className="flex items-center gap-2 p-2 bg-white rounded-lg border border-slate-200 cursor-pointer hover:border-indigo-300 text-xs">
                <input
                  type="checkbox"
                  checked={hasUserInterview}
                  onChange={(e) => setHasUserInterview(e.target.checked)}
                  className="rounded text-indigo-600"
                />
                <UserCheck className="w-4 h-4 text-emerald-600" />
                <span>本人面談</span>
              </label>

              <label className="flex items-center gap-2 p-2 bg-white rounded-lg border border-slate-200 cursor-pointer hover:border-indigo-300 text-xs">
                <input
                  type="checkbox"
                  checked={hasCoordination}
                  onChange={(e) => setHasCoordination(e.target.checked)}
                  className="rounded text-indigo-600"
                />
                <Shuffle className="w-4 h-4 text-amber-600" />
                <span>関係機関・企業調整</span>
              </label>
            </div>

            {hasUserInterview && (
              <div className="mt-3 pt-3 border-t border-slate-200/60 flex items-center gap-3">
                <span className="text-xs text-slate-600 font-medium">面談方法:</span>
                <div className="flex gap-2 text-xs">
                  <label className="flex items-center gap-1 cursor-pointer">
                    <input
                      type="radio"
                      name="interview_method"
                      value="FACE_TO_FACE"
                      checked={interviewMethod === 'FACE_TO_FACE'}
                      onChange={() => setInterviewMethod('FACE_TO_FACE')}
                    />
                    <span>対面</span>
                  </label>
                  <label className="flex items-center gap-1 cursor-pointer">
                    <input
                      type="radio"
                      name="interview_method"
                      value="ONLINE"
                      checked={interviewMethod === 'ONLINE'}
                      onChange={() => setInterviewMethod('ONLINE')}
                    />
                    <span>オンライン</span>
                  </label>
                  <label className="flex items-center gap-1 cursor-pointer">
                    <input
                      type="radio"
                      name="interview_method"
                      value="PHONE"
                      checked={interviewMethod === 'PHONE'}
                      onChange={() => setInterviewMethod('PHONE')}
                    />
                    <span>電話</span>
                  </label>
                </div>
              </div>
            )}
          </div>

          {/* 現場の一次情報 */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              確認した状況（面談・訪問で把握した就労・生活の様子） <span className="text-rose-500">*</span>
            </label>
            <textarea
              value={confirmedSituation}
              onChange={(e) => setConfirmedSituation(e.target.value)}
              placeholder="例: 上司より業務指示の理解が進んでいるとの評価。本人も体調安定と回答。"
              rows={2}
              className="w-full px-3 py-2 border border-slate-200 rounded-xl text-xs focus:ring-2 focus:ring-indigo-500 resize-none"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              実際に行った支援・調整内容 <span className="text-rose-500">*</span>
            </label>
            <textarea
              value={providedSupport}
              onChange={(e) => setProvidedSupport(e.target.value)}
              placeholder="例: 来月の繁忙期に向け、休憩の取り方について上司と本人とでルールを合意した。"
              rows={2}
              className="w-full px-3 py-2 border border-slate-200 rounded-xl text-xs focus:ring-2 focus:ring-indigo-500 resize-none"
              required
            />
          </div>

          {/* 対処力・介在境界（客観的事実） */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 bg-indigo-50/40 p-3.5 rounded-xl border border-indigo-100">
            <div>
              <label className="block text-[11px] font-semibold text-indigo-900 mb-1">
                本人がどこまで自分で対処したか
              </label>
              <textarea
                value={userActionObserved}
                onChange={(e) => setUserActionObserved(e.target.value)}
                placeholder="例: 疲労感を事前に自覚し、自分から上司に報告できていた。"
                rows={2}
                className="w-full px-2.5 py-1.5 border border-indigo-200 rounded-lg text-xs focus:ring-2 focus:ring-indigo-500 resize-none bg-white"
              />
            </div>
            <div>
              <label className="block text-[11px] font-semibold text-indigo-900 mb-1">
                支援員がどこから介在したか
              </label>
              <textarea
                value={staffInterventionBoundary}
                onChange={(e) => setStaffInterventionBoundary(e.target.value)}
                placeholder="例: 双方のニュアンスの橋渡しのみ介入し、具体的な合意は本人に任せた。"
                rows={2}
                className="w-full px-2.5 py-1.5 border border-indigo-200 rounded-lg text-xs focus:ring-2 focus:ring-indigo-500 resize-none bg-white"
              />
            </div>
          </div>

          {/* 次回予定 */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              次回予定・確認事項
            </label>
            <input
              type="text"
              value={nextStep}
              onChange={(e) => setNextStep(e.target.value)}
              placeholder="例: 2週間後に電話で体調のフォローを実施する。"
              className="w-full px-3 py-2 border border-slate-200 rounded-xl text-xs focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {/* フッター */}
          <div className="pt-3 border-t border-slate-100 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-xl transition-all"
            >
              キャンセル
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-5 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-sm flex items-center gap-1.5 disabled:opacity-50 transition-all"
            >
              <Save className="w-4 h-4" />
              {submitting ? '保存中...' : '記録を保存'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
