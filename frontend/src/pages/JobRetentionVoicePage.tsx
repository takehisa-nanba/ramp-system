// frontend/src/pages/JobRetentionVoicePage.tsx

import React, { useState, useEffect } from 'react';
import { jobRetentionApi } from '../services/jobRetentionApi';
import type { RetentionContract, UserVoiceLog } from '../services/jobRetentionApi';
import { MessageSquare, CheckCircle2, AlertCircle, Sparkles, Send, History, HeartHandshake, FileText, Eye } from 'lucide-react';
import { useUserDocuments } from '../hooks/useUserDocuments';
import { A4PrintDocumentView } from '../components/documents/A4PrintDocumentView';

interface JobRetentionVoicePageProps {
  defaultTab?: 'create' | 'history';
}

export const JobRetentionVoicePage: React.FC<JobRetentionVoicePageProps> = ({ defaultTab = 'create' }) => {
  const [contract, setContract] = useState<RetentionContract | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [pastLogs, setPastLogs] = useState<UserVoiceLog[]>([]);
  const [activeTab, setActiveTab] = useState<'create' | 'history'>(defaultTab);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // これまでの文書アーカイブ用 hook
  const {
    deliveredDocs,
    previewSnapshot,
    previewConsent,
    showPreviewModal,
    setShowPreviewModal,
    handleOpenRenderedDocument,
  } = useUserDocuments();

  useEffect(() => {
    setActiveTab(defaultTab);
  }, [defaultTab]);

  // フォームステート
  const [rawVoice, setRawVoice] = useState('');
  const [troublePoint, setTroublePoint] = useState('');
  const [successPoint, setSuccessPoint] = useState('');
  const [selfCopingAction, setSelfCopingAction] = useState('');
  const [selfCopingResult, setSelfCopingResult] = useState('');
  const [needsHelp, setNeedsHelp] = useState(false);
  const [helpTopic, setHelpTopic] = useState('');

  // 契約情報取得
  useEffect(() => {
    loadContractAndData();
  }, []);

  const loadContractAndData = async () => {
    try {
      setLoading(true);
      const c = await jobRetentionApi.getMyContract();
      setContract(c);

      // 一時保存ドラフトの復元 (sessionStorage)
      const draftKey = `retention_voice_draft_${c.id}`;
      const saved = sessionStorage.getItem(draftKey);
      if (saved) {
        try {
          const parsed = JSON.parse(saved);
          setRawVoice(parsed.rawVoice || '');
          setTroublePoint(parsed.troublePoint || '');
          setSuccessPoint(parsed.successPoint || '');
          setSelfCopingAction(parsed.selfCopingAction || '');
          setSelfCopingResult(parsed.selfCopingResult || '');
          setNeedsHelp(parsed.needsHelp || false);
          setHelpTopic(parsed.helpTopic || '');
        } catch (e) {
          console.error("Draft restore error", e);
        }
      }

      // 過去ログ取得
      const logs = await jobRetentionApi.listVoices(c.id);
      setPastLogs(logs);
    } catch (err: any) {
      setErrorMessage(err?.response?.data?.msg || '定着支援情報の取得に失敗しました。');
    } finally {
      setLoading(false);
    }
  };

  // 入力途中のセッション一時保存（入力消失防止）
  useEffect(() => {
    if (!contract) return;
    const draftKey = `retention_voice_draft_${contract.id}`;
    const draftData = {
      rawVoice,
      troublePoint,
      successPoint,
      selfCopingAction,
      selfCopingResult,
      needsHelp,
      helpTopic
    };
    sessionStorage.setItem(draftKey, JSON.stringify(draftData));
  }, [contract, rawVoice, troublePoint, successPoint, selfCopingAction, selfCopingResult, needsHelp, helpTopic]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!contract) return;

    if (!rawVoice.trim() && !troublePoint.trim() && !successPoint.trim() && !selfCopingAction.trim()) {
      setErrorMessage('ひとこと、または困りごと・できたことのいずれかを入力してください。');
      return;
    }

    try {
      setSubmitting(true);
      setErrorMessage(null);
      await jobRetentionApi.recordVoice(contract.id, {
        raw_voice: rawVoice,
        trouble_point: troublePoint,
        success_point: successPoint,
        self_coping_action: selfCopingAction,
        self_coping_result: selfCopingResult,
        needs_help: needsHelp,
        help_topic: helpTopic
      });

      // ドラフト消去 & リセット
      sessionStorage.removeItem(`retention_voice_draft_${contract.id}`);
      setRawVoice('');
      setTroublePoint('');
      setSuccessPoint('');
      setSelfCopingAction('');
      setSelfCopingResult('');
      setNeedsHelp(false);
      setHelpTopic('');

      setSuccessMessage('できごとを記録しました。支援員に共有されます。');
      setTimeout(() => setSuccessMessage(null), 4000);

      // 過去ログ再取得
      const logs = await jobRetentionApi.listVoices(contract.id);
      setPastLogs(logs);
      setActiveTab('history');
    } catch (err: any) {
      setErrorMessage(err?.response?.data?.msg || '保存に失敗しました。');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-6">
      {/* ヘッダー */}
      <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-100 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 mb-1">
              就労定着サポート
            </span>
            <h1 className="text-xl font-bold text-slate-800">できごとを残す</h1>
            <p className="text-xs text-slate-500 mt-0.5">
              {contract?.workplace_name ? `勤務先: ${contract.workplace_name}` : '日々の気づきや変化を短時間で記録できます'}
            </p>
          </div>
          <div className="h-10 w-10 bg-indigo-50 rounded-xl flex items-center justify-center text-indigo-600">
            <MessageSquare className="w-5 h-5" />
          </div>
        </div>

        {/* タブ切り替え */}
        <div className="flex gap-2 mt-4 pt-3 border-t border-slate-100">
          <button
            onClick={() => setActiveTab('create')}
            className={`flex-1 py-2 text-sm font-medium rounded-xl transition-all ${
              activeTab === 'create'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'bg-slate-50 text-slate-600 hover:bg-slate-100'
            }`}
          >
            ✏️ 新しく記録する
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`flex-1 py-2 text-sm font-medium rounded-xl transition-all flex items-center justify-center gap-1.5 ${
              activeTab === 'history'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'bg-slate-50 text-slate-600 hover:bg-slate-100'
            }`}
          >
            <History className="w-4 h-4" /> わたしの歩み ({pastLogs.length})
          </button>
        </div>
      </div>

      {successMessage && (
        <div className="mb-4 p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}

      {errorMessage && (
        <div className="mb-4 p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* タブ1: 入力フォーム */}
      {activeTab === 'create' && (
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* 生の声・つぶやき */}
          <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-100">
            <label className="block text-sm font-semibold text-slate-800 mb-1 flex items-center gap-1.5">
              <Sparkles className="w-4 h-4 text-amber-500" />
              最近あったこと・今の気持ち
            </label>
            <p className="text-xs text-slate-500 mb-2.5">
              仕事や生活で感じたこと、つぶやきなど、短文でも構いません。
            </p>
            <textarea
              value={rawVoice}
              onChange={(e) => setRawVoice(e.target.value)}
              placeholder="例：新しい作業に入って少し緊張した。休憩時間に散歩したら落ち着いた。"
              rows={3}
              className="w-full px-3.5 py-2.5 text-sm rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
            />
          </div>

          {/* 困りごと & 対処 */}
          <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-100 space-y-4">
            <h2 className="text-sm font-semibold text-slate-800 border-b border-slate-100 pb-2">
              困ったことと、自分で試してみたこと
            </h2>

            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                困ったこと・気になったこと
              </label>
              <input
                type="text"
                value={troublePoint}
                onChange={(e) => setTroublePoint(e.target.value)}
                placeholder="例：指示の意図がわかりにくかった、午後に急に眠気が出た"
                className="w-full px-3.5 py-2 text-sm rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                自分でやってみた工夫・対処
              </label>
              <input
                type="text"
                value={selfCopingAction}
                onChange={(e) => setSelfCopingAction(e.target.value)}
                placeholder="例：メモを読み返して確認した、冷たい水で顔を洗った"
                className="w-full px-3.5 py-2 text-sm rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                その結果どうだったか
              </label>
              <input
                type="text"
                value={selfCopingResult}
                onChange={(e) => setSelfCopingResult(e.target.value)}
                placeholder="例：無事に作業を終えられた、少し楽になった"
                className="w-full px-3.5 py-2 text-sm rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>

          {/* よかったこと */}
          <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-100">
            <label className="block text-sm font-semibold text-slate-800 mb-1">
              できたこと・うまくいったこと
            </label>
            <input
              type="text"
              value={successPoint}
              onChange={(e) => setSuccessPoint(e.target.value)}
              placeholder="例：挨拶を自分からできた、時間通りに出勤できた"
              className="w-full px-3.5 py-2.5 text-sm rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {/* 相談希望トグル */}
          <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-100">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <HeartHandshake className="w-5 h-5 text-indigo-600" />
                <div>
                  <span className="text-sm font-semibold text-slate-800 block">
                    支援員に相談したい・手伝ってほしい
                  </span>
                  <span className="text-xs text-slate-500">
                    面談時または電話で一緒に整理したいときにチェック
                  </span>
                </div>
              </div>
              <input
                type="checkbox"
                checked={needsHelp}
                onChange={(e) => setNeedsHelp(e.target.checked)}
                className="w-5 h-5 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500"
              />
            </div>

            {needsHelp && (
              <div className="mt-3 pt-3 border-t border-slate-100">
                <input
                  type="text"
                  value={helpTopic}
                  onChange={(e) => setHelpTopic(e.target.value)}
                  placeholder="相談したいこと（例: 次回の面談でシフトの相談をしたい）"
                  className="w-full px-3.5 py-2 text-sm rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            )}
          </div>

          {/* 送信ボタン */}
          <button
            type="submit"
            disabled={submitting}
            className="w-full py-3.5 px-4 bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white font-semibold rounded-2xl shadow-sm flex items-center justify-center gap-2 transition-all disabled:opacity-50"
          >
            <Send className="w-4 h-4" />
            {submitting ? '送信中...' : 'できごとを残す'}
          </button>
        </form>
      )}

      {/* タブ2: わたしの歩み（タイムライン & これまでの確定文書） */}
      {activeTab === 'history' && (
        <div className="space-y-6">
          {/* これまでの確定文書アーカイブ */}
          <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-100 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-teal-600" />
                <h3 className="font-bold text-slate-800 text-sm sm:text-base">これまでの確定文書</h3>
              </div>
              <span className="text-xs text-slate-400">{deliveredDocs.length} 件</span>
            </div>

            {deliveredDocs.length === 0 ? (
              <p className="text-xs text-slate-400 py-3 text-center">
                これまでに交付された確定文書はありません。
              </p>
            ) : (
              <div className="space-y-2">
                {deliveredDocs.map((doc) => (
                  <div
                    key={doc.delivery_id}
                    className="flex flex-col sm:flex-row sm:items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-100 hover:bg-slate-100/80 transition-colors gap-2"
                  >
                    <div>
                      <div className="font-bold text-slate-800 text-xs sm:text-sm">{doc.title}</div>
                      <div className="text-[11px] text-slate-400 mt-0.5 flex items-center gap-3">
                        <span>交付日: {doc.delivered_at ? new Date(doc.delivered_at).toLocaleDateString('ja-JP') : '-'}</span>
                        {doc.is_signed ? (
                          <span className="text-emerald-600 font-semibold flex items-center gap-1">
                            <CheckCircle2 className="w-3 h-3" /> 署名済み
                          </span>
                        ) : (
                          <span className="text-amber-600 font-semibold">確認済み</span>
                        )}
                      </div>
                    </div>

                    <button
                      onClick={() => handleOpenRenderedDocument(doc.document_type, doc.document_id)}
                      className="self-end sm:self-center px-3 py-1.5 text-xs font-semibold text-teal-700 bg-white border border-teal-200 hover:bg-teal-50 rounded-lg flex items-center gap-1 transition-colors shadow-2xs"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      A4文書を表示
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* できごとの記録タイムライン */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider pl-1">
              できごとの記録タイムライン
            </h3>
            {pastLogs.length === 0 ? (
              <div className="bg-white rounded-2xl p-8 text-center text-slate-500 border border-slate-100">
                まだできごとの記録がありません。日常のひとことや気持ちを気軽に残してみてください。
              </div>
            ) : (
              pastLogs.map((log) => (
                <div key={log.id} className="bg-white rounded-2xl p-5 shadow-sm border border-slate-100 space-y-2">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span>
                      {log.logged_at ? new Date(log.logged_at).toLocaleDateString('ja-JP', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                      }) : ''}
                    </span>
                    {log.needs_help && (
                      <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-rose-50 text-rose-600">
                        相談希望
                      </span>
                    )}
                  </div>

                  {log.raw_voice && (
                    <p className="text-sm font-medium text-slate-800 bg-slate-50 p-3 rounded-xl">
                      「{log.raw_voice}」
                    </p>
                  )}

                  {(log.trouble_point || log.self_coping_action) && (
                    <div className="text-xs space-y-1 bg-amber-50/50 p-3 rounded-xl border border-amber-100">
                      {log.trouble_point && (
                        <p className="text-slate-700">
                          <span className="font-semibold text-amber-800">困ったこと:</span> {log.trouble_point}
                        </p>
                      )}
                      {log.self_coping_action && (
                        <p className="text-slate-700">
                          <span className="font-semibold text-emerald-800">自分でやってみたこと:</span> {log.self_coping_action}
                        </p>
                      )}
                      {log.self_coping_result && (
                        <p className="text-slate-500">
                          <span className="font-semibold">結果:</span> {log.self_coping_result}
                        </p>
                      )}
                    </div>
                  )}

                  {log.success_point && (
                    <div className="text-xs text-emerald-800 bg-emerald-50 p-2.5 rounded-xl font-medium">
                      ✨ できたこと: {log.success_point}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* A4 プレビュー Modal */}
      {showPreviewModal && previewSnapshot && (
        <A4PrintDocumentView
          snapshot={previewSnapshot}
          consentInfo={previewConsent}
          onClose={() => setShowPreviewModal(false)}
        />
      )}
    </div>
  );
};

export default JobRetentionVoicePage;
