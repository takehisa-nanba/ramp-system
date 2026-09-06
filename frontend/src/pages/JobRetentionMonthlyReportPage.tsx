import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { jobRetentionApi } from '../services/jobRetentionApi';
import type { RetentionContract, MonthlyRetentionReportData, SupportPlan } from '../services/jobRetentionApi';
import { RetentionPlanBanner } from '../components/retention/RetentionPlanBanner';
import { RetentionPlanReviewModal } from '../components/retention/RetentionPlanReviewModal';
import { FileText, Save, CheckCircle2, ArrowLeft, Calendar, Sparkles, AlertCircle, Target, ArrowRight, ShieldCheck } from 'lucide-react';

export const JobRetentionMonthlyReportPage: React.FC = () => {
  const { contractId } = useParams<{ contractId: string }>();
  const navigate = useNavigate();

  const now = new Date();
  const defaultYearMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  const [yearMonth, setYearMonth] = useState(defaultYearMonth);

  const [contract, setContract] = useState<RetentionContract | null>(null);
  const [reportData, setReportData] = useState<MonthlyRetentionReportData | null>(null);
  const [activePlan, setActivePlan] = useState<SupportPlan | null>(null);
  const [historyPlans, setHistoryPlans] = useState<SupportPlan[]>([]);
  const [isReviewModalOpen, setIsReviewModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const cid = contractId ? parseInt(contractId, 10) : 0;

  useEffect(() => {
    if (!cid) return;
    loadData();
  }, [cid, yearMonth]);

  const loadData = async () => {
    try {
      setLoading(true);
      setErrorMsg(null);
      const [c, preview, planRes, plans] = await Promise.all([
        jobRetentionApi.getContract(cid),
        jobRetentionApi.previewMonthlyReport(cid, yearMonth),
        jobRetentionApi.getActiveSupportPlan(cid),
        jobRetentionApi.listSupportPlans(cid).catch(() => []),
      ]);
      setContract(c);
      setReportData(preview);
      setActivePlan(planRes.plan);
      setHistoryPlans(plans);
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.msg || 'レポートデータの取得に失敗しました。');
    } finally {
      setLoading(false);
    }
  };

  const handleFieldChange = (field: keyof MonthlyRetentionReportData, value: string) => {
    if (!reportData) return;
    setReportData({
      ...reportData,
      [field]: value
    });
  };

  const handleSave = async (finalize = false) => {
    if (!reportData || !cid) return;

    try {
      setSaving(true);
      setErrorMsg(null);
      const res = await jobRetentionApi.saveMonthlyReport(cid, yearMonth, reportData, finalize);
      setSuccessMsg(res.msg);
      setReportData({
        ...reportData,
        status: finalize ? 'FINALIZED' : 'DRAFT'
      });
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.msg || 'レポートの保存に失敗しました。');
    } finally {
      setSaving(false);
    }
  };

  if (loading && !reportData) {
    return (
      <div className="flex justify-center items-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      {/* 戻るボタン & タイトル */}
      <div className="mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <button
            onClick={() => navigate(-1)}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800 mb-2"
          >
            <ArrowLeft className="w-4 h-4" /> 定着支援管理に戻る
          </button>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-slate-800 flex items-center gap-2">
              <FileText className="w-6 h-6 text-indigo-600" />
              就労定着支援状況報告書（支援レポート）
            </h1>
            {reportData?.status === 'FINALIZED' ? (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800">
                確定済み
              </span>
            ) : (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-800">
                下書き
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            利用者: <span className="font-semibold text-slate-700">{contract?.user_name}</span> |
            一次情報から公式レポートの各項目へ自動マッピングされています。必要に応じて補足・調整してください。
          </p>
        </div>

        {/* 対象月選択 */}
        <div className="flex items-center gap-2 bg-white px-3 py-2 rounded-xl border border-slate-200 shadow-sm">
          <Calendar className="w-4 h-4 text-indigo-600" />
          <input
            type="month"
            value={yearMonth}
            onChange={(e) => setYearMonth(e.target.value)}
            className="text-xs font-semibold text-slate-700 focus:outline-none"
          />
        </div>
      </div>

      {/* 支援計画（全体目標 & 見直し期限）常時表示バナー */}
      <div className="mb-6">
        <RetentionPlanBanner
          plan={activePlan}
          onOpenReviewModal={() => setIsReviewModalOpen(true)}
          historyPlans={historyPlans}
          onLoadHistory={async () => {
            const plans = await jobRetentionApi.listSupportPlans(cid);
            setHistoryPlans(plans);
          }}
        />
      </div>

      {successMsg && (
        <div className="mb-4 p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {errorMsg && (
        <div className="mb-4 p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* 公式帳票 標準項目セクション */}
      {reportData && (
        <div className="mb-6 bg-white p-6 rounded-2xl shadow-sm border border-slate-200 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h2 className="text-sm font-bold text-slate-800 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-indigo-600" />
              就労定着支援状況報告書 公式必須項目
            </h2>
            <span className="text-[11px] text-slate-400">
              ※当月目標は前月確定値または全体目標から初期提案（編集可能）
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* 当月の主な支援目標 */}
            <div className="space-y-1 md:col-span-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                  <Target className="w-3.5 h-3.5 text-indigo-600" />
                  当月の主な支援目標（初期提案値・編集可能）
                </label>
                {reportData.support_goal ? (
                  <span className="text-[11px] text-indigo-600 font-semibold">目標設定済み</span>
                ) : (
                  <span className="text-[11px] text-slate-400">未入力</span>
                )}
              </div>
              <textarea
                value={reportData.support_goal || ''}
                onChange={(e) => handleFieldChange('support_goal', e.target.value)}
                rows={2}
                placeholder="初月は全体計画の目標から、通常月は前月確定レポートの今後の支援内容から提案されます。"
                className="w-full p-3 text-xs rounded-xl border border-indigo-200 bg-indigo-50/20 focus:bg-white focus:ring-2 focus:ring-indigo-500 leading-relaxed font-medium"
              />
            </div>

            {/* 支援内容 */}
            <div className="space-y-1">
              <label className="text-xs font-bold text-slate-700 block">
                当月実施した支援内容（公式記載用）
              </label>
              <textarea
                value={reportData.support_content || ''}
                onChange={(e) => handleFieldChange('support_content', e.target.value)}
                rows={3}
                placeholder="本人への定期面談、職場訪問等の具体的な支援内容"
                className="w-full p-3 text-xs rounded-xl border border-slate-200 focus:ring-2 focus:ring-indigo-500 leading-relaxed"
              />
            </div>

            {/* 支援結果 */}
            <div className="space-y-1">
              <label className="text-xs font-bold text-slate-700 block">
                支援結果・本人の状況変化（公式記載用）
              </label>
              <textarea
                value={reportData.support_result || ''}
                onChange={(e) => handleFieldChange('support_result', e.target.value)}
                rows={3}
                placeholder="支援の結果確認された状況、本人の安定度・変化"
                className="w-full p-3 text-xs rounded-xl border border-slate-200 focus:ring-2 focus:ring-indigo-500 leading-relaxed"
              />
            </div>

            {/* 今後の支援内容（翌月引き継ぎ） */}
            <div className="space-y-1 md:col-span-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                  <ArrowRight className="w-3.5 h-3.5 text-indigo-600" />
                  今後の支援内容（確定後、翌月の「当月の主な支援目標」に自動引き継ぎ）
                </label>
              </div>
              <textarea
                value={reportData.future_support_plan || ''}
                onChange={(e) => handleFieldChange('future_support_plan', e.target.value)}
                rows={2}
                placeholder="次月に向けて継続・強化する支援方針（確定すると次月の当月目標に引き継がれます）"
                className="w-full p-3 text-xs rounded-xl border border-emerald-200 bg-emerald-50/20 focus:bg-white focus:ring-2 focus:ring-emerald-500 leading-relaxed font-medium"
              />
            </div>

            {/* 対象者・事業主・関係機関等の取組 */}
            <div className="space-y-1">
              <label className="text-xs font-bold text-slate-700 block">
                対象者・事業主・関係機関等の取組
              </label>
              <textarea
                value={reportData.stakeholder_efforts || ''}
                onChange={(e) => handleFieldChange('stakeholder_efforts', e.target.value)}
                rows={2}
                placeholder="本人・事業主・医療機関・地域障害者職業センター等の取組状況"
                className="w-full p-3 text-xs rounded-xl border border-slate-200 focus:ring-2 focus:ring-indigo-500 leading-relaxed"
              />
            </div>

            {/* 共有事項 */}
            <div className="space-y-1">
              <label className="text-xs font-bold text-slate-700 block">
                共有事項
              </label>
              <textarea
                value={reportData.sharing_notes || ''}
                onChange={(e) => handleFieldChange('sharing_notes', e.target.value)}
                rows={2}
                placeholder="関係者間で共有すべき留意事項・確認結果"
                className="w-full p-3 text-xs rounded-xl border border-slate-200 focus:ring-2 focus:ring-indigo-500 leading-relaxed"
              />
            </div>
          </div>
        </div>
      )}

      {/* 自動生成ヒント */}
      <div className="mb-6 p-4 rounded-2xl bg-indigo-50/70 border border-indigo-100 flex items-start gap-3">
        <Sparkles className="w-5 h-5 text-indigo-600 shrink-0 mt-0.5" />
        <div className="text-xs text-indigo-950 leading-relaxed">
          <span className="font-semibold block mb-0.5">一次情報からの自動マッピング仕様</span>
          本月中の本人面談・企業訪問記録、本人の生の声、企業からのフィードバックを元に各項目が自動抽出されています。
          一次情報そのものは不変のまま保持され、ここでの編集は報告書出力用として保存されます。
        </div>
      </div>

      {/* 詳細記録・一次情報整理項目フォーム */}
      {reportData && (
        <div className="space-y-5">
          <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">
            日々の記録からの抽出・整理項目
          </div>
          {/* 1. 面談実施状況 & 企業訪問状況 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-100">
              <label className="block text-xs font-bold text-slate-800 mb-1">
                1. 本人面談実施状況（実施日・方法・時間等）
              </label>
              <textarea
                value={reportData.interview_records || ''}
                onChange={(e) => handleFieldChange('interview_records', e.target.value)}
                rows={3}
                className="w-full p-3 text-xs rounded-xl border border-slate-200 focus:ring-2 focus:ring-indigo-500 font-mono leading-relaxed"
              />
            </div>

            <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-100">
              <label className="block text-xs font-bold text-slate-800 mb-1">
                2. 企業訪問・職場状況把握（実施日・対応者等）
              </label>
              <textarea
                value={reportData.company_visit_records || ''}
                onChange={(e) => handleFieldChange('company_visit_records', e.target.value)}
                rows={3}
                className="w-full p-3 text-xs rounded-xl border border-slate-200 focus:ring-2 focus:ring-indigo-500 font-mono leading-relaxed"
              />
            </div>
          </div>

          {/* 2. 就労状況 & 生活状況 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-100">
              <label className="block text-xs font-bold text-slate-800 mb-1">
                3. 就労状況（勤務時間・出勤状況、業務内容・環境の変化）
              </label>
              <textarea
                value={reportData.work_status_summary || ''}
                onChange={(e) => handleFieldChange('work_status_summary', e.target.value)}
                rows={4}
                className="w-full p-3 text-xs rounded-xl border border-slate-200 focus:ring-2 focus:ring-indigo-500 leading-relaxed"
              />
            </div>

            <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-100">
              <label className="block text-xs font-bold text-slate-800 mb-1">
                4. 生活状況（生活リズム、健康管理、金銭管理等）
              </label>
              <textarea
                value={reportData.life_status_summary || ''}
                onChange={(e) => handleFieldChange('life_status_summary', e.target.value)}
                rows={4}
                className="w-full p-3 text-xs rounded-xl border border-slate-200 focus:ring-2 focus:ring-indigo-500 leading-relaxed"
              />
            </div>
          </div>

          {/* 3. 本人の状況・自力対処 & 企業の評価 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-100">
              <label className="block text-xs font-bold text-slate-800 mb-1">
                5. 本人の状況・自力対処の状況・本人の意向
              </label>
              <textarea
                value={reportData.user_coping_summary || ''}
                onChange={(e) => handleFieldChange('user_coping_summary', e.target.value)}
                rows={4}
                className="w-full p-3 text-xs rounded-xl border border-slate-200 focus:ring-2 focus:ring-indigo-500 leading-relaxed"
              />
            </div>

            <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-100">
              <label className="block text-xs font-bold text-slate-800 mb-1">
                6. 企業の状況・職場での様子・要望（企業連携時）
              </label>
              <textarea
                value={reportData.employer_feedback_summary || ''}
                onChange={(e) => handleFieldChange('employer_feedback_summary', e.target.value)}
                rows={4}
                className="w-full p-3 text-xs rounded-xl border border-slate-200 focus:ring-2 focus:ring-indigo-500 leading-relaxed"
              />
            </div>
          </div>

          {/* 4. 実施した支援内容 & 今後の支援方針 */}
          <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-100">
            <label className="block text-xs font-bold text-slate-800 mb-1">
              7. 当月実施した支援・調整内容（支援員の介在範囲等）
            </label>
            <textarea
              value={reportData.support_details || ''}
              onChange={(e) => handleFieldChange('support_details', e.target.value)}
              rows={3}
              className="w-full p-3 text-xs rounded-xl border border-slate-200 focus:ring-2 focus:ring-indigo-500 leading-relaxed mb-4"
            />

            <label className="block text-xs font-bold text-slate-800 mb-1">
              8. 今後の支援方針・次回課題（本人の自律的対処の促進方針）
            </label>
            <textarea
              value={reportData.future_support_policy || ''}
              onChange={(e) => handleFieldChange('future_support_policy', e.target.value)}
              rows={3}
              className="w-full p-3 text-xs rounded-xl border border-slate-200 focus:ring-2 focus:ring-indigo-500 leading-relaxed"
            />
          </div>

          {/* アクションバー */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-200">
            <button
              onClick={() => handleSave(false)}
              disabled={saving}
              className="px-5 py-2.5 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 rounded-xl shadow-sm transition-all disabled:opacity-50"
            >
              {saving ? '保存中...' : '下書き保存'}
            </button>
            <button
              onClick={() => handleSave(true)}
              disabled={saving}
              className="px-6 py-2.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-sm flex items-center gap-1.5 transition-all disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              {saving ? '処理中...' : 'レポートを確定する'}
            </button>
          </div>
        </div>
      )}

      {/* 計画見直し・新規作成モーダル */}
      {isReviewModalOpen && cid > 0 && (
        <RetentionPlanReviewModal
          isOpen={isReviewModalOpen}
          onClose={() => setIsReviewModalOpen(false)}
          contractId={cid}
          userName={contract?.user_name || ''}
          activePlan={activePlan}
          onSaved={(_newPlan) => {
            loadData();
          }}
        />
      )}
    </div>
  );
};

export default JobRetentionMonthlyReportPage;
