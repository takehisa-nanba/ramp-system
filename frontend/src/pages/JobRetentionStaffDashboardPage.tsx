// frontend/src/pages/JobRetentionStaffDashboardPage.tsx

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { jobRetentionApi } from '../services/jobRetentionApi';
import type { RetentionContract, UserVoiceLog, SupportPlan, SupportPlanSummary } from '../services/jobRetentionApi';
import { JobRetentionActionModal } from './JobRetentionActionModal';
import { RetentionPlanBanner } from '../components/retention/RetentionPlanBanner';
import { RetentionPlanReviewModal } from '../components/retention/RetentionPlanReviewModal';
import { 
  Building2, Plus, MessageSquare, FileText, 
  Calendar, AlertCircle, ChevronDown, ChevronUp, UserCheck
} from 'lucide-react';
import { getLocalDateString } from '../utils/dateUtils';

export const JobRetentionStaffDashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [contracts, setContracts] = useState<RetentionContract[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // 支援記録モーダル
  const [activeModalContract, setActiveModalContract] = useState<{ id: number; name: string } | null>(null);

  // 支援計画見直し・作成モーダル
  const [reviewModalContract, setReviewModalContract] = useState<{
    id: number;
    name: string;
    activePlan?: SupportPlanSummary | null;
  } | null>(null);

  // 支援計画の過去版履歴
  const [historyMap, setHistoryMap] = useState<{ [contractId: number]: SupportPlan[] }>({});

  // 本人の声展開状態
  const [expandedVoices, setExpandedVoices] = useState<{ [contractId: number]: UserVoiceLog[] }>({});
  const [loadingVoiceId, setLoadingVoiceId] = useState<number | null>(null);

  // 新規登録モーダル
  const [isNewContractOpen, setIsNewContractOpen] = useState(false);
  const [newUserId, setNewUserId] = useState('');
  const [newWorkplace, setNewWorkplace] = useState('');
  const [newJobTitle, setNewJobTitle] = useState('');
  const [newStartDate, setNewStartDate] = useState(getLocalDateString());
  const [isCompanyInvolved, setIsCompanyInvolved] = useState(true);
  const [creatingContract, setCreatingContract] = useState(false);

  useEffect(() => {
    loadContracts();
  }, []);

  const loadContracts = async () => {
    try {
      setLoading(true);
      const list = await jobRetentionApi.listContracts();
      setContracts(list);
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.msg || '契約一覧の取得に失敗しました。');
    } finally {
      setLoading(false);
    }
  };

  const loadHistory = async (contractId: number) => {
    try {
      const plans = await jobRetentionApi.listSupportPlans(contractId);
      setHistoryMap(prev => ({ ...prev, [contractId]: plans }));
    } catch (err) {
      console.error('Failed to load plan history', err);
    }
  };

  const toggleVoices = async (contractId: number) => {
    if (expandedVoices[contractId]) {
      const next = { ...expandedVoices };
      delete next[contractId];
      setExpandedVoices(next);
      return;
    }

    try {
      setLoadingVoiceId(contractId);
      const voices = await jobRetentionApi.listVoices(contractId);
      setExpandedVoices(prev => ({ ...prev, [contractId]: voices }));
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingVoiceId(null);
    }
  };

  const handleCreateContract = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUserId || !newWorkplace || !newStartDate) return;

    try {
      setCreatingContract(true);
      const [y, m, d] = newStartDate.split('-').map(Number);
      const endD = new Date(y + 3, m - 1, d);
      const endStr = getLocalDateString(endD);

      await jobRetentionApi.createContract({
        user_id: parseInt(newUserId, 10),
        contract_start_date: newStartDate,
        contract_end_date: endStr,
        workplace_name: newWorkplace,
        job_title: newJobTitle,
        is_company_involved: isCompanyInvolved
      });

      setIsNewContractOpen(false);
      setNewUserId('');
      setNewWorkplace('');
      setNewJobTitle('');
      loadContracts();
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.msg || '新規定着支援契約の作成に失敗しました。');
    } finally {
      setCreatingContract(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* ページヘッダー */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 mb-1">
            独立業務ドメイン
          </span>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <Building2 className="w-7 h-7 text-indigo-600" />
            就労定着支援 管理ダッシュボード
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            本人の生の声を起点とし、面談・企業訪問の実施から月次支援レポートの自動生成までをシームレスに行えます。
          </p>
        </div>

        <button
          onClick={() => setIsNewContractOpen(true)}
          className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl shadow-sm flex items-center gap-1.5 transition-all self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          新規定着支援を開始
        </button>
      </div>

      {errorMsg && (
        <div className="mb-6 p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* 契約カード一覧 */}
      {loading ? (
        <div className="flex justify-center items-center min-h-[40vh]">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600"></div>
        </div>
      ) : contracts.length === 0 ? (
        <div className="bg-white rounded-2xl p-12 text-center text-slate-500 border border-slate-100 shadow-sm">
          現在進行中の就労定着支援はありません。「新規定着支援を開始」から登録してください。
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {contracts.map((c) => (
            <div key={c.id} className="bg-white rounded-2xl p-5 shadow-sm border border-slate-100 hover:border-indigo-100 transition-all">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-100">
                <div>
                  <div className="flex items-center gap-2.5 mb-1">
                    <span className="text-base font-bold text-slate-800">{c.user_name}</span>
                    {c.status === 'ACTIVE' && (
                      <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-700">
                        支援中
                      </span>
                    )}
                    {c.status === 'TRANSITION_PENDING' && (
                      <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-amber-50 text-amber-700">
                        転職移行期間
                      </span>
                    )}
                    {c.is_company_involved && (
                      <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-blue-50 text-blue-700">
                        企業連携あり
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-slate-500 flex flex-wrap items-center gap-x-4 gap-y-1">
                    <span className="flex items-center gap-1">
                      <Building2 className="w-3.5 h-3.5 text-slate-400" />
                      勤務先: <strong className="text-slate-700 font-semibold">{c.latest_workplace || '未登録'}</strong> ({c.latest_job_title || '一般職'})
                    </span>
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5 text-slate-400" />
                      契約期間: {c.contract_start_date} 〜 {c.contract_end_date}
                    </span>
                  </div>
                </div>

                {/* アクションボタン */}
                <div className="flex items-center gap-2 flex-wrap">
                  {c.current_month_report_status && (
                    <button
                      onClick={() => navigate(`/job-retention/${c.id}/reports`)}
                      className={`px-2.5 py-1.5 rounded-xl text-xs font-semibold border flex items-center gap-1 transition-all ${
                        c.current_month_report_status === 'FINALIZED'
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100'
                          : c.current_month_report_status === 'DRAFT'
                          ? 'bg-amber-50 text-amber-700 border-amber-200 hover:bg-amber-100'
                          : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                      }`}
                      title="支援レポート一覧を開く"
                    >
                      <FileText className="w-3.5 h-3.5" />
                      今月: {
                        c.current_month_report_status === 'FINALIZED' ? '確定済み' :
                        c.current_month_report_status === 'DRAFT' ? '下書き' : '未作成'
                      }
                    </button>
                  )}

                  <button
                    onClick={() => setActiveModalContract({ id: c.id, name: c.user_name })}
                    className="px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-semibold rounded-xl flex items-center gap-1.5 transition-all"
                  >
                    <UserCheck className="w-3.5 h-3.5" />
                    支援記録を登録
                  </button>

                  <button
                    onClick={() => navigate(`/job-retention/${c.id}/reports`)}
                    className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl shadow-sm flex items-center gap-1.5 transition-all"
                  >
                    <FileText className="w-3.5 h-3.5" />
                    支援レポート
                  </button>
                </div>
              </div>

              {/* 支援計画（全体目標 & 見直し期限 & 期限状態）常時表示バナー */}
              <div className="py-3">
                <RetentionPlanBanner
                  plan={c.active_plan}
                  onOpenReviewModal={() => setReviewModalContract({ id: c.id, name: c.user_name, activePlan: c.active_plan })}
                  historyPlans={historyMap[c.id]}
                  onLoadHistory={() => loadHistory(c.id)}
                />
              </div>

              {/* フッター情報 & 声のアコーディオン */}
              <div className="pt-3 flex items-center justify-between text-xs text-slate-500">
                <div className="flex items-center gap-4">
                  <span>累計支援記録: <strong className="text-slate-700">{c.action_count || 0}件</strong></span>
                  <span>本人の声投稿: <strong className="text-slate-700">{c.voice_count || 0}件</strong></span>
                </div>

                <button
                  onClick={() => toggleVoices(c.id)}
                  className="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-800"
                >
                  <MessageSquare className="w-3.5 h-3.5" />
                  本人の声を確認 {expandedVoices[c.id] ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </button>
              </div>

              {/* 展開された本人の声一覧 */}
              {loadingVoiceId === c.id && (
                <div className="mt-3 p-4 bg-slate-50 rounded-xl text-center text-xs text-slate-400">
                  読み込み中...
                </div>
              )}

              {expandedVoices[c.id] && (
                <div className="mt-3 pt-3 border-t border-slate-100 space-y-2">
                  <span className="text-[11px] font-bold text-slate-400 block mb-1">直近の本人の投稿</span>
                  {expandedVoices[c.id].length === 0 ? (
                    <div className="text-xs text-slate-400 py-2">まだ声の投稿がありません。</div>
                  ) : (
                    expandedVoices[c.id].slice(0, 3).map((v) => (
                      <div key={v.id} className="p-3 bg-slate-50 rounded-xl text-xs space-y-1">
                        <div className="flex justify-between text-[10px] text-slate-400">
                          <span>{v.logged_at ? new Date(v.logged_at).toLocaleDateString('ja-JP') : ''}</span>
                          {v.needs_help && <span className="text-rose-600 font-bold">相談希望</span>}
                        </div>
                        {v.raw_voice && <p className="text-slate-800 font-medium">「{v.raw_voice}」</p>}
                        {v.self_coping_action && (
                          <p className="text-slate-600">
                            <span className="font-semibold text-emerald-700">自力対処:</span> {v.self_coping_action}
                          </p>
                        )}
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* 支援記録登録モーダル */}
      {activeModalContract && (
        <JobRetentionActionModal
          isOpen={true}
          onClose={() => setActiveModalContract(null)}
          contractId={activeModalContract.id}
          userName={activeModalContract.name}
          onSaved={() => {
            setActiveModalContract(null);
            loadContracts();
          }}
        />
      )}

      {/* 新規定着支援登録モーダル */}
      {isNewContractOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
          <div className="bg-white w-full max-w-md rounded-2xl shadow-xl overflow-hidden p-6 text-xs">
            <h2 className="text-base font-bold text-slate-800 mb-4 flex items-center gap-2">
              <Plus className="w-5 h-5 text-indigo-600" />
              新規定着支援の開始
            </h2>

            <form onSubmit={handleCreateContract} className="space-y-3.5">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">利用者ID (ユーザー番号)</label>
                <input
                  type="number"
                  value={newUserId}
                  onChange={(e) => setNewUserId(e.target.value)}
                  placeholder="例: 1"
                  required
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">就職先企業名</label>
                <input
                  type="text"
                  value={newWorkplace}
                  onChange={(e) => setNewWorkplace(e.target.value)}
                  placeholder="例: 株式会社ABCコーポレーション"
                  required
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">職種・業務内容</label>
                <input
                  type="text"
                  value={newJobTitle}
                  onChange={(e) => setNewJobTitle(e.target.value)}
                  placeholder="例: 総務事務・PC作業"
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">定着支援開始日</label>
                <input
                  type="date"
                  value={newStartDate}
                  onChange={(e) => setNewStartDate(e.target.value)}
                  required
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <label className="flex items-center gap-2 cursor-pointer pt-1">
                <input
                  type="checkbox"
                  checked={isCompanyInvolved}
                  onChange={(e) => setIsCompanyInvolved(e.target.checked)}
                  className="rounded text-indigo-600"
                />
                <span className="font-semibold text-slate-700">企業連携あり（企業訪問・職場把握を実施）</span>
              </label>

              <div className="pt-4 flex justify-end gap-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsNewContractOpen(false)}
                  className="px-4 py-2 bg-slate-100 text-slate-600 rounded-xl hover:bg-slate-200"
                >
                  キャンセル
                </button>
                <button
                  type="submit"
                  disabled={creatingContract}
                  className="px-5 py-2 bg-indigo-600 text-white font-semibold rounded-xl hover:bg-indigo-700 shadow-sm"
                >
                  {creatingContract ? '登録中...' : '登録する'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 支援計画の新規作成・随時見直しモーダル */}
      {reviewModalContract && (
        <RetentionPlanReviewModal
          isOpen={Boolean(reviewModalContract)}
          onClose={() => setReviewModalContract(null)}
          contractId={reviewModalContract.id}
          userName={reviewModalContract.name}
          activePlan={reviewModalContract.activePlan}
          onSaved={(_newPlan) => {
            loadContracts();
            if (reviewModalContract.id) {
              loadHistory(reviewModalContract.id);
            }
          }}
        />
      )}
    </div>
  );
};

export default JobRetentionStaffDashboardPage;
