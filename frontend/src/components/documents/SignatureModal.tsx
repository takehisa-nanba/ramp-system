import React, { useState, useEffect } from 'react';
import { 
  CheckCircle, FileText, Send, Upload, AlertCircle, 
  X, Printer, ShieldCheck, Clock
} from 'lucide-react';
import client from '../../services/apiClient';

interface DocumentStatusResponse {
  document_type: string;
  document_id: number;
  document_version: number;
  doc_status: string;
  has_snapshot: boolean;
  can_sign_digitally: boolean;
  deliveries: Array<{
    id: number;
    delivery_method: string;
    delivered_at: string;
    viewed_at: string | null;
    delivered_by_name: string | null;
  }>;
  consent: {
    id: number;
    signature_method: string;
    action: string;
    signed_at: string;
    evidence_file_url: string | null;
    recorded_by_name: string | null;
  } | null;
}

export interface SignatureModalProps {
  isOpen: boolean;
  onClose: () => void;
  documentType: 'SUPPORT_PLAN' | 'RETENTION_SUPPORT_REPORT';
  documentId: number;
  documentTitle: string;
  userName?: string;
  mode?: 'staff_manage' | 'user_sign';
  isStaffMode?: boolean; // 職員操作モードか本人操作モードか
  onSuccess?: () => void;
  onStatusChange?: () => void;
  onOpenPreview?: () => void;
}

export const SignatureModal: React.FC<SignatureModalProps> = ({
  isOpen,
  onClose,
  documentType,
  documentId,
  documentTitle,
  userName,
  mode = 'staff_manage',
  isStaffMode: propIsStaffMode,
  onSuccess,
  onStatusChange,
  onOpenPreview,
}) => {
  const isStaffMode = propIsStaffMode ?? (mode === 'staff_manage');
  const [statusData, setStatusData] = useState<DocumentStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // 紙署名アップロードフォーム
  const [signedDate, setSignedDate] = useState<string>(new Date().toISOString().slice(0, 10));
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  useEffect(() => {
    if (isOpen) {
      fetchStatus();
    }
  }, [isOpen, documentType, documentId]);

  const fetchStatus = async () => {
    try {
      setLoading(true);
      setErrorMsg(null);
      const res = await client.get<DocumentStatusResponse>(
        `/consents/documents/${documentType}/${documentId}/status`
      );
      setStatusData(res.data);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.msg || '文書ステータスの取得に失敗しました。');
    } finally {
      setLoading(false);
    }
  };

  const notifyChange = () => {
    if (onSuccess) onSuccess();
    if (onStatusChange) onStatusChange();
  };

  // 1. 文書確定 (職員)
  const handleFinalize = async () => {
    try {
      setSubmitting(true);
      setErrorMsg(null);
      await client.post(`/consents/documents/${documentType}/${documentId}/finalize`);
      setSuccessMsg('文書を確定し、確定版スナップショットを固定しました。');
      await fetchStatus();
      notifyChange();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.msg || '確定処理に失敗しました。');
    } finally {
      setSubmitting(false);
    }
  };

  // 2. 電子配信 (職員)
  const handleDeliverDigital = async () => {
    try {
      setSubmitting(true);
      setErrorMsg(null);
      await client.post(`/consents/documents/${documentType}/${documentId}/deliver-digital`);
      setSuccessMsg('本人アカウントへ電子交付（配信）しました。');
      await fetchStatus();
      notifyChange();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.msg || '電子配信に失敗しました。');
    } finally {
      setSubmitting(false);
    }
  };

  // 3. 紙交付記録 (職員)
  const handleDeliverPaper = async () => {
    try {
      setSubmitting(true);
      setErrorMsg(null);
      await client.post(`/consents/documents/${documentType}/${documentId}/deliver-paper`, {
        delivered_at: new Date().toISOString().slice(0, 10)
      });
      setSuccessMsg('紙交付の記録を登録しました。');
      await fetchStatus();
      notifyChange();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.msg || '紙交付記録の登録に失敗しました。');
    } finally {
      setSubmitting(false);
    }
  };

  // 4. 紙署名証拠アップロード (職員)
  const handleUploadPaperSignature = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setErrorMsg('署名済みの証拠ファイル（画像またはPDF）を選択してください。');
      return;
    }

    try {
      setSubmitting(true);
      setErrorMsg(null);
      const formData = new FormData();
      formData.append('document_type', documentType);
      formData.append('document_id', documentId.toString());
      formData.append('signed_at', signedDate);
      formData.append('evidence_file', selectedFile);

      await client.post('/consents/paper-upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setSuccessMsg('紙署名証拠ファイルを登録し、計画を有効化しました。');
      setSelectedFile(null);
      await fetchStatus();
      notifyChange();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.msg || '紙署名証拠の登録に失敗しました。');
    } finally {
      setSubmitting(false);
    }
  };

  // 5. 本人電子署名 (利用者マイページ)
  const handleDigitalSign = async () => {
    try {
      setSubmitting(true);
      setErrorMsg(null);
      await client.post('/consents/digital-sign', {
        document_type: documentType,
        document_id: documentId
      });
      setSuccessMsg('同意・電子署名を完了しました。');
      await fetchStatus();
      notifyChange();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.msg || '電子署名に失敗しました。');
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  const isSigned = statusData?.consent !== null && statusData?.consent !== undefined;

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white w-full max-w-2xl rounded-3xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
        {/* ヘッダー */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/50">
          <div className="flex items-center space-x-3">
            <ShieldCheck className="w-6 h-6 text-indigo-600" />
            <div>
              <h2 className="text-lg font-bold text-slate-800">{documentTitle}</h2>
              <p className="text-xs text-slate-500">
                {userName ? `対象利用者: ${userName} | ` : ''}文書確定・交付および同意証跡の管理
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-600 rounded-xl hover:bg-slate-100 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* コンテンツ */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-sm">
          {/* メッセージ */}
          {errorMsg && (
            <div className="flex items-start space-x-2 p-3 bg-red-50 text-red-700 rounded-xl text-xs border border-red-200">
              <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}
          {successMsg && (
            <div className="flex items-start space-x-2 p-3 bg-emerald-50 text-emerald-700 rounded-xl text-xs border border-emerald-200">
              <CheckCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <span>{successMsg}</span>
            </div>
          )}

          {loading ? (
            <div className="py-12 flex justify-center items-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
            </div>
          ) : (
            <>
              {/* ステータスバッジ */}
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200">
                  <span className="text-xs font-semibold text-slate-500 block mb-1">文書確定状態</span>
                  <span className={`inline-flex items-center font-bold px-2.5 py-0.5 rounded-full text-xs ${
                    statusData?.has_snapshot ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                  }`}>
                    {statusData?.has_snapshot ? '確定済み (スナップショット固定)' : '下書き (未確定)'}
                  </span>
                </div>
                <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200">
                  <span className="text-xs font-semibold text-slate-500 block mb-1">本人電子署名適格性</span>
                  <span className={`inline-flex items-center font-bold px-2.5 py-0.5 rounded-full text-xs ${
                    statusData?.can_sign_digitally ? 'bg-indigo-100 text-indigo-800' : 'bg-slate-200 text-slate-700'
                  }`}>
                    {statusData?.can_sign_digitally ? '利用可能 (電子交付推奨)' : '対象外 (紙署名要)'}
                  </span>
                </div>
              </div>

              {/* プレビューボタン */}
              {onOpenPreview && (
                <div className="flex justify-between items-center p-4 bg-indigo-50/50 rounded-2xl border border-indigo-100">
                  <div className="flex items-center space-x-2 text-indigo-900">
                    <FileText className="w-5 h-5 text-indigo-600" />
                    <span className="font-semibold text-xs">確定文書の全体プレビュー</span>
                  </div>
                  <button
                    onClick={onOpenPreview}
                    className="flex items-center space-x-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-medium transition"
                  >
                    <Printer className="w-3.5 h-3.5" />
                    <span>A4帳票を開く</span>
                  </button>
                </div>
              )}

              {/* 署名完了済み証跡 */}
              {isSigned ? (
                <div className="p-5 bg-emerald-50 rounded-2xl border border-emerald-200 space-y-2">
                  <div className="flex items-center space-x-2 text-emerald-800 font-bold">
                    <CheckCircle className="w-5 h-5 text-emerald-600" />
                    <span>署名・同意が成立しています</span>
                  </div>
                  <div className="text-xs text-emerald-900 grid grid-cols-2 gap-2 pt-2">
                    <div>
                      <span className="text-emerald-700">成立経路: </span>
                      <span className="font-semibold">
                        {statusData?.consent?.signature_method === 'USER_DIGITAL' ? '本人電子署名 (USER_DIGITAL)' : '紙署名証憑 (PAPER_UPLOAD)'}
                      </span>
                    </div>
                    <div>
                      <span className="text-emerald-700">成立日時: </span>
                      <span>{statusData?.consent?.signed_at?.slice(0, 16).replace('T', ' ')}</span>
                    </div>
                    {statusData?.consent?.evidence_file_url && (
                      <div className="col-span-2 mt-1">
                        <span className="text-emerald-700">証憑ファイル: </span>
                        <a
                          href={statusData.consent.evidence_file_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-indigo-600 underline font-medium hover:text-indigo-800"
                        >
                          添付ファイルを確認する
                        </a>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <>
                  {/* 未署名時の操作 (モード分岐) */}
                  {isStaffMode ? (
                    <div className="space-y-4">
                      <h3 className="font-bold text-slate-800 text-xs uppercase tracking-wider">交付および証跡の登録</h3>

                      {/* 1. 未確定の場合の確定ボタン */}
                      {!statusData?.has_snapshot && (
                        <div className="p-4 bg-amber-50 rounded-2xl border border-amber-200 flex items-center justify-between">
                          <div>
                            <p className="font-bold text-amber-900 text-xs">内容の確定が必要です</p>
                            <p className="text-amber-700 text-xs mt-0.5">サビ管承認の上、文書内容を固定して交付可能にします。</p>
                          </div>
                          <button
                            onClick={handleFinalize}
                            disabled={submitting}
                            className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white font-medium rounded-xl text-xs transition"
                          >
                            文書を確定する
                          </button>
                        </div>
                      )}

                      {/* 2. 交付アクション */}
                      {statusData?.has_snapshot && (
                        <div className="grid grid-cols-2 gap-3">
                          <button
                            onClick={handleDeliverDigital}
                            disabled={submitting}
                            className="flex items-center justify-center space-x-2 p-3 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded-2xl font-medium text-xs transition border border-indigo-200"
                          >
                            <Send className="w-4 h-4" />
                            <span>本人へ電子交付 (配信)</span>
                          </button>
                          <button
                            onClick={handleDeliverPaper}
                            disabled={submitting}
                            className="flex items-center justify-center space-x-2 p-3 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-2xl font-medium text-xs transition border border-slate-200"
                          >
                            <Printer className="w-4 h-4" />
                            <span>紙で交付した事実を記録</span>
                          </button>
                        </div>
                      )}

                      {/* 3. 紙署名アップロードフォーム */}
                      {statusData?.has_snapshot && (
                        <form onSubmit={handleUploadPaperSignature} className="p-4 bg-slate-50 rounded-2xl border border-slate-200 space-y-3">
                          <h4 className="font-bold text-slate-700 text-xs flex items-center space-x-1.5">
                            <Upload className="w-4 h-4 text-slate-500" />
                            <span>紙署名証憑のアップロード（フォールバック）</span>
                          </h4>
                          <div className="grid grid-cols-2 gap-3">
                            <div>
                              <label className="block text-xs font-semibold text-slate-600 mb-1">受領・署名日</label>
                              <input
                                type="date"
                                value={signedDate}
                                onChange={(e) => setSignedDate(e.target.value)}
                                className="w-full text-xs px-3 py-2 border border-slate-300 rounded-xl bg-white"
                                required
                              />
                            </div>
                            <div>
                              <label className="block text-xs font-semibold text-slate-600 mb-1">署名済み証拠ファイル</label>
                              <input
                                type="file"
                                accept=".png,.jpg,.jpeg,.pdf"
                                onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                                className="w-full text-xs text-slate-600 file:mr-2 file:py-1.5 file:px-3 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
                                required
                              />
                            </div>
                          </div>
                          <div className="text-right">
                            <button
                              type="submit"
                              disabled={submitting || !selectedFile}
                              className="px-4 py-2 bg-slate-800 hover:bg-slate-900 disabled:bg-slate-300 text-white font-medium rounded-xl text-xs transition"
                            >
                              紙署名を完了して有効化
                            </button>
                          </div>
                        </form>
                      )}
                    </div>
                  ) : (
                    /* 本人操作モード（マイページ用） */
                    <div className="space-y-4">
                      <div className="p-4 bg-indigo-50 rounded-2xl border border-indigo-100 text-indigo-900 text-xs leading-relaxed">
                        上記文書の内容をよくご確認の上、同意される場合は「同意して電子署名する」ボタンを押してください。
                      </div>
                      <div className="flex justify-end space-x-3">
                        <button
                          onClick={handleDigitalSign}
                          disabled={submitting}
                          className="flex items-center space-x-2 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-2xl transition shadow-md"
                        >
                          <CheckCircle className="w-4 h-4" />
                          <span>同意して電子署名する</span>
                        </button>
                      </div>
                    </div>
                  )}
                </>
              )}

              {/* 交付履歴一覧 */}
              {(statusData?.deliveries || []).length > 0 && (
                <div className="pt-2 border-t border-slate-100">
                  <h4 className="text-xs font-semibold text-slate-500 mb-2 flex items-center space-x-1">
                    <Clock className="w-3.5 h-3.5" />
                    <span>交付・閲覧ログ</span>
                  </h4>
                  <div className="space-y-1.5">
                    {statusData?.deliveries.map((d) => (
                      <div key={d.id} className="text-xs bg-slate-50 p-2.5 rounded-xl border border-slate-200 flex justify-between items-center text-slate-600">
                        <div className="flex items-center space-x-2">
                          <span className="font-semibold text-slate-700">
                            {d.delivery_method === 'DIGITAL' ? '電子交付' : '紙手渡し'}
                          </span>
                          <span>交付日時: {d.delivered_at.slice(0, 16).replace('T', ' ')}</span>
                          {d.delivered_by_name && <span>(担当: {d.delivered_by_name})</span>}
                        </div>
                        <div>
                          {d.viewed_at ? (
                            <span className="text-emerald-700 font-medium">初回閲覧: {d.viewed_at.slice(0, 16).replace('T', ' ')}</span>
                          ) : (
                            <span className="text-slate-400">未閲覧</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};
