// frontend/src/pages/user/UserSupportViewPage.tsx

import React, { useEffect, useState } from 'react';
import { 
  jobRetentionApi, 
  type RetentionContract,
  type SupportPlan,
  type SupportPlanDetailData
} from '../../services/jobRetentionApi';
import { useUserDocuments } from '../../hooks/useUserDocuments';
import { A4PrintDocumentView } from '../../components/documents/A4PrintDocumentView';
import { SignatureModal } from '../../components/documents/SignatureModal';
import { 
  Target, 
  FileText, 
  CheckCircle2, 
  AlertCircle, 
  Clock, 
  Eye, 
  ShieldCheck, 
  Briefcase
} from 'lucide-react';

export const UserSupportViewPage: React.FC = () => {
  const [contract, setContract] = useState<RetentionContract | null>(null);
  const [activePlan, setActivePlan] = useState<SupportPlan | null>(null);
  const [planDetail, setPlanDetail] = useState<SupportPlanDetailData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const {
    pendingDocs,
    deliveredDocs,
    docError,
    previewSnapshot,
    previewConsent,
    showPreviewModal,
    setShowPreviewModal,
    selectedDocForSign,
    setSelectedDocForSign,
    handleOpenRenderedDocument,
    handleSignatureSuccess,
  } = useUserDocuments();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const c = await jobRetentionApi.getMyContract();
      if (c && c.id) {
        setContract(c);
        try {
          const planRes = await jobRetentionApi.getActiveSupportPlan(c.id);
          if (planRes.has_plan && planRes.plan) {
            setActivePlan(planRes.plan);
            // 詳細項目も取得
            try {
              const detail = await jobRetentionApi.getSupportPlanDetail(c.id, planRes.plan.id);
              setPlanDetail(detail);
            } catch (detailErr) {
              console.warn('計画詳細の取得をスキップしました', detailErr);
            }
          }
        } catch (planErr) {
          console.warn('支援計画の取得をスキップしました', planErr);
        }
      }
    } catch (err: any) {
      console.error('支援情報の取得に失敗しました', err);
      setError('支援情報の取得に失敗しました。');
    } finally {
      setLoading(false);
    }
  };

  // 同意待ちの新しい支援計画（もしあれば）
  const pendingPlanDoc = pendingDocs.find(d => d.document_type === 'SUPPORT_PLAN');

  // 電子交付済みの支援レポート一覧
  const deliveredReports = deliveredDocs.filter(d => d.document_type === 'RETENTION_SUPPORT_REPORT');

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[50vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-600"></div>
        <span className="ml-3 text-slate-600 text-sm">支援情報を読み込み中...</span>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* ページタイトル */}
      <div>
        <h1 className="text-2xl font-black text-slate-900 flex items-center gap-2">
          <FileText className="w-6 h-6 text-teal-600" />
          支援を見る
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 mt-1">
          現在適用されている支援計画や、正式に交付された月次レポートを確認できます。
        </p>
      </div>

      {(error || docError) && (
        <div className="bg-rose-50 border border-rose-200 text-rose-700 p-4 rounded-xl flex items-center text-xs sm:text-sm">
          <AlertCircle className="w-5 h-5 mr-2 flex-shrink-0" />
          <span>{error || docError}</span>
        </div>
      )}

      {/* 1. 確認してほしい新しい支援計画（同意待ちがある場合のみ強調表示） */}
      {pendingPlanDoc && (
        <section className="bg-amber-50 border-2 border-amber-300 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex items-center gap-2 text-amber-900 font-bold">
            <AlertCircle className="w-5 h-5 text-amber-600" />
            <h2 className="text-lg">確認してほしい新しい支援計画があります（第{pendingPlanDoc.document_version}版）</h2>
          </div>
          <p className="text-xs sm:text-sm text-amber-800">
            支援員より新しく見直された支援計画書が作成されました。
            内容をご確認の上、電子署名（サイン）をお願いいたします。署名が完了するまでは、現在の支援計画が引き続き有効となります。
          </p>

          <div className="bg-white rounded-xl p-4 border border-amber-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div className="font-bold text-slate-800 text-sm">{pendingPlanDoc.title}</div>
              <div className="text-xs text-slate-500 mt-0.5">
                交付日: {pendingPlanDoc.delivered_at ? new Date(pendingPlanDoc.delivered_at).toLocaleDateString('ja-JP') : '本日'}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => handleOpenRenderedDocument(pendingPlanDoc.document_type, pendingPlanDoc.document_id)}
                className="px-3 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg flex items-center gap-1 transition-colors"
              >
                <Eye className="w-3.5 h-3.5" />
                計画書を読む
              </button>
              <button
                onClick={() => setSelectedDocForSign(pendingPlanDoc)}
                className="px-4 py-2 text-xs font-bold text-white bg-teal-600 hover:bg-teal-700 rounded-lg shadow-sm flex items-center gap-1.5 transition-colors"
              >
                <ShieldCheck className="w-3.5 h-3.5" />
                内容を確認してサインする
              </button>
            </div>
          </div>
        </section>
      )}

      {/* 2. 現在の支援計画（ACTIVE） */}
      <section className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-4">
          <div className="flex items-center gap-2">
            <Target className="w-5 h-5 text-teal-600" />
            <h2 className="font-bold text-slate-800 text-lg">現在の支援計画</h2>
            {activePlan && (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                第{activePlan.version}版 有効
              </span>
            )}
          </div>
          {activePlan && (
            <div className="text-xs text-slate-500">
              計画期間: {activePlan.start_date} 〜 {activePlan.plan_end_date}
            </div>
          )}
        </div>

        {activePlan ? (
          <div className="space-y-6">
            {/* 全体目標 */}
            <div className="bg-teal-50/60 border border-teal-100 rounded-xl p-4">
              <div className="text-xs font-bold text-teal-800 mb-1 flex items-center gap-1">
                <Target className="w-3.5 h-3.5" />
                全体の支援目標
              </div>
              <p className="text-sm font-semibold text-slate-800 leading-relaxed">
                {activePlan.overall_support_goal || '安定した就労の継続'}
              </p>
            </div>

            {/* 見直し予定日 */}
            <div className="flex items-center gap-2 text-xs text-slate-600 bg-slate-50 p-3 rounded-xl border border-slate-100">
              <Clock className="w-4 h-4 text-slate-400" />
              <span>
                次回見直し予定: <strong className="text-slate-800">{activePlan.next_plan_start_date || '未定'}</strong>
              </span>
            </div>

            {/* 具体的な支援内容・課題項目 */}
            {planDetail && planDetail.items && planDetail.items.length > 0 && (
              <div className="space-y-3">
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                  具体的な支援内容と役割分担
                </h3>
                <div className="grid grid-cols-1 gap-3">
                  {planDetail.items.map((item, idx) => (
                    <div key={item.id || idx} className="bg-slate-50 rounded-xl p-4 border border-slate-100 space-y-2">
                      <div className="flex items-center gap-2">
                        <span className="w-5 h-5 rounded-full bg-teal-100 text-teal-800 text-xs font-bold flex items-center justify-center">
                          {item.item_number}
                        </span>
                        <span className="font-bold text-slate-800 text-sm">
                          {item.challenge_topic || `支援項目 ${item.item_number}`}
                        </span>
                      </div>
                      {item.support_content && (
                        <p className="text-xs text-slate-600 pl-7">
                          {item.support_content}
                        </p>
                      )}
                      {(item.role_sharing || item.support_frequency) && (
                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-slate-500 pl-7 pt-1">
                          {item.support_frequency && <span>頻度: {item.support_frequency}</span>}
                          {item.role_sharing && <span>役割: {item.role_sharing}</span>}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-8 text-slate-500 text-xs sm:text-sm">
            現在有効な支援計画書は登録されていません。
          </div>
        )}
      </section>

      {/* 3. 正式な支援レポート（電子交付済み） */}
      <section className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
        <div className="border-b border-slate-100 pb-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-teal-600" />
            <h2 className="font-bold text-slate-800 text-lg">交付された支援レポート</h2>
          </div>
          <span className="text-xs text-slate-400">計 {deliveredReports.length} 件</span>
        </div>
        <p className="text-xs text-slate-500">
          支援員より正式に電子交付された月次状況報告書です。いつでもA4形式で閲覧いただけます。
        </p>

        {deliveredReports.length === 0 ? (
          <div className="text-center py-6 text-slate-400 text-xs sm:text-sm bg-slate-50 rounded-xl border border-dashed border-slate-200">
            電子交付された支援レポートはまだありません。
          </div>
        ) : (
          <div className="space-y-2.5">
            {deliveredReports.map((doc) => (
              <div
                key={doc.delivery_id}
                className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 bg-slate-50 rounded-xl border border-slate-100 hover:bg-slate-100/80 transition-colors gap-3"
              >
                <div>
                  <div className="font-bold text-slate-800 text-sm">{doc.title}</div>
                  <div className="text-xs text-slate-400 mt-0.5 flex items-center gap-3">
                    <span>交付日: {doc.delivered_at ? new Date(doc.delivered_at).toLocaleDateString('ja-JP') : '-'}</span>
                    {doc.is_signed ? (
                      <span className="text-emerald-600 font-semibold flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" /> 署名済み
                      </span>
                    ) : (
                      <span className="text-amber-600 font-semibold">確認済み</span>
                    )}
                  </div>
                </div>

                <button
                  onClick={() => handleOpenRenderedDocument(doc.document_type, doc.document_id)}
                  className="self-end sm:self-center px-3.5 py-1.5 text-xs font-semibold text-teal-700 bg-white border border-teal-200 hover:bg-teal-50 rounded-lg flex items-center gap-1 transition-colors shadow-2xs"
                >
                  <Eye className="w-3.5 h-3.5" />
                  A4文書を表示
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* 4. 契約・勤務先情報 */}
      {contract && (
        <section className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-3">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
            <Briefcase className="w-5 h-5 text-teal-600" />
            <h2 className="font-bold text-slate-800 text-base">ご契約・勤務先について</h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-100">
              <span className="text-slate-400 block mb-1 font-semibold">勤務先企業名</span>
              <span className="font-bold text-slate-800 text-sm">{contract.workplace_name || contract.latest_workplace || '未設定'}</span>
            </div>
            <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-100">
              <span className="text-slate-400 block mb-1 font-semibold">定着支援契約期間</span>
              <span className="font-bold text-slate-800 text-sm">{contract.contract_start_date} 〜 {contract.contract_end_date}</span>
            </div>
          </div>
        </section>
      )}

      {/* A4 プレビュー Modal */}
      {showPreviewModal && previewSnapshot && (
        <A4PrintDocumentView
          snapshot={previewSnapshot}
          consentInfo={previewConsent}
          onClose={() => setShowPreviewModal(false)}
        />
      )}

      {/* 電子署名 Modal */}
      {selectedDocForSign && (
        <SignatureModal
          isOpen={true}
          onClose={() => setSelectedDocForSign(null)}
          onSuccess={handleSignatureSuccess}
          documentType={selectedDocForSign.document_type}
          documentId={selectedDocForSign.document_id}
          documentTitle={selectedDocForSign.title}
          mode="user_sign"
        />
      )}
    </div>
  );
};
