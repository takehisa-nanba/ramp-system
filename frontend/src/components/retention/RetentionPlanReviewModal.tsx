import React, { useState, useEffect } from 'react';
import { jobRetentionApi } from '../../services/jobRetentionApi';
import type {
  SupportPlan,
  SupportPlanSummary,
  PlanInputAssistanceData,
  RetentionSupportPlanItemData,
  RetentionSourceLinkData
} from '../../services/jobRetentionApi';
import { getLocalDateString, calculateDefaultPlanEndDate, calculateNextDay } from '../../utils/dateUtils';
import {
  X,
  Target,
  AlertTriangle,
  Save,
  Calendar,
  Building2,
  UserCheck,
  FileText,
  Sparkles,
  Quote,
  CheckCircle2,
  Plus,
  Trash2,
  Layers
} from 'lucide-react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  contractId: number;
  userName: string;
  activePlan?: SupportPlanSummary | SupportPlan | null;
  onSaved: (newPlan: SupportPlan) => void;
}

export const RetentionPlanReviewModal: React.FC<Props> = ({
  isOpen,
  onClose,
  contractId,
  userName,
  activePlan,
  onSaved,
}) => {
  const isReview = Boolean(activePlan);
  const today = getLocalDateString();

  // タブ切り替え: 'assistance' (一次情報・確定事実) | 'form2' (様式2支援内容) | 'summary' (期間・日常目標)
  const [activeTab, setActiveTab] = useState<'assistance' | 'form2' | 'summary'>('assistance');

  // 入力支援データ
  const [assistanceData, setAssistanceData] = useState<PlanInputAssistanceData | null>(null);
  const [loadingAssistance, setLoadingAssistance] = useState(false);

  // フォームステート
  const [startDate, setStartDate] = useState(today);
  const [planEndDate, setPlanEndDate] = useState('');
  const [maxEndDate, setMaxEndDate] = useState('');
  const [reviewReason, setReviewReason] = useState('');
  const [overallGoal, setOverallGoal] = useState('');

  // 厚労省様式2 固有項目スナップショット
  const [physicalEnv, setPhysicalEnv] = useState('');
  const [humanEnv, setHumanEnv] = useState('');
  const [userWishes, setUserWishes] = useState('');
  const [healthCond, setHealthCond] = useState('');
  const [relatedOrgs, setRelatedOrgs] = useState('');

  // 支援内容・評価テーブル (①〜③)
  const [items, setItems] = useState<RetentionSupportPlanItemData[]>([
    {
      item_number: 1,
      challenge_topic: '',
      support_policy: '',
      support_content: '',
      support_frequency: '月1回以上',
      role_sharing: ''
    }
  ]);

  // 出所追跡リンク
  const [sourceLinks, setSourceLinks] = useState<RetentionSourceLinkData[]>([]);

  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // 初期化と入力支援データフェッチ
  useEffect(() => {
    if (isOpen) {
      setActiveTab('assistance');
      setErrorMsg(null);

      // 日付初期化
      if (isReview && activePlan) {
        const prevEnd = activePlan.plan_end_date || activePlan.next_review_deadline;
        const defaultStart = (prevEnd && today > prevEnd) ? calculateNextDay(prevEnd) : today;
        setStartDate(defaultStart);
        const calculatedMax = calculateDefaultPlanEndDate(defaultStart);
        setMaxEndDate(calculatedMax);
        setPlanEndDate(calculatedMax);
        setOverallGoal(activePlan.overall_support_goal || '');
        setReviewReason('');
      } else {
        setStartDate(today);
        const calculatedMax = calculateDefaultPlanEndDate(today);
        setMaxEndDate(calculatedMax);
        setPlanEndDate(calculatedMax);
        setOverallGoal('');
        setReviewReason('初回策定');
      }

      // 入力支援データ取得
      setLoadingAssistance(true);
      jobRetentionApi.getPlanAssistanceData(contractId)
        .then((data) => {
          setAssistanceData(data);
          // 確定事実から初期値を補完
          if (data.employment_info_snapshot) {
            setPhysicalEnv(data.employment_info_snapshot.physical_work_environment || '');
            setHumanEnv(data.employment_info_snapshot.human_work_environment || '');
            setRelatedOrgs(data.employment_info_snapshot.related_support_organizations || '');
          }
        })
        .catch((err) => {
          console.error('入力支援データ取得エラー:', err);
        })
        .finally(() => {
          setLoadingAssistance(false);
        });
    }
  }, [isOpen, activePlan, isReview, contractId]);

  // 開始日変更時に上限終了予定日を再計算
  const handleStartDateChange = (newDate: string) => {
    setStartDate(newDate);
    if (newDate) {
      const calculatedMax = calculateDefaultPlanEndDate(newDate);
      setMaxEndDate(calculatedMax);
      setPlanEndDate(calculatedMax);
    }
  };

  // 一次情報引用ハンドラー
  const handleAdoptVoiceAsTopic = (candidate: { id: number; content: string; source_type: string }) => {
    const updated = [...items];
    if (updated.length > 0) {
      updated[0].challenge_topic = candidate.content;
      setItems(updated);
    }
    setSourceLinks((prev) => [
      ...prev,
      {
        target_field: 'items[0].challenge_topic',
        source_type: candidate.source_type,
        source_id: candidate.id,
        excerpt_text: candidate.content
      }
    ]);
  };

  const handleAdoptVoiceAsWishes = (candidate: { id: number; content: string; source_type: string }) => {
    setUserWishes(candidate.content);
    setSourceLinks((prev) => [
      ...prev,
      {
        target_field: 'situation_info.user_wishes',
        source_type: candidate.source_type,
        source_id: candidate.id,
        excerpt_text: candidate.content
      }
    ]);
  };

  const handleAdoptFeedbackAsEnv = (candidate: { id: number; content: string; source_type: string }) => {
    setHumanEnv((prev) => (prev ? `${prev} / ${candidate.content}` : candidate.content));
    setSourceLinks((prev) => [
      ...prev,
      {
        target_field: 'employment_info.human_work_environment',
        source_type: candidate.source_type,
        source_id: candidate.id,
        excerpt_text: candidate.content
      }
    ]);
  };

  const handleAdoptAsOverallGoal = (text: string) => {
    setOverallGoal(text);
  };

  // アイテム行追加・削除
  const handleAddItem = () => {
    if (items.length >= 3) return; // 厚労省様式は原則①〜③
    setItems((prev) => [
      ...prev,
      {
        item_number: prev.length + 1,
        challenge_topic: '',
        support_policy: '',
        support_content: '',
        support_frequency: '月1回以上',
        role_sharing: ''
      }
    ]);
  };

  const handleRemoveItem = (index: number) => {
    if (items.length <= 1) return;
    const next = items.filter((_, idx) => idx !== index).map((it, idx) => ({ ...it, item_number: idx + 1 }));
    setItems(next);
  };

  const handleItemChange = (index: number, field: keyof RetentionSupportPlanItemData, val: any) => {
    const updated = [...items];
    updated[index] = { ...updated[index], [field]: val };
    setItems(updated);
  };

  if (!isOpen) return null;

  // 上限チェック (原則 6か月 - 1日)
  const isOverdueMax = Boolean(planEndDate && maxEndDate && planEndDate > maxEndDate);
  const nextPlanStartDate = planEndDate ? calculateNextDay(planEndDate) : '';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!overallGoal.trim()) {
      setActiveTab('summary');
      setErrorMsg('「日常支援用サマリー（大まかな支援目標）」は必須です。');
      return;
    }
    if (!startDate) {
      setActiveTab('summary');
      setErrorMsg('「計画開始日」は必須です。');
      return;
    }
    if (!planEndDate) {
      setActiveTab('summary');
      setErrorMsg('「計画終了予定日」は必須です。');
      return;
    }
    if (isOverdueMax) {
      setActiveTab('summary');
      setErrorMsg(`計画終了予定日は開始日（${startDate}）から6か月以内（上限: ${maxEndDate}）である必要があります。`);
      return;
    }
    if (isReview && !reviewReason.trim()) {
      setActiveTab('summary');
      setErrorMsg('随時見直しを行う際は、「見直し契機・理由」を必ず記録してください。');
      return;
    }

    try {
      setSubmitting(true);
      setErrorMsg(null);

      const res = await jobRetentionApi.createOrReviewSupportPlan(contractId, {
        overall_support_goal: overallGoal.trim(),
        start_date: startDate,
        plan_end_date: planEndDate,
        next_review_deadline: planEndDate,
        review_date: today,
        review_reason: reviewReason.trim(),
        items_data: items.map((it) => ({
          ...it,
          support_period_start: it.support_period_start || startDate,
          support_period_end: it.support_period_end || planEndDate
        })),
        source_links_data: sourceLinks,
        detail_fields: {
          physical_work_environment: physicalEnv,
          human_work_environment: humanEnv,
          user_wishes: userWishes,
          health_condition: healthCond,
          related_support_organizations: relatedOrgs
        }
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
      <div className="bg-white w-full max-w-4xl rounded-2xl shadow-2xl border border-slate-100 flex flex-col overflow-hidden my-4 max-h-[90vh]">
        {/* モーダルヘッダー */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-gradient-to-r from-indigo-50/70 via-white to-sky-50/70">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-indigo-600 text-white rounded-xl shadow-xs">
              <Target className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-800 flex items-center gap-2">
                {isReview
                  ? `就労定着支援計画の随時見直し（第${(activePlan?.version || 1) + 1}版作成）`
                  : '就労定着支援計画（別紙様式2）の新規策定'}
              </h2>
              <p className="text-xs text-slate-500">
                対象者: <span className="font-semibold text-slate-700">{userName}</span> ｜ 厚労省通知・別紙様式2完全準拠
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

        {/* タブナビゲーション */}
        <div className="px-6 pt-3 pb-1 border-b border-slate-100 bg-slate-50/50 flex gap-2">
          <button
            type="button"
            onClick={() => setActiveTab('assistance')}
            className={`px-4 py-2 text-xs font-bold rounded-lg transition-all flex items-center gap-1.5 ${
              activeTab === 'assistance'
                ? 'bg-white text-indigo-700 shadow-xs border border-indigo-100'
                : 'text-slate-600 hover:text-slate-800 hover:bg-white/60'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            1. 確定事実・一次情報候補
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('form2')}
            className={`px-4 py-2 text-xs font-bold rounded-lg transition-all flex items-center gap-1.5 ${
              activeTab === 'form2'
                ? 'bg-white text-indigo-700 shadow-xs border border-indigo-100'
                : 'text-slate-600 hover:text-slate-800 hover:bg-white/60'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            2. 公式様式2: 支援内容・評価
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('summary')}
            className={`px-4 py-2 text-xs font-bold rounded-lg transition-all flex items-center gap-1.5 ${
              activeTab === 'summary'
                ? 'bg-white text-indigo-700 shadow-xs border border-indigo-100'
                : 'text-slate-600 hover:text-slate-800 hover:bg-white/60'
            }`}
          >
            <Calendar className="w-3.5 h-3.5" />
            3. 期間・日常支援サマリー
          </button>
        </div>

        {/* フォーム本文 */}
        <form onSubmit={handleSubmit} className="p-6 overflow-y-auto space-y-5 flex-1">
          {errorMsg && (
            <div className="p-3.5 bg-rose-50 border border-rose-200 text-rose-700 rounded-xl text-xs flex items-start gap-2.5">
              <AlertTriangle className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
              <div>{errorMsg}</div>
            </div>
          )}

          {/* ============================================================
              TAB 1: 確定事実の確認と一次情報候補の参照
             ============================================================ */}
          {activeTab === 'assistance' && (
            <div className="space-y-5">
              <div className="bg-sky-50/60 border border-sky-100 p-3 rounded-xl text-xs text-sky-800 flex items-start gap-2">
                <Sparkles className="w-4 h-4 text-sky-600 shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold">事実と判断の分離：</span>
                  RAMPSystemに蓄積された事実（基本情報・エピソード）を自動表示しています。
                  本人の生の声や企業フィードバックから支援課題・方針へ引用できます。
                </div>
              </div>

              {/* 1. 確定事実カード (再入力不要) */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-3.5 space-y-2">
                  <div className="flex items-center gap-2 text-xs font-bold text-slate-700 border-b border-slate-200 pb-1.5">
                    <UserCheck className="w-4 h-4 text-indigo-600" />
                    利用者基本情報（自動取得）
                  </div>
                  <div className="text-xs space-y-1 text-slate-600">
                    <p><span className="text-slate-400">氏名:</span> {assistanceData?.user_info_snapshot.user_name || userName}</p>
                    <p><span className="text-slate-400">性別 / 年齢:</span> {assistanceData?.user_info_snapshot.gender || '未設定'} / {assistanceData?.user_info_snapshot.age_at_planning ?? '未設定'}歳</p>
                    <p><span className="text-slate-400">区分 / 手帳:</span> {assistanceData?.user_info_snapshot.support_level} / {assistanceData?.user_info_snapshot.disability_handbook_type}</p>
                  </div>
                </div>

                <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-3.5 space-y-2">
                  <div className="flex items-center gap-2 text-xs font-bold text-slate-700 border-b border-slate-200 pb-1.5">
                    <Building2 className="w-4 h-4 text-indigo-600" />
                    雇用先・労働条件（自動取得）
                  </div>
                  <div className="text-xs space-y-1 text-slate-600">
                    <p><span className="text-slate-400">企業名:</span> {assistanceData?.employment_info_snapshot.employer_name || '未登録'}</p>
                    <p><span className="text-slate-400">職種:</span> {assistanceData?.employment_info_snapshot.work_content || '未設定'}</p>
                    <p><span className="text-slate-400">就職日:</span> {assistanceData?.employment_info_snapshot.job_start_date || '未設定'}</p>
                  </div>
                </div>
              </div>

              {/* 2. 一次情報候補カード */}
              <div className="space-y-3">
                <div className="text-xs font-bold text-slate-700 flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <Quote className="w-4 h-4 text-amber-500" />
                    直近の一次情報ログ（引用可能）
                  </span>
                  <span className="text-[11px] text-slate-400 font-normal">
                    クリックで様式2の各項目へ反映できます
                  </span>
                </div>

                {loadingAssistance ? (
                  <div className="text-xs text-slate-400 py-6 text-center">候補データを読み込み中...</div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {/* 本人の声 */}
                    <div className="border border-slate-200 rounded-xl p-3 bg-white space-y-2">
                      <div className="text-xs font-bold text-slate-800 flex items-center gap-1.5 text-amber-700">
                        本人の生の声（困りごと・希望）
                      </div>
                      {assistanceData?.candidates.voice_candidates.length ? (
                        assistanceData.candidates.voice_candidates.map((vc) => (
                          <div key={vc.id} className="p-2 bg-amber-50/40 rounded-lg text-xs space-y-1.5 border border-amber-100">
                            <p className="text-slate-700 font-medium">{vc.content}</p>
                            <div className="flex gap-2 pt-1 border-t border-amber-200/50">
                              <button
                                type="button"
                                onClick={() => handleAdoptVoiceAsTopic(vc)}
                                className="text-[11px] px-2 py-0.5 bg-amber-100 text-amber-800 rounded hover:bg-amber-200 font-medium transition"
                              >
                                ①支援課題に引用
                              </button>
                              <button
                                type="button"
                                onClick={() => handleAdoptVoiceAsWishes(vc)}
                                className="text-[11px] px-2 py-0.5 bg-slate-100 text-slate-700 rounded hover:bg-slate-200 font-medium transition"
                              >
                                本人希望に引用
                              </button>
                            </div>
                          </div>
                        ))
                      ) : (
                        <p className="text-[11px] text-slate-400">登録された本人の声はありません。</p>
                      )}
                    </div>

                    {/* 企業フィードバック */}
                    <div className="border border-slate-200 rounded-xl p-3 bg-white space-y-2">
                      <div className="text-xs font-bold text-slate-800 flex items-center gap-1.5 text-indigo-700">
                        企業フィードバック（職場の様子）
                      </div>
                      {assistanceData?.candidates.feedback_candidates.length ? (
                        assistanceData.candidates.feedback_candidates.map((fc) => (
                          <div key={fc.id} className="p-2 bg-indigo-50/40 rounded-lg text-xs space-y-1.5 border border-indigo-100">
                            <p className="text-slate-700 font-medium">{fc.content}</p>
                            <div className="flex gap-2 pt-1 border-t border-indigo-200/50">
                              <button
                                type="button"
                                onClick={() => handleAdoptFeedbackAsEnv(fc)}
                                className="text-[11px] px-2 py-0.5 bg-indigo-100 text-indigo-800 rounded hover:bg-indigo-200 font-medium transition"
                              >
                                人的環境に引用
                              </button>
                              <button
                                type="button"
                                onClick={() => handleAdoptAsOverallGoal(fc.content)}
                                className="text-[11px] px-2 py-0.5 bg-slate-100 text-slate-700 rounded hover:bg-slate-200 font-medium transition"
                              >
                                日常目標に引用
                              </button>
                            </div>
                          </div>
                        ))
                      ) : (
                        <p className="text-[11px] text-slate-400">登録された企業フィードバックはありません。</p>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* 次へボタン */}
              <div className="pt-2 flex justify-end">
                <button
                  type="button"
                  onClick={() => setActiveTab('form2')}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-xl text-xs font-bold hover:bg-indigo-700 transition"
                >
                  次へ: 様式2 支援内容の入力 →
                </button>
              </div>
            </div>
          )}

          {/* ============================================================
              TAB 2: 厚労省様式2 支援内容・評価
             ============================================================ */}
          {activeTab === 'form2' && (
            <div className="space-y-5">
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 text-xs text-slate-700">
                <p className="font-bold mb-1">厚労省別紙様式2「支援内容・評価」項目</p>
                <p className="text-slate-500">
                  課題・ニーズごとに支援方針・支援内容・期間・頻度を構造化して登録します（最大3項目）。
                  入力内容は共通の短期目標（ShortTermGoal）と接続されます。
                </p>
              </div>

              {/* スナップショット補足情報 */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                <div>
                  <label className="block text-slate-600 font-bold mb-1">職場環境（物理的環境）</label>
                  <input
                    type="text"
                    value={physicalEnv}
                    onChange={(e) => setPhysicalEnv(e.target.value)}
                    placeholder="例: 空調完備の執務スペース、休憩室近接"
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
                <div>
                  <label className="block text-slate-600 font-bold mb-1">職場環境（人的環境）</label>
                  <input
                    type="text"
                    value={humanEnv}
                    onChange={(e) => setHumanEnv(e.target.value)}
                    placeholder="例: 指導担当者隣席配置、復唱確認ルール"
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
                <div>
                  <label className="block text-slate-600 font-bold mb-1">本人の希望・意向</label>
                  <input
                    type="text"
                    value={userWishes}
                    onChange={(e) => setUserWishes(e.target.value)}
                    placeholder="例: 長く安定して勤務を継続したい"
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
                <div>
                  <label className="block text-slate-600 font-bold mb-1">健康状態・体調面</label>
                  <input
                    type="text"
                    value={healthCond}
                    onChange={(e) => setHealthCond(e.target.value)}
                    placeholder="例: 服薬管理良好、睡眠時間7時間確保"
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-slate-600 font-bold mb-1">関係支援機関</label>
                  <input
                    type="text"
                    value={relatedOrgs}
                    onChange={(e) => setRelatedOrgs(e.target.value)}
                    placeholder="例: ハローワーク、地域障害者職業センター"
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
              </div>

              {/* 支援内容・評価アイテム リスト */}
              <div className="space-y-4 pt-2">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                    <Layers className="w-4 h-4 text-indigo-600" />
                    支援内容・計画項目（①〜③）
                  </h3>
                  {items.length < 3 && (
                    <button
                      type="button"
                      onClick={handleAddItem}
                      className="px-2.5 py-1 text-xs bg-indigo-50 text-indigo-700 rounded-lg hover:bg-indigo-100 font-bold flex items-center gap-1 transition"
                    >
                      <Plus className="w-3.5 h-3.5" /> 項目を追加
                    </button>
                  )}
                </div>

                {items.map((it, idx) => (
                  <div key={idx} className="border border-slate-200 rounded-xl p-3.5 bg-slate-50/40 space-y-3 relative">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold px-2 py-0.5 bg-indigo-100 text-indigo-800 rounded-md">
                        様式2 項目 {it.item_number}
                      </span>
                      {items.length > 1 && (
                        <button
                          type="button"
                          onClick={() => handleRemoveItem(idx)}
                          className="text-slate-400 hover:text-rose-600 p-1 transition"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                      <div>
                        <label className="block text-slate-600 font-medium mb-1">課題・ニーズ</label>
                        <input
                          type="text"
                          value={it.challenge_topic || ''}
                          onChange={(e) => handleItemChange(idx, 'challenge_topic', e.target.value)}
                          placeholder="例: 通勤ラッシュ時の疲労軽減"
                          className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-white text-xs"
                        />
                      </div>
                      <div>
                        <label className="block text-slate-600 font-medium mb-1">支援頻度</label>
                        <input
                          type="text"
                          value={it.support_frequency || ''}
                          onChange={(e) => handleItemChange(idx, 'support_frequency', e.target.value)}
                          placeholder="例: 月1回面談、週1回メール確認"
                          className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-white text-xs"
                        />
                      </div>
                      <div>
                        <label className="block text-slate-600 font-medium mb-1">支援方針</label>
                        <textarea
                          rows={2}
                          value={it.support_policy || ''}
                          onChange={(e) => handleItemChange(idx, 'support_policy', e.target.value)}
                          placeholder="例: 時差出勤を活用し、体調変化の早期察知と自己対処を定着させる"
                          className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-white text-xs"
                        />
                      </div>
                      <div>
                        <label className="block text-slate-600 font-medium mb-1">支援内容</label>
                        <textarea
                          rows={2}
                          value={it.support_content || ''}
                          onChange={(e) => handleItemChange(idx, 'support_content', e.target.value)}
                          placeholder="例: 月次面談での睡眠・疲労度確認、企業担当者との連絡調整"
                          className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-white text-xs"
                        />
                      </div>
                      <div className="md:col-span-2">
                        <label className="block text-slate-600 font-medium mb-1">関係者の役割分担</label>
                        <input
                          type="text"
                          value={it.role_sharing || ''}
                          onChange={(e) => handleItemChange(idx, 'role_sharing', e.target.value)}
                          placeholder="例: 本人: 体調記録 / 企業: 勤務時間配慮 / 支援員: 月次モニタリング"
                          className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-white text-xs"
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* ナビゲーションボタン */}
              <div className="pt-2 flex justify-between">
                <button
                  type="button"
                  onClick={() => setActiveTab('assistance')}
                  className="px-4 py-2 border border-slate-200 text-slate-600 rounded-xl text-xs font-bold hover:bg-slate-100 transition"
                >
                  ← 一次情報候補に戻る
                </button>
                <button
                  type="button"
                  onClick={() => {
                    // Item 1の支援方針が入力されており、overallGoalが未設定なら初期提案
                    if (!overallGoal && items[0]?.support_policy) {
                      setOverallGoal(items[0].support_policy);
                    }
                    setActiveTab('summary');
                  }}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-xl text-xs font-bold hover:bg-indigo-700 transition"
                >
                  次へ: 期間と日常サマリー →
                </button>
              </div>
            </div>
          )}

          {/* ============================================================
              TAB 3: 計画期間と日常支援サマリー
             ============================================================ */}
          {activeTab === 'summary' && (
            <div className="space-y-5">
              {/* 期間設定 */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1.5 flex items-center gap-1.5">
                    <Calendar className="w-3.5 h-3.5 text-slate-500" />
                    計画開始日 <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="date"
                    required
                    value={startDate}
                    onChange={(e) => handleStartDateChange(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 font-medium focus:bg-white focus:ring-2 focus:ring-indigo-500 transition"
                  />
                  <p className="text-[11px] text-slate-400 mt-1">当該計画版の適用開始日</p>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1.5 flex items-center gap-1.5">
                    <Calendar className="w-3.5 h-3.5 text-slate-500" />
                    計画終了予定日 <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="date"
                    required
                    value={planEndDate}
                    onChange={(e) => setPlanEndDate(e.target.value)}
                    className={`w-full px-3.5 py-2.5 bg-slate-50 border rounded-xl text-xs font-medium focus:bg-white focus:ring-2 transition ${
                      isOverdueMax ? 'border-rose-300 text-rose-800 focus:ring-rose-500' : 'border-slate-200 text-slate-800 focus:ring-indigo-500'
                    }`}
                  />
                  <div className="flex items-center justify-between text-[11px] mt-1">
                    <span className="text-slate-400">
                      原則: 開始日 + 6か月 - 1日（上限: <span className="font-semibold text-slate-600">{maxEndDate}</span>）
                    </span>
                    {nextPlanStartDate && (
                      <span className="text-indigo-600 font-medium">次期開始: {nextPlanStartDate}</span>
                    )}
                  </div>
                </div>
              </div>

              {/* 随時見直し理由（見直し時必須） */}
              {isReview && (
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1.5">
                    見直し契機・理由 <span className="text-rose-500">*</span>
                  </label>
                  <textarea
                    rows={2}
                    required
                    value={reviewReason}
                    onChange={(e) => setReviewReason(e.target.value)}
                    placeholder="例: 職場の業務変更に伴う疲労増大への配慮、本人の体調安定に伴う通所頻度変更など"
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 focus:bg-white focus:ring-2 focus:ring-indigo-500 transition"
                  />
                  <p className="text-[11px] text-slate-400 mt-1">
                    随時見直しを行った背景・契機を記録します（Detailに保持され監査証跡となります）。
                  </p>
                </div>
              )}

              {/* 日常支援用サマリー（大まかな支援目標） */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-bold text-slate-700">
                    日常支援用サマリー（大まかな支援目標） <span className="text-rose-500">*</span>
                  </label>
                  {items[0]?.support_policy && (
                    <button
                      type="button"
                      onClick={() => setOverallGoal(items[0].support_policy || '')}
                      className="text-[11px] text-indigo-600 hover:text-indigo-800 font-medium"
                    >
                      様式2項目①からコピー
                    </button>
                  )}
                </div>
                <textarea
                  rows={3}
                  required
                  value={overallGoal}
                  onChange={(e) => setOverallGoal(e.target.value)}
                  placeholder="例: 職場環境に慣れ、体調を安定させて週5日勤務を継続する"
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 focus:bg-white focus:ring-2 focus:ring-indigo-500 transition"
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  スタッフ画面やダッシュボードで常時確認される総合サマリーです（共通Goalモデルに格納）。
                </p>
              </div>

              {/* ナビゲーションボタン */}
              <div className="pt-2 flex justify-between">
                <button
                  type="button"
                  onClick={() => setActiveTab('form2')}
                  className="px-4 py-2 border border-slate-200 text-slate-600 rounded-xl text-xs font-bold hover:bg-slate-100 transition"
                >
                  ← 様式2 支援内容に戻る
                </button>
              </div>
            </div>
          )}

          {/* モーダルフッター */}
          <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              <span>確定時に計画書スナップショットが固定保存されます</span>
            </div>
            <div className="flex items-center gap-2.5">
              <button
                type="button"
                onClick={onClose}
                disabled={submitting}
                className="px-4 py-2 border border-slate-200 text-slate-600 rounded-xl text-xs font-bold hover:bg-slate-50 transition"
              >
                キャンセル
              </button>
              <button
                type="submit"
                disabled={submitting || isOverdueMax}
                className="px-5 py-2.5 bg-indigo-600 text-white rounded-xl text-xs font-bold hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-1.5 shadow-xs transition"
              >
                <Save className="w-4 h-4" />
                {submitting ? '保存中...' : isReview ? '見直し計画を確定する' : '計画を新規策定する'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
