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

  // 共通Goalモデル（厚労省様式2 長期・短期目標）
  const [ltgDescription, setLtgDescription] = useState('');
  const [ltgSetYm, setLtgSetYm] = useState('');
  const [ltgTargetYm, setLtgTargetYm] = useState('');
  const [stgDescription, setStgDescription] = useState('');
  const [stgSetYm, setStgSetYm] = useState('');
  const [stgTargetYm, setStgTargetYm] = useState('');

  // 労働条件4項目（様式2公式）
  const [employmentType, setEmploymentType] = useState('');
  const [wageCondition, setWageCondition] = useState('');
  const [holidayCondition, setHolidayCondition] = useState('');
  const [workingHoursAndBreak, setWorkingHoursAndBreak] = useState('');

  // 就職前引継・生活面サポート体制
  const [preEmploymentHandover, setPreEmploymentHandover] = useState('');
  const [livingEnvSupport, setLivingEnvSupport] = useState('');

  // 厚労省様式2 固有項目スナップショット
  const [physicalEnv, setPhysicalEnv] = useState('');
  const [humanEnv, setHumanEnv] = useState('');
  const [userWishes, setUserWishes] = useState('');
  const [healthCond, setHealthCond] = useState('');
  const [relatedOrgs, setRelatedOrgs] = useState('');

  // 本人への説明・同意に必要な項目
  const [explainedDate, setExplainedDate] = useState('');
  const [agreedDate, setAgreedDate] = useState('');
  const [consentConfirmed, setConsentConfirmed] = useState(false);
  const [consentNotes, setConsentNotes] = useState('');
  const [staffExplainerName, setStaffExplainerName] = useState('');

  // 確定事実スナップショット（様式2公式項目・要件1）
  const [snapshotUserName, setSnapshotUserName] = useState('');
  const [snapshotUserNameKana, setSnapshotUserNameKana] = useState('');
  const [snapshotGender, setSnapshotGender] = useState('');
  const [snapshotBirthDate, setSnapshotBirthDate] = useState('');
  const [snapshotAge, setSnapshotAge] = useState<number | null>(null);
  const [snapshotSupportLevel, setSnapshotSupportLevel] = useState('');
  const [snapshotHandbookType, setSnapshotHandbookType] = useState(''); // 要件2: 身体／療育／精神（等級から推測しない）

  const [snapshotEmployerName, setSnapshotEmployerName] = useState('');
  const [snapshotEmployerIndustry, setSnapshotEmployerIndustry] = useState('');
  const [snapshotEmployerAddress, setSnapshotEmployerAddress] = useState('');
  const [snapshotEmployerTel, setSnapshotEmployerTel] = useState('');
  const [snapshotEmployerContactPerson, setSnapshotEmployerContactPerson] = useState('');
  const [snapshotJobStartDate, setSnapshotJobStartDate] = useState('');
  const [snapshotWorkContent, setSnapshotWorkContent] = useState('');

  const [snapshotOfficeName, setSnapshotOfficeName] = useState('');
  const [snapshotOfficeNumber, setSnapshotOfficeNumber] = useState('');
  const [snapshotOfficeAddress, setSnapshotOfficeAddress] = useState('');
  const [snapshotOfficeTel, setSnapshotOfficeTel] = useState('');
  const [snapshotOfficeFax, setSnapshotOfficeFax] = useState('');

  // 支援内容・評価テーブル (①〜③)
  const [items, setItems] = useState<RetentionSupportPlanItemData[]>([
    {
      item_number: 1,
      challenge_topic: '',
      support_policy: '',
      support_content: '',
      support_period_start: '',
      support_period_end: '',
      support_frequency: '',
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
        const startYm = defaultStart.slice(0, 7);
        const endYm = calculatedMax.slice(0, 7);
        setLtgSetYm(startYm);
        setLtgTargetYm(endYm);
        setStgSetYm(startYm);
        setStgTargetYm(endYm);
      } else {
        setStartDate(today);
        const calculatedMax = calculateDefaultPlanEndDate(today);
        setMaxEndDate(calculatedMax);
        setPlanEndDate(calculatedMax);
        setOverallGoal('');
        setReviewReason(''); // 初回は見直し理由なし (要件6)
        const startYm = today.slice(0, 7);
        const endYm = calculatedMax.slice(0, 7);
        setLtgSetYm(startYm);
        setLtgTargetYm(endYm);
        setStgSetYm(startYm);
        setStgTargetYm(endYm);
      }

      // 入力支援データ取得
      setLoadingAssistance(true);
      jobRetentionApi.getPlanAssistanceData(contractId)
        .then((data) => {
          setAssistanceData(data);
          // 1. 利用者基本情報確定事実スナップショット初期化
          const u = data.user_info_snapshot;
          if (u) {
            setSnapshotUserName(u.user_name || userName || '');
            setSnapshotUserNameKana(u.user_name_kana || '');
            setSnapshotGender(u.gender || '');
            setSnapshotBirthDate(u.birth_date || '');
            setSnapshotAge(u.age_at_planning ?? null);
            setSnapshotSupportLevel(u.support_level || '');
            // 要件2: 手帳種別（身体／療育／精神）は等級から推測しない
            setSnapshotHandbookType(u.disability_handbook_type || '');
          }

          // 2. 雇用先・就労事実スナップショット初期化
          const em = data.employment_info_snapshot;
          if (em) {
            setSnapshotEmployerName(em.employer_name || '');
            setSnapshotEmployerIndustry(em.employer_industry || '');
            setSnapshotEmployerAddress(em.employer_address || '');
            setSnapshotEmployerTel(em.employer_tel || '');
            setSnapshotEmployerContactPerson(em.employer_contact_person || '');
            setSnapshotJobStartDate(em.job_start_date || '');
            setSnapshotWorkContent(em.work_content || '');

            if (em.physical_work_environment) setPhysicalEnv(em.physical_work_environment);
            if (em.human_work_environment) setHumanEnv(em.human_work_environment);
            if (em.related_support_organizations) setRelatedOrgs(em.related_support_organizations);
            if (em.employment_type) setEmploymentType(em.employment_type);
            if (em.wage_condition) setWageCondition(em.wage_condition);
            if (em.holiday_condition) setHolidayCondition(em.holiday_condition);
            if (em.working_hours_and_break) setWorkingHoursAndBreak(em.working_hours_and_break);
          }

          // 3. 事業所スナップショット初期化
          const off = data.office_info_snapshot;
          if (off) {
            setSnapshotOfficeName(off.office_name || '');
            setSnapshotOfficeNumber(off.office_number || '');
            setSnapshotOfficeAddress(off.office_address || '');
            setSnapshotOfficeTel(off.office_tel || '');
            setSnapshotOfficeFax(off.office_fax || '');
          }
        })
        .catch((err) => {
          console.error('入力支援データ取得エラー:', err);
        })
        .finally(() => {
          setLoadingAssistance(false);
        });
    }
  }, [isOpen, activePlan, isReview, contractId, userName]);

  // 開始日変更時に上限終了予定日を再計算
  const handleStartDateChange = (newDate: string) => {
    setStartDate(newDate);
    if (newDate) {
      const calculatedMax = calculateDefaultPlanEndDate(newDate);
      setMaxEndDate(calculatedMax);
      setPlanEndDate(calculatedMax);
      const startYm = newDate.slice(0, 7);
      const endYm = calculatedMax.slice(0, 7);
      if (!ltgSetYm) setLtgSetYm(startYm);
      if (!ltgTargetYm) setLtgTargetYm(endYm);
      if (!stgSetYm) setStgSetYm(startYm);
      if (!stgTargetYm) setStgTargetYm(endYm);
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

  const handleAdoptWorkConditions = (targetField: 'employmentType' | 'wage' | 'holiday' | 'hours', val: string) => {
    if (targetField === 'employmentType') setEmploymentType(val);
    else if (targetField === 'wage') setWageCondition(val);
    else if (targetField === 'holiday') setHolidayCondition(val);
    else if (targetField === 'hours') setWorkingHoursAndBreak(val);
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
        support_frequency: '',
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

      // 有効な入力があるアイテムのみ送信 (要件3: support_period_start / end を自動補完しない)
      const validItems = items.filter(
        (it) => (it.challenge_topic && it.challenge_topic.trim()) ||
                (it.support_policy && it.support_policy.trim()) ||
                (it.support_content && it.support_content.trim())
      ).map((it) => ({
        ...it,
        support_period_start: it.support_period_start ? it.support_period_start : undefined,
        support_period_end: it.support_period_end ? it.support_period_end : undefined
      }));

      const res = await jobRetentionApi.createOrReviewSupportPlan(contractId, {
        overall_support_goal: overallGoal.trim(),
        start_date: startDate,
        plan_end_date: planEndDate,
        next_review_deadline: planEndDate,
        review_date: isReview ? today : undefined,
        review_reason: isReview ? reviewReason.trim() : undefined,
        long_term_goal_data: ltgDescription.trim() ? {
          description: ltgDescription.trim(),
          set_year_month: ltgSetYm || undefined,
          target_year_month: ltgTargetYm || undefined
        } : undefined,
        short_term_goal_data: stgDescription.trim() ? {
          description: stgDescription.trim(),
          set_year_month: stgSetYm || undefined,
          target_year_month: stgTargetYm || undefined
        } : undefined,
        items_data: validItems.length > 0 ? validItems : undefined,
        source_links_data: sourceLinks,
        detail_fields: {
          // 利用者基本情報確定スナップショット (要件1)
          user_name: snapshotUserName || undefined,
          user_name_kana: snapshotUserNameKana || undefined,
          gender: snapshotGender || undefined,
          birth_date: snapshotBirthDate || undefined,
          age_at_planning: snapshotAge !== null ? snapshotAge : undefined,
          support_level: snapshotSupportLevel || undefined,
          disability_handbook_type: snapshotHandbookType || undefined,

          // 雇用先確定スナップショット (要件1)
          employer_name: snapshotEmployerName || undefined,
          employer_industry: snapshotEmployerIndustry || undefined,
          employer_address: snapshotEmployerAddress || undefined,
          employer_tel: snapshotEmployerTel || undefined,
          employer_contact_person: snapshotEmployerContactPerson || undefined,
          job_start_date: snapshotJobStartDate || undefined,
          work_content: snapshotWorkContent || undefined,

          // 事業所確定スナップショット (要件1)
          office_name: snapshotOfficeName || undefined,
          office_number: snapshotOfficeNumber || undefined,
          office_address: snapshotOfficeAddress || undefined,
          office_tel: snapshotOfficeTel || undefined,
          office_fax: snapshotOfficeFax || undefined,

          // 労働条件・環境・引継情報
          employment_type: employmentType || undefined,
          wage_condition: wageCondition || undefined,
          holiday_condition: holidayCondition || undefined,
          working_hours_and_break: workingHoursAndBreak || undefined,
          pre_employment_handover: preEmploymentHandover || undefined,
          living_environment_support: livingEnvSupport || undefined,
          physical_work_environment: physicalEnv || undefined,
          human_work_environment: humanEnv || undefined,
          user_wishes: userWishes || undefined,
          health_condition: healthCond || undefined,
          related_support_organizations: relatedOrgs || undefined,
          explained_date: explainedDate || undefined,
          agreed_date: agreedDate || undefined,
          consent_confirmed: consentConfirmed,
          consent_notes: consentNotes || undefined,
          staff_explainer_name: staffExplainerName || undefined
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
                    利用者基本情報（一次モデル取得）
                  </div>
                  <div className="text-xs space-y-1.5 text-slate-600">
                    <p><span className="text-slate-400">氏名:</span> {snapshotUserName || userName}</p>
                    <p><span className="text-slate-400">ふりがな:</span> {snapshotUserNameKana || '未登録'}</p>
                    <p><span className="text-slate-400">性別 / 生年月日:</span> {snapshotGender || '未登録'} / {snapshotBirthDate || '未登録'} {snapshotAge !== null && snapshotAge !== undefined ? `(${snapshotAge}歳)` : ''}</p>
                    <p><span className="text-slate-400">障害支援区分:</span> {snapshotSupportLevel || '未登録'}</p>
                    <div className="pt-1">
                      <div className="flex items-center justify-between text-[11px] mb-1">
                        <span className="font-bold text-slate-700">障害者手帳種別（様式2公式項目・要確認）:</span>
                        {assistanceData?.candidates.handbook_level_candidate && (
                          <span className="text-amber-700 font-medium">登録等級（参考）: {assistanceData.candidates.handbook_level_candidate}</span>
                        )}
                      </div>
                      <select
                        value={snapshotHandbookType}
                        onChange={(e) => setSnapshotHandbookType(e.target.value)}
                        className="w-full px-2.5 py-1.5 border border-slate-200 rounded-lg text-xs bg-white text-slate-700 font-medium"
                      >
                        <option value="">未設定（手帳種別を支援員が確認・選択してください）</option>
                        <option value="身体障害者手帳">身体障害者手帳</option>
                        <option value="療育手帳">療育手帳（愛の手帳・みどりの手帳等）</option>
                        <option value="精神障害者保健福祉手帳">精神障害者保健福祉手帳</option>
                        <option value="手帳なし">手帳なし</option>
                      </select>
                    </div>
                  </div>
                </div>

                <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-3.5 space-y-2">
                  <div className="flex items-center gap-2 text-xs font-bold text-slate-700 border-b border-slate-200 pb-1.5">
                    <Building2 className="w-4 h-4 text-indigo-600" />
                    雇用先・就労事実（一次モデル取得）
                  </div>
                  <div className="text-xs space-y-1 text-slate-600">
                    <p><span className="text-slate-400">企業名:</span> {assistanceData?.employment_info_snapshot.employer_name || '未登録'}</p>
                    <p><span className="text-slate-400">職種・業務内容:</span> {assistanceData?.employment_info_snapshot.work_content || '未登録'}</p>
                    <p><span className="text-slate-400">雇用開始日:</span> {assistanceData?.employment_info_snapshot.job_start_date || '未登録'}</p>
                    <p><span className="text-slate-400">事業所名:</span> {assistanceData?.office_info_snapshot.office_name || '未登録'}</p>
                  </div>
                </div>
              </div>

              {/* 2. 一次情報候補カード */}
              <div className="space-y-3">
                <div className="text-xs font-bold text-slate-700 flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <Quote className="w-4 h-4 text-amber-500" />
                    一次情報ログ・参考記録（確認・引用用）
                  </span>
                  <span className="text-[11px] text-slate-400 font-normal">
                    支援員が確認のうえ様式2へ反映してください
                  </span>
                </div>

                {loadingAssistance ? (
                  <div className="text-xs text-slate-400 py-6 text-center">候補データを読み込み中...</div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {/* 就労条件の参考情報 */}
                    {assistanceData?.candidates.work_conditions_candidate && (
                      <div className="border border-slate-200 rounded-xl p-3 bg-white space-y-2 md:col-span-2">
                        <div className="text-xs font-bold text-slate-800 flex items-center justify-between text-teal-700">
                          <span>参考: 直近エピソードの労働条件記録（自由記述）</span>
                          <span className="text-[11px] text-slate-400 font-normal">※賃金等の公式項目への自動代入は禁止されています</span>
                        </div>
                        <div className="p-2 bg-teal-50/40 rounded-lg text-xs space-y-1.5 border border-teal-100">
                          <p className="text-slate-700 font-medium">{assistanceData.candidates.work_conditions_candidate}</p>
                          <div className="flex flex-wrap gap-2 pt-1 border-t border-teal-200/50">
                            <button
                              type="button"
                              onClick={() => handleAdoptWorkConditions('employmentType', assistanceData.candidates.work_conditions_candidate!)}
                              className="text-[11px] px-2 py-0.5 bg-teal-100 text-teal-800 rounded hover:bg-teal-200 font-medium transition"
                            >
                              雇用形態に反映
                            </button>
                            <button
                              type="button"
                              onClick={() => handleAdoptWorkConditions('wage', assistanceData.candidates.work_conditions_candidate!)}
                              className="text-[11px] px-2 py-0.5 bg-teal-100 text-teal-800 rounded hover:bg-teal-200 font-medium transition"
                            >
                              賃金に反映
                            </button>
                            <button
                              type="button"
                              onClick={() => handleAdoptWorkConditions('holiday', assistanceData.candidates.work_conditions_candidate!)}
                              className="text-[11px] px-2 py-0.5 bg-teal-100 text-teal-800 rounded hover:bg-teal-200 font-medium transition"
                            >
                              休日に反映
                            </button>
                            <button
                              type="button"
                              onClick={() => handleAdoptWorkConditions('hours', assistanceData.candidates.work_conditions_candidate!)}
                              className="text-[11px] px-2 py-0.5 bg-teal-100 text-teal-800 rounded hover:bg-teal-200 font-medium transition"
                            >
                              勤務時間・休憩に反映
                            </button>
                          </div>
                        </div>
                      </div>
                    )}

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
                  次へ: 様式2 公式項目の入力 →
                </button>
              </div>
            </div>
          )}

          {/* ============================================================
              TAB 2: 厚労省様式2 公式項目（目標・労働条件・支援内容）
             ============================================================ */}
          {activeTab === 'form2' && (
            <div className="space-y-6">
              {/* 1. 長期目標・短期目標 */}
              <div className="border border-slate-200 rounded-xl p-4 bg-slate-50/60 space-y-4">
                <h3 className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                  <Target className="w-4 h-4 text-indigo-600" />
                  長期目標・短期目標（厚労省様式2公式項目）
                </h3>

                {/* 長期目標 */}
                <div className="space-y-2 bg-white p-3 rounded-lg border border-slate-200">
                  <label className="block text-xs font-bold text-slate-700">長期目標</label>
                  <textarea
                    rows={2}
                    value={ltgDescription}
                    onChange={(e) => setLtgDescription(e.target.value)}
                    placeholder="例: 職場の人間関係を良好に保ち、1年以上の安定就労を継続する"
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                  />
                  <div className="grid grid-cols-2 gap-3 pt-1">
                    <div>
                      <label className="block text-[11px] text-slate-500 mb-1">設定年月 (YYYY-MM)</label>
                      <input
                        type="month"
                        value={ltgSetYm}
                        onChange={(e) => setLtgSetYm(e.target.value)}
                        className="w-full px-2.5 py-1.5 border border-slate-200 rounded-lg text-xs"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] text-slate-500 mb-1">達成予定年月 (YYYY-MM)</label>
                      <input
                        type="month"
                        value={ltgTargetYm}
                        onChange={(e) => setLtgTargetYm(e.target.value)}
                        className="w-full px-2.5 py-1.5 border border-slate-200 rounded-lg text-xs"
                      />
                    </div>
                  </div>
                </div>

                {/* 短期目標 */}
                <div className="space-y-2 bg-white p-3 rounded-lg border border-slate-200">
                  <label className="block text-xs font-bold text-slate-700">短期目標</label>
                  <textarea
                    rows={2}
                    value={stgDescription}
                    onChange={(e) => setStgDescription(e.target.value)}
                    placeholder="例: 体調に不安が生じた際に自ら上司や支援員へ相談できる"
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
                  />
                  <div className="grid grid-cols-2 gap-3 pt-1">
                    <div>
                      <label className="block text-[11px] text-slate-500 mb-1">設定年月 (YYYY-MM)</label>
                      <input
                        type="month"
                        value={stgSetYm}
                        onChange={(e) => setStgSetYm(e.target.value)}
                        className="w-full px-2.5 py-1.5 border border-slate-200 rounded-lg text-xs"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] text-slate-500 mb-1">達成予定年月 (YYYY-MM)</label>
                      <input
                        type="month"
                        value={stgTargetYm}
                        onChange={(e) => setStgTargetYm(e.target.value)}
                        className="w-full px-2.5 py-1.5 border border-slate-200 rounded-lg text-xs"
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* 2. 労働条件（雇用形態・賃金・休日・勤務時間） */}
              <div className="border border-slate-200 rounded-xl p-4 bg-slate-50/60 space-y-3">
                <h3 className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                  <Building2 className="w-4 h-4 text-indigo-600" />
                  労働条件（厚労省様式2公式項目・支援員確認）
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                  <div>
                    <label className="block text-slate-600 font-bold mb-1">雇用形態</label>
                    <input
                      type="text"
                      value={employmentType}
                      onChange={(e) => setEmploymentType(e.target.value)}
                      placeholder="例: パートタイム、契約社員、正社員"
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-white text-xs"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-600 font-bold mb-1">賃金</label>
                    <input
                      type="text"
                      value={wageCondition}
                      onChange={(e) => setWageCondition(e.target.value)}
                      placeholder="例: 時給1,100円、月給180,000円"
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-white text-xs"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-600 font-bold mb-1">休日</label>
                    <input
                      type="text"
                      value={holidayCondition}
                      onChange={(e) => setHolidayCondition(e.target.value)}
                      placeholder="例: 完全週休2日制（土日祝）、シフト制"
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-white text-xs"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-600 font-bold mb-1">勤務時間・休憩</label>
                    <input
                      type="text"
                      value={workingHoursAndBreak}
                      onChange={(e) => setWorkingHoursAndBreak(e.target.value)}
                      placeholder="例: 9:00〜16:00（休憩60分）"
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-white text-xs"
                    />
                  </div>
                </div>
              </div>

              {/* 3. 引継事項・生活環境・職場環境 */}
              <div className="border border-slate-200 rounded-xl p-4 bg-slate-50/60 space-y-3">
                <h3 className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                  <FileText className="w-4 h-4 text-indigo-600" />
                  本人の状況・引継・環境サポート体制
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                  <div>
                    <label className="block text-slate-600 font-bold mb-1">就職前事業所からの引継事項</label>
                    <textarea
                      rows={2}
                      value={preEmploymentHandover}
                      onChange={(e) => setPreEmploymentHandover(e.target.value)}
                      placeholder="例: 集中力持続傾向、疲労時のサイン、移行事業所での訓練実績"
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-white text-xs"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-600 font-bold mb-1">生活環境・生活面サポート体制</label>
                    <textarea
                      rows={2}
                      value={livingEnvSupport}
                      onChange={(e) => setLivingEnvSupport(e.target.value)}
                      placeholder="例: 家族同居、通院同行体制、相談支援専門員との月1回連絡"
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-white text-xs"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-600 font-bold mb-1">職場環境（物理的環境）</label>
                    <input
                      type="text"
                      value={physicalEnv}
                      onChange={(e) => setPhysicalEnv(e.target.value)}
                      placeholder="例: 空調完備の執務スペース、休憩室近接"
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-white text-xs"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-600 font-bold mb-1">職場環境（人的環境）</label>
                    <input
                      type="text"
                      value={humanEnv}
                      onChange={(e) => setHumanEnv(e.target.value)}
                      placeholder="例: 指導担当者隣席配置、復唱確認ルール"
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-white text-xs"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-600 font-bold mb-1">本人の希望・意向</label>
                    <input
                      type="text"
                      value={userWishes}
                      onChange={(e) => setUserWishes(e.target.value)}
                      placeholder="例: 長く安定して勤務を継続したい"
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-white text-xs"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-600 font-bold mb-1">健康状態・体調面</label>
                    <input
                      type="text"
                      value={healthCond}
                      onChange={(e) => setHealthCond(e.target.value)}
                      placeholder="例: 服薬管理良好、睡眠時間7時間確保"
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-white text-xs"
                    />
                  </div>
                  <div className="md:col-span-2">
                    <label className="block text-slate-600 font-bold mb-1">関係支援機関</label>
                    <input
                      type="text"
                      value={relatedOrgs}
                      onChange={(e) => setRelatedOrgs(e.target.value)}
                      placeholder="例: ハローワーク、地域障害者職業センター、かかりつけ医"
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-white text-xs"
                    />
                  </div>
                </div>
              </div>

              {/* 4. 支援内容・評価テーブル (①〜③) */}
              <div className="space-y-4 pt-1">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                    <Layers className="w-4 h-4 text-indigo-600" />
                    支援内容・計画項目（①〜③・未入力項目は空のまま保持）
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
                          placeholder="例: 月1回面談、随時連絡"
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
                      <div className="md:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-3 p-2.5 bg-white rounded-lg border border-slate-200">
                        <div>
                          <div className="flex items-center justify-between mb-1">
                            <label className="block text-slate-600 font-medium text-[11px]">支援期間 開始日（未入力可）</label>
                            <button
                              type="button"
                              onClick={() => handleItemChange(idx, 'support_period_start', startDate)}
                              className="text-[10px] text-indigo-600 hover:text-indigo-800 font-medium underline"
                            >
                              計画開始日（{startDate}）を反映
                            </button>
                          </div>
                          <input
                            type="date"
                            value={it.support_period_start || ''}
                            onChange={(e) => handleItemChange(idx, 'support_period_start', e.target.value)}
                            className="w-full px-2.5 py-1.5 border border-slate-200 rounded-lg text-xs"
                          />
                        </div>
                        <div>
                          <div className="flex items-center justify-between mb-1">
                            <label className="block text-slate-600 font-medium text-[11px]">支援期間 終了日（未入力可）</label>
                            <button
                              type="button"
                              onClick={() => handleItemChange(idx, 'support_period_end', planEndDate)}
                              className="text-[10px] text-indigo-600 hover:text-indigo-800 font-medium underline"
                            >
                              計画終了日（{planEndDate}）を反映
                            </button>
                          </div>
                          <input
                            type="date"
                            value={it.support_period_end || ''}
                            onChange={(e) => handleItemChange(idx, 'support_period_end', e.target.value)}
                            className="w-full px-2.5 py-1.5 border border-slate-200 rounded-lg text-xs"
                          />
                        </div>
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
                    if (!overallGoal && ltgDescription) {
                      setOverallGoal(ltgDescription);
                    }
                    setActiveTab('summary');
                  }}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-xl text-xs font-bold hover:bg-indigo-700 transition"
                >
                  次へ: 説明同意・期間サマリー →
                </button>
              </div>
            </div>
          )}

          {/* ============================================================
              TAB 3: 説明・同意、期間、日常支援サマリー
             ============================================================ */}
          {activeTab === 'summary' && (
            <div className="space-y-5">
              {/* 1. 本人への説明・同意に必要な項目 */}
              <div className="border border-slate-200 rounded-xl p-4 bg-slate-50/60 space-y-3">
                <h3 className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                  <UserCheck className="w-4 h-4 text-emerald-600" />
                  本人への説明・同意情報（厚労省様式2公式項目）
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                  <div>
                    <label className="block text-slate-600 font-bold mb-1">本人説明日</label>
                    <input
                      type="date"
                      value={explainedDate}
                      onChange={(e) => setExplainedDate(e.target.value)}
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-white text-xs"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-600 font-bold mb-1">同意受領日</label>
                    <input
                      type="date"
                      value={agreedDate}
                      onChange={(e) => setAgreedDate(e.target.value)}
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-white text-xs"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-600 font-bold mb-1">説明実施者（職員氏名）</label>
                    <input
                      type="text"
                      value={staffExplainerName}
                      onChange={(e) => setStaffExplainerName(e.target.value)}
                      placeholder="例: 定着支援員 山田太郎"
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-white text-xs"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-600 font-bold mb-1">説明・同意特記事項</label>
                    <input
                      type="text"
                      value={consentNotes}
                      onChange={(e) => setConsentNotes(e.target.value)}
                      placeholder="例: 本人署名確認済み、書面交付済み"
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-white text-xs"
                    />
                  </div>
                  <div className="md:col-span-2 pt-1">
                    <label className="flex items-center gap-2 text-xs font-bold text-slate-700 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={consentConfirmed}
                        onChange={(e) => setConsentConfirmed(e.target.checked)}
                        className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 w-4 h-4"
                      />
                      本人への説明を実施し、計画内容についての同意を確認した
                    </label>
                  </div>
                </div>
              </div>

              {/* 2. 期間設定 */}
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

              {/* 3. 随時見直し理由（見直し時のみ表示。初回は非表示：要件6） */}
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

              {/* 4. 日常支援用サマリー（大まかな支援目標） */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-bold text-slate-700">
                    日常支援用サマリー（大まかな支援目標） <span className="text-rose-500">*</span>
                  </label>
                  {ltgDescription && (
                    <button
                      type="button"
                      onClick={() => setOverallGoal(ltgDescription)}
                      className="text-[11px] text-indigo-600 hover:text-indigo-800 font-medium"
                    >
                      長期目標からコピー
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
                  スタッフ画面やダッシュボードで常時確認される総合サマリーです。
                </p>
              </div>

              {/* ナビゲーションボタン */}
              <div className="pt-2 flex justify-between">
                <button
                  type="button"
                  onClick={() => setActiveTab('form2')}
                  className="px-4 py-2 border border-slate-200 text-slate-600 rounded-xl text-xs font-bold hover:bg-slate-100 transition"
                >
                  ← 様式2 公式項目に戻る
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
