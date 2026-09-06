import React, { useState, useEffect } from 'react';
import { Printer, X, CheckCircle, FileText, Loader2 } from 'lucide-react';
import apiClient from '../../services/apiClient';

export interface DocumentSnapshot {
  document_type: string;
  document_id: number;
  plan_version?: number;
  report_year_month?: string;
  status?: string;
  plan_start_date?: string;
  plan_end_date?: string;
  created_at?: string;
  sabikan_approved_at?: string;
  sabikan_name?: string;
  user?: {
    id?: number;
    display_name?: string;
    user_code?: string;
    last_name?: string;
    first_name?: string;
    last_name_kana?: string;
    first_name_kana?: string;
    birth_date?: string;
    gender?: string;
    handbook_level?: string;
    disability_type?: string;
  };
  office?: {
    office_name?: string;
    address?: string;
    phone_number?: string;
    fax_number?: string;
    representative_name?: string;
  };
  long_term_goals?: Array<{
    id: number;
    goal_text: string;
    set_year_month?: string;
    target_year_month?: string;
    achievement_status?: string;
    short_term_goals?: Array<{
      id: number;
      goal_text: string;
      set_year_month?: string;
      target_year_month?: string;
      achievement_status?: string;
    }>;
  }>;
  is_retention_plan?: boolean;
  retention_detail?: {
    overall_support_goal?: string;
    review_date?: string;
    review_reason?: string;
    user_name?: string;
    user_name_kana?: string;
    gender?: string;
    birth_date?: string;
    age_at_planning?: number;
    support_level?: string;
    disability_handbook_type?: string;
    employer_name?: string;
    employer_industry?: string;
    employer_address?: string;
    employer_tel?: string;
    employer_contact_person?: string;
    job_start_date?: string;
    office_name?: string;
    office_number?: string;
    office_address?: string;
    office_tel?: string;
    office_fax?: string;
    items?: Array<{
      item_number?: number;
      challenge_topic?: string;
      support_policy?: string;
      support_content?: string;
      support_period_start?: string;
      support_period_end?: string;
      support_frequency?: string;
    }>;
  };
  // レポート用項目
  support_goal?: string;
  support_content?: string;
  support_result?: string;
  future_support_plan?: string;
  stakeholder_efforts?: string;
  sharing_notes?: string;
  interview_records?: string;
  company_visit_records?: string;
  work_status_summary?: string;
  life_status_summary?: string;
  user_coping_summary?: string;
  employer_feedback_summary?: string;
  support_details?: string;
  future_support_policy?: string;
}

export interface A4PrintDocumentViewProps {
  snapshot?: DocumentSnapshot;
  documentType?: 'SUPPORT_PLAN' | 'RETENTION_SUPPORT_REPORT';
  documentId?: number;
  onClose?: () => void;
  consentInfo?: {
    signature_method: string;
    action: string;
    consent_timestamp?: string;
    evidence_file_url?: string;
  } | null;
}

export const A4PrintDocumentView: React.FC<A4PrintDocumentViewProps> = ({
  snapshot: propSnapshot,
  documentType,
  documentId,
  onClose,
  consentInfo: propConsentInfo,
}) => {
  const [snapshot, setSnapshot] = useState<DocumentSnapshot | null>(propSnapshot || null);
  const [consentInfo, setConsentInfo] = useState(propConsentInfo || null);
  const [loading, setLoading] = useState(!propSnapshot && !!documentType && !!documentId);
  const [fetchError, setFetchError] = useState<string | null>(null);

  useEffect(() => {
    if (propSnapshot) {
      setSnapshot(propSnapshot);
      return;
    }
    if (!documentType || !documentId) return;

    const fetchSnapshot = async () => {
      try {
        setLoading(true);
        setFetchError(null);
        const res = await apiClient.get(`/consents/documents/${documentType}/${documentId}/status`);
        if (res.data?.document_snapshot) {
          setSnapshot(res.data.document_snapshot);
        } else {
          // user-mypage rendered endpoint fallback
          const renderRes = await apiClient.get(`/user-mypage/documents/${documentType}/${documentId}/rendered`);
          setSnapshot(renderRes.data);
        }
        if (res.data?.consent) {
          setConsentInfo(res.data.consent);
        }
      } catch (err: any) {
        setFetchError(err?.response?.data?.msg || '帳票データの取得に失敗しました。');
      } finally {
        setLoading(false);
      }
    };

    fetchSnapshot();
  }, [propSnapshot, documentType, documentId]);

  const handlePrint = () => {
    window.print();
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-12 bg-white rounded-2xl shadow">
        <Loader2 className="w-8 h-8 text-indigo-600 animate-spin mb-2" />
        <p className="text-xs text-slate-500 font-medium">A4帳票データを読み込んでいます...</p>
      </div>
    );
  }

  if (fetchError || !snapshot) {
    return (
      <div className="p-8 bg-white rounded-2xl text-center">
        <p className="text-sm font-bold text-rose-600 mb-4">{fetchError || 'スナップショットが存在しません。確定済みであることを確認してください。'}</p>
        {onClose && (
          <button onClick={onClose} className="px-4 py-2 text-xs font-bold bg-slate-100 rounded-lg">
            閉じる
          </button>
        )}
      </div>
    );
  }

  const isRetentionPlan = snapshot.document_type === 'SUPPORT_PLAN' && snapshot.is_retention_plan;
  const isReport = snapshot.document_type === 'RETENTION_SUPPORT_REPORT';

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/80 backdrop-blur-sm flex flex-col items-center justify-start overflow-y-auto p-4 md:p-8 print:p-0 print:bg-white print:static">
      {/* ツールバー (印刷時は非表示) */}
      <div className="w-full max-w-4xl flex items-center justify-between bg-white px-6 py-3 rounded-2xl shadow-lg mb-6 print:hidden">
        <div className="flex items-center space-x-3">
          <FileText className="w-6 h-6 text-indigo-600" />
          <span className="font-bold text-slate-800 text-lg">
            {isReport
              ? `就労定着支援状況報告書 (${snapshot.report_year_month || ''})`
              : isRetentionPlan
              ? `就労定着支援計画書 (様式2) 第${snapshot.plan_version || 1}版`
              : `個別支援計画書 第${snapshot.plan_version || 1}版`}
          </span>
          {consentInfo && (
            <span className="inline-flex items-center text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
              <CheckCircle className="w-3.5 h-3.5 mr-1" />
              {consentInfo.signature_method === 'USER_DIGITAL' ? '本人電子署名済' : '紙署名証憑受領済'}
            </span>
          )}
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={handlePrint}
            className="flex items-center space-x-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-xl transition shadow-sm"
          >
            <Printer className="w-4 h-4" />
            <span>印刷 / PDF出力</span>
          </button>
          {onClose && (
            <button
              onClick={onClose}
              className="p-2 text-slate-400 hover:text-slate-600 rounded-xl hover:bg-slate-100 transition"
              aria-label="閉じる"
            >
              <X className="w-6 h-6" />
            </button>
          )}
        </div>
      </div>

      {/* A4 帳票本体 (A4縦: 210mm x 297mm 相当) */}
      <div className="w-full max-w-4xl bg-white p-8 md:p-12 shadow-2xl rounded-2xl print:shadow-none print:rounded-none print:p-0 text-slate-900 font-sans border border-slate-200 print:border-none min-h-[297mm]">
        {/* ============================================================== */}
        {/* 1. 就労定着支援計画 (別紙様式2) */}
        {/* ============================================================== */}
        {isRetentionPlan && (
          <div className="space-y-6 text-sm">
            <div className="text-center pb-2 border-b-2 border-slate-800">
              <p className="text-xs text-slate-500 text-right">別紙様式２</p>
              <h1 className="text-xl font-bold tracking-wider">就労定着支援計画書</h1>
              <div className="flex justify-between text-xs text-slate-600 mt-2">
                <span>計画作成日: {snapshot.created_at?.slice(0, 10) || '　　年　月　日'}</span>
                <span>計画期間: {snapshot.plan_start_date || '　　年　月　日'} 〜 {snapshot.plan_end_date || '　　年　月　日'}</span>
              </div>
            </div>

            {/* 利用者・雇用先情報 */}
            <table className="w-full border-collapse border border-slate-400 text-xs">
              <tbody>
                <tr>
                  <th className="border border-slate-400 bg-slate-100 p-2 w-28 text-left">利用者氏名</th>
                  <td className="border border-slate-400 p-2 font-medium">
                    {snapshot.retention_detail?.user_name || snapshot.user?.display_name}
                    {snapshot.retention_detail?.user_name_kana && (
                      <span className="text-slate-500 ml-2">({snapshot.retention_detail.user_name_kana})</span>
                    )}
                  </td>
                  <th className="border border-slate-400 bg-slate-100 p-2 w-28 text-left">生年月日 / 年齢</th>
                  <td className="border border-slate-400 p-2">
                    {snapshot.retention_detail?.birth_date || snapshot.user?.birth_date || '-'}
                    {snapshot.retention_detail?.age_at_planning ? ` (${snapshot.retention_detail.age_at_planning}歳)` : ''}
                  </td>
                </tr>
                <tr>
                  <th className="border border-slate-400 bg-slate-100 p-2 text-left">就職先企業名</th>
                  <td className="border border-slate-400 p-2 font-medium">
                    {snapshot.retention_detail?.employer_name || '-'}
                  </td>
                  <th className="border border-slate-400 bg-slate-100 p-2 text-left">就職年月日</th>
                  <td className="border border-slate-400 p-2">
                    {snapshot.retention_detail?.job_start_date || '-'}
                  </td>
                </tr>
                <tr>
                  <th className="border border-slate-400 bg-slate-100 p-2 text-left">事業所名</th>
                  <td className="border border-slate-400 p-2">
                    {snapshot.retention_detail?.office_name || snapshot.office?.office_name || '-'}
                  </td>
                  <th className="border border-slate-400 bg-slate-100 p-2 text-left">事業所番号</th>
                  <td className="border border-slate-400 p-2">
                    {snapshot.retention_detail?.office_number || '-'}
                  </td>
                </tr>
              </tbody>
            </table>

            {/* 全体目標 */}
            <div className="border border-slate-400 rounded p-3 bg-slate-50">
              <h2 className="font-bold text-xs text-slate-700 mb-1">【総合的な援助方針・大まかな支援目標】</h2>
              <p className="text-sm whitespace-pre-wrap">
                {snapshot.retention_detail?.overall_support_goal || '未設定'}
              </p>
            </div>

            {/* 支援内容・評価 表 (①〜③) */}
            <div>
              <h2 className="font-bold text-xs text-slate-700 mb-2">【具体的な課題・支援方針・支援内容】</h2>
              <table className="w-full border-collapse border border-slate-400 text-xs">
                <thead>
                  <tr className="bg-slate-100 text-center">
                    <th className="border border-slate-400 p-2 w-12">番号</th>
                    <th className="border border-slate-400 p-2 w-48">課題・ニーズ</th>
                    <th className="border border-slate-400 p-2">支援方針・内容</th>
                    <th className="border border-slate-400 p-2 w-28">期間・頻度</th>
                  </tr>
                </thead>
                <tbody>
                  {(snapshot.retention_detail?.items || []).length === 0 ? (
                    <tr>
                      <td colSpan={4} className="border border-slate-400 p-4 text-center text-slate-400">
                        支援項目の登録はありません
                      </td>
                    </tr>
                  ) : (
                    snapshot.retention_detail?.items?.map((it, idx) => (
                      <tr key={idx}>
                        <td className="border border-slate-400 p-2 text-center font-bold">{it.item_number || idx + 1}</td>
                        <td className="border border-slate-400 p-2 font-medium">{it.challenge_topic || '-'}</td>
                        <td className="border border-slate-400 p-2">
                          {it.support_policy && (
                            <div className="mb-1">
                              <span className="font-semibold text-slate-600">方針: </span>
                              {it.support_policy}
                            </div>
                          )}
                          {it.support_content && (
                            <div>
                              <span className="font-semibold text-slate-600">内容: </span>
                              {it.support_content}
                            </div>
                          )}
                        </td>
                        <td className="border border-slate-400 p-2 text-center">
                          <div>{it.support_period_start && it.support_period_end ? `${it.support_period_start}〜${it.support_period_end}` : '-'}</div>
                          <div className="text-slate-500 mt-1">{it.support_frequency || ''}</div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* 本人説明・同意署名欄 */}
            <div className="border border-slate-400 p-4 rounded mt-8">
              <p className="text-xs text-slate-700 leading-relaxed">
                上記計画の内容について説明を受け、同意いたしました。
              </p>
              <div className="flex justify-between items-end mt-6 text-xs">
                <div>
                  <p>説明日: {snapshot.sabikan_approved_at?.slice(0, 10) || '　　年　月　日'}</p>
                  <p className="mt-1">説明者 (サビ管): {snapshot.sabikan_name || '-'}</p>
                </div>
                <div className="w-64 border-b border-slate-800 pb-1 text-right">
                  <span className="text-slate-500 mr-4">署名欄</span>
                  <span className="font-bold text-sm">
                    {consentInfo
                      ? consentInfo.signature_method === 'USER_DIGITAL'
                        ? `${snapshot.user?.display_name || ''} (電子署名済)`
                        : `${snapshot.user?.display_name || ''} (受領済)`
                      : '_______________________ 印'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ============================================================== */}
        {/* 2. 就労定着支援レポート (別紙様式1) */}
        {/* ============================================================== */}
        {isReport && (
          <div className="space-y-6 text-sm">
            <div className="text-center pb-2 border-b-2 border-slate-800">
              <p className="text-xs text-slate-500 text-right">別紙様式１</p>
              <h1 className="text-xl font-bold tracking-wider">就労定着支援状況報告書</h1>
              <p className="text-sm text-slate-700 mt-1">対象月: {snapshot.report_year_month || '-'}</p>
            </div>

            <table className="w-full border-collapse border border-slate-400 text-xs">
              <tbody>
                <tr>
                  <th className="border border-slate-400 bg-slate-100 p-2 w-28 text-left">利用者氏名</th>
                  <td className="border border-slate-400 p-2 font-medium">
                    {snapshot.user?.display_name || '-'}
                  </td>
                  <th className="border border-slate-400 bg-slate-100 p-2 w-28 text-left">事業所名</th>
                  <td className="border border-slate-400 p-2">
                    {snapshot.office?.office_name || '-'}
                  </td>
                </tr>
              </tbody>
            </table>

            <div className="border border-slate-400 rounded p-3">
              <h2 className="font-bold text-xs text-slate-700 mb-1">【当月の主な支援目標】</h2>
              <p className="text-sm whitespace-pre-wrap">{snapshot.support_goal || '未設定'}</p>
            </div>

            <div className="border border-slate-400 rounded p-3">
              <h2 className="font-bold text-xs text-slate-700 mb-1">【就労・生活状況のまとめ】</h2>
              <p className="text-sm whitespace-pre-wrap">{snapshot.work_status_summary || '特記事項なし'}</p>
            </div>

            <div className="border border-slate-400 rounded p-3">
              <h2 className="font-bold text-xs text-slate-700 mb-1">【支援実施内容および結果】</h2>
              <p className="text-sm whitespace-pre-wrap">{snapshot.support_content || '未設定'}</p>
              {snapshot.support_result && (
                <div className="mt-2 pt-2 border-t border-slate-200">
                  <span className="font-semibold text-xs text-slate-600">結果: </span>
                  <p className="text-sm whitespace-pre-wrap">{snapshot.support_result}</p>
                </div>
              )}
            </div>

            <div className="border border-slate-400 rounded p-3">
              <h2 className="font-bold text-xs text-slate-700 mb-1">【今後の支援計画】</h2>
              <p className="text-sm whitespace-pre-wrap">{snapshot.future_support_plan || '未設定'}</p>
            </div>

            {/* 確認証跡欄 */}
            <div className="border border-slate-400 p-4 rounded mt-6 text-xs">
              <div className="flex justify-between items-center">
                <span>作成者: {snapshot.sabikan_name || '担当職員'}</span>
                <span>
                  本人確認状況: {consentInfo ? '確認済み' : '未確認'}
                  {consentInfo?.consent_timestamp && ` (${consentInfo.consent_timestamp.slice(0, 10)})`}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* ============================================================== */}
        {/* 3. 個別支援計画 (標準) */}
        {/* ============================================================== */}
        {!isRetentionPlan && !isReport && (
          <div className="space-y-6 text-sm">
            <div className="text-center pb-2 border-b-2 border-slate-800">
              <h1 className="text-xl font-bold tracking-wider">個別支援計画書</h1>
              <div className="flex justify-between text-xs text-slate-600 mt-2">
                <span>第 {snapshot.plan_version || 1} 版</span>
                <span>計画期間: {snapshot.plan_start_date || '-'} 〜 {snapshot.plan_end_date || '-'}</span>
              </div>
            </div>

            <table className="w-full border-collapse border border-slate-400 text-xs">
              <tbody>
                <tr>
                  <th className="border border-slate-400 bg-slate-100 p-2 w-28 text-left">利用者氏名</th>
                  <td className="border border-slate-400 p-2 font-medium">{snapshot.user?.display_name || '-'}</td>
                  <th className="border border-slate-400 bg-slate-100 p-2 w-28 text-left">事業所名</th>
                  <td className="border border-slate-400 p-2">{snapshot.office?.office_name || '-'}</td>
                </tr>
              </tbody>
            </table>

            {/* 目標一覧 */}
            <div className="space-y-4">
              {(snapshot.long_term_goals || []).map((ltg, idx) => (
                <div key={idx} className="border border-slate-400 rounded p-3">
                  <div className="font-bold text-xs text-indigo-900 mb-1">
                    長期目標 {idx + 1}: {ltg.goal_text}
                    {ltg.set_year_month && ltg.target_year_month && (
                      <span className="text-slate-500 font-normal ml-2">({ltg.set_year_month} 〜 {ltg.target_year_month})</span>
                    )}
                  </div>
                  <div className="pl-4 mt-2 space-y-2">
                    {(ltg.short_term_goals || []).map((stg, sIdx) => (
                      <div key={sIdx} className="text-xs text-slate-700 bg-slate-50 p-2 rounded border border-slate-200">
                        <span className="font-semibold text-slate-800">短期目標 {sIdx + 1}: </span>
                        {stg.goal_text}
                        {stg.set_year_month && stg.target_year_month && (
                          <span className="text-slate-500 ml-2">({stg.set_year_month} 〜 {stg.target_year_month})</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            {/* 署名欄 */}
            <div className="border border-slate-400 p-4 rounded mt-8">
              <p className="text-xs text-slate-700 leading-relaxed">
                上記計画の内容について説明を受け、同意いたしました。
              </p>
              <div className="flex justify-between items-end mt-6 text-xs">
                <div>
                  <p>説明日: {snapshot.sabikan_approved_at?.slice(0, 10) || '　　年　月　日'}</p>
                  <p className="mt-1">サービス管理責任者: {snapshot.sabikan_name || '-'}</p>
                </div>
                <div className="w-64 border-b border-slate-800 pb-1 text-right">
                  <span className="font-bold text-sm">
                    {consentInfo ? `${snapshot.user?.display_name || ''} (同意済)` : '_______________________ 印'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
