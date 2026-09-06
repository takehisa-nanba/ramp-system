// frontend/src/pages/user/UserHomePage.tsx

import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { 
  jobRetentionApi, 
  type RetentionContract, 
  type SupportPlan 
} from '../../services/jobRetentionApi';
import { useUserDocuments } from '../../hooks/useUserDocuments';
import { A4PrintDocumentView } from '../../components/documents/A4PrintDocumentView';
import { SignatureModal } from '../../components/documents/SignatureModal';
import { 
  AlertCircle, 
  CheckCircle2, 
  PenTool, 
  Calendar, 
  Building2, 
  Target, 
  Clock, 
  Sparkles,
  ShieldCheck,
  ChevronRight,
  Eye
} from 'lucide-react';

export const UserHomePage: React.FC = () => {
  const navigate = useNavigate();

  const [contract, setContract] = useState<RetentionContract | null>(null);
  const [activePlan, setActivePlan] = useState<SupportPlan | null>(null);
  const [loadingSummary, setLoadingSummary] = useState(true);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  const {
    pendingDocs,
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
    loadContractAndPlan();
  }, []);

  const loadContractAndPlan = async () => {
    try {
      setLoadingSummary(true);
      setSummaryError(null);
      const c = await jobRetentionApi.getMyContract();
      if (c && c.id) {
        setContract(c);
        try {
          const planRes = await jobRetentionApi.getActiveSupportPlan(c.id);
          if (planRes.has_plan && planRes.plan) {
            setActivePlan(planRes.plan);
          }
        } catch (planErr) {
          console.warn('支援計画の取得をスキップしました', planErr);
        }
      }
    } catch (err: any) {
      console.error('契約情報の取得に失敗しました', err);
      setSummaryError('ご案内情報の取得に失敗しました。');
    } finally {
      setLoadingSummary(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* 挨拶ヘッダー */}
      <div className="bg-gradient-to-r from-teal-600 to-emerald-600 rounded-2xl p-6 text-white shadow-md shadow-teal-900/10">
        <h1 className="text-xl sm:text-2xl font-black mb-1">
          こんにちは！ RAMP 定着ノートへようこそ
        </h1>
        <p className="text-teal-50 text-xs sm:text-sm">
          安心して働き続けるためのマイページです。大切なお知らせや支援内容をいつでも確認できます。
        </p>
      </div>

      {/* エラー表示 */}
      {(summaryError || docError) && (
        <div className="bg-rose-50 border border-rose-200 text-rose-700 p-4 rounded-xl flex items-center text-xs sm:text-sm">
          <AlertCircle className="w-5 h-5 mr-2 flex-shrink-0" />
          <span>{summaryError || docError}</span>
        </div>
      )}

      {/* 1. 最重要：確認・同意が必要な文書（pendingDocs） */}
      <section>
        {pendingDocs.length > 0 ? (
          <div className="bg-amber-50 border-2 border-amber-300 rounded-2xl p-5 shadow-sm space-y-3">
            <div className="flex items-center gap-2 text-amber-900 font-bold text-base">
              <AlertCircle className="w-5 h-5 text-amber-600" />
              <h2>ご確認・サインをお願いしたい文書があります（{pendingDocs.length}件）</h2>
            </div>
            <p className="text-xs sm:text-sm text-amber-800">
              支援員より新しく交付された正式文書です。内容をご確認いただき、電子署名（サイン）をお願いいたします。
            </p>

            <div className="space-y-2.5 pt-1">
              {pendingDocs.map((doc) => (
                <div 
                  key={`${doc.document_type}-${doc.document_id}`}
                  className="bg-white rounded-xl p-4 border border-amber-200 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-100 text-amber-800">
                        {doc.document_type === 'SUPPORT_PLAN' ? '支援計画書' : '就労定着支援状況報告書'}
                      </span>
                      <span className="font-bold text-slate-800 text-sm">{doc.title}</span>
                    </div>
                    <div className="text-xs text-slate-500">
                      交付日: {doc.delivered_at ? new Date(doc.delivered_at).toLocaleDateString('ja-JP') : '本日'}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 self-end sm:self-center">
                    <button
                      onClick={() => handleOpenRenderedDocument(doc.document_type, doc.document_id)}
                      className="px-3 py-1.5 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg flex items-center gap-1 transition-colors"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      文書を読む
                    </button>
                    <button
                      onClick={() => setSelectedDocForSign(doc)}
                      className="px-3.5 py-1.5 text-xs font-bold text-white bg-teal-600 hover:bg-teal-700 rounded-lg shadow-sm flex items-center gap-1.5 transition-colors"
                    >
                      <ShieldCheck className="w-3.5 h-3.5" />
                      確認してサインする
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="bg-white border border-slate-200 rounded-2xl p-4 flex items-center gap-3 text-slate-600 text-xs sm:text-sm">
            <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />
            <span>現在、確認やサインが必要な文書はありません。</span>
          </div>
        )}
      </section>

      {/* 2. クイックアクション：「最近、何かありましたか？」 */}
      <section className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-teal-600" />
            <h2 className="font-bold text-slate-800 text-base">最近、困ったことや気になることはありますか？</h2>
          </div>
          <p className="text-xs sm:text-sm text-slate-500">
            仕事での嬉しかったこと、困りごと、体調の変化など、なんでも気軽に残してください。支援員と一緒に振り返ることができます。
          </p>
        </div>
        <button
          onClick={() => navigate('/user/voice')}
          className="shrink-0 inline-flex items-center justify-center px-5 py-2.5 bg-teal-600 hover:bg-teal-700 text-white text-sm font-bold rounded-xl shadow-sm transition-colors gap-2"
        >
          <PenTool className="w-4 h-4" />
          できごと・気持ちを残す
        </button>
      </section>

      {/* 3. 現在の支援サマリー */}
      <section className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <Target className="w-5 h-5 text-teal-600" />
            <h2 className="font-bold text-slate-800 text-base">現在の支援について</h2>
          </div>
          <Link
            to="/user/support"
            className="inline-flex items-center text-xs font-bold text-teal-600 hover:text-teal-700 transition-colors"
          >
            支援の内容を見る
            <ChevronRight className="w-4 h-4 ml-0.5" />
          </Link>
        </div>

        {contract ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* 就労・契約期間 */}
            <div className="bg-slate-50 rounded-xl p-4 space-y-2 border border-slate-100">
              <div className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <Building2 className="w-4 h-4 text-slate-500" />
                勤務先・契約期間
              </div>
              <div>
                <p className="font-bold text-slate-800 text-sm">
                  {contract.workplace_name || contract.latest_workplace || '勤務先情報なし'}
                </p>
                <p className="text-xs text-slate-500 mt-0.5">
                  契約期間: {contract.contract_start_date} 〜 {contract.contract_end_date}
                </p>
              </div>
            </div>

            {/* 支援目標 & 見直し予定 */}
            <div className="bg-slate-50 rounded-xl p-4 space-y-2 border border-slate-100">
              <div className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <Calendar className="w-4 h-4 text-slate-500" />
                現在の目標と見直し
              </div>
              <div>
                {activePlan ? (
                  <>
                    <p className="text-xs text-slate-700 font-medium line-clamp-2">
                      <span className="font-bold text-teal-800 mr-1">目標:</span>
                      {activePlan.overall_support_goal || '安定した就労の継続'}
                    </p>
                    <p className="text-xs text-slate-500 mt-1 flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5 text-slate-400" />
                      次回見直し予定: <strong className="text-slate-700">{activePlan.next_plan_start_date || '未定'}</strong>
                    </p>
                  </>
                ) : (
                  <p className="text-xs text-slate-500">
                    現在有効な支援計画書は登録されていません。
                  </p>
                )}
              </div>
            </div>
          </div>
        ) : (
          <p className="text-xs text-slate-500 py-2">
            {loadingSummary ? '定着支援の契約情報を読み込み中...' : '定着支援の契約情報は現在登録されていません。'}
          </p>
        )}
      </section>

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
