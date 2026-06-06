import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { 
  FileText, Target, CheckCircle, Plus, 
  AlertCircle, MessageSquare, Clock, Compass, HelpCircle, 
  ArrowRight, AlertTriangle, Copy, Trash2
} from 'lucide-react';
import {
  fetchUserSupportPlans,
  fetchUserMonitoringReports,
  fetchUserCaseConferences,
  recordUserConsent,
  activateSupportPlan,
  createSupportPlanDraft,
  createNextSupportPlanDraft,
  saveSupportPlanGoals,
  getSupportPlanDetails,
  updateSupportPlanDraft,
  type UserSupportPlansResponse,
  type UserMonitoringResponse,
  type CaseConferenceItem,
} from '../../services/userService';
import { X } from 'lucide-react';

const statusLabel: Record<string, { label: string; color: string }> = {
  ACTIVE: { label: '有効 (ACTIVE)', color: 'bg-emerald-100 text-emerald-700' },
  DRAFT: { label: '下書き (DRAFT)', color: 'bg-slate-100 text-slate-600' },
  PENDING_CONSENT: { label: '同意待ち', color: 'bg-amber-100 text-amber-700' },
  PENDING_CONFERENCE: { label: '会議待ち', color: 'bg-indigo-100 text-indigo-700' },
  ARCHIVED: { label: '過去 (ARCHIVED)', color: 'bg-slate-100 text-slate-500' },
};

const getDaysUntil = (dateStr: string | null): number | null => {
  if (!dateStr) return null;
  const diff = new Date(dateStr).getTime() - new Date().setHours(0,0,0,0);
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
};

const conferenceTypeLabel: Record<string, string> = {
  AD_HOC: '随時',
  REGULAR: '定例',
  EMERGENCY: '緊急',
};

export const UserSupportPlanTab: React.FC<{ userId: number }> = ({ userId }) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const sectionParam = searchParams.get('section');

  // データ状態
  const [plansData, setPlansData] = useState<UserSupportPlansResponse | null>(null);
  const [monitoringData, setMonitoringData] = useState<UserMonitoringResponse | null>(null);
  const [conferences, setConferences] = useState<CaseConferenceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 同意ダイアログ用
  const [showConsentModal, setShowConsentModal] = useState(false);
  const [consentProofType, setConsentProofType] = useState<'DIGITAL_SIGNATURE' | 'IN_PERSON_HANDOVER'>('DIGITAL_SIGNATURE');
  const [signerName, setSignerName] = useState('');
  const [consentSubmitting, setConsentSubmitting] = useState(false);
  const [consentError, setConsentError] = useState<string | null>(null);

  // データ一括ロード
  const loadAllData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [plansRes, monitoringRes, confRes] = await Promise.all([
        fetchUserSupportPlans(userId),
        fetchUserMonitoringReports(userId),
        fetchUserCaseConferences(userId)
      ]);

      setPlansData(plansRes);
      setMonitoringData(monitoringRes);
      setConferences(confRes.items);
    } catch (err) {
      console.error(err);
      setError('計画サイクルデータの取得に失敗しました。');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAllData();
  }, [userId]);

  const handleConsentSubmit = async () => {
    const pendingPlan = plansData?.plan_history.find(p => p.plan_status === 'PENDING_CONSENT');
    if (!pendingPlan) {
      setConsentError('同意待ちの計画が見つかりません。');
      return;
    }

    if (!signerName.trim()) {
      setConsentError('署名者・受領者名を入力してください。');
      return;
    }

    try {
      setConsentSubmitting(true);
      setConsentError(null);

      // 1. 同意証跡の登録
      const proofStr = consentProofType === 'DIGITAL_SIGNATURE'
        ? `DIGITAL_SIGNATURE_BY_${signerName}`
        : `IN_PERSON_HANDOVER_TO_${signerName}`;
      
      const consentRes = await recordUserConsent(pendingPlan.id, userId, proofStr);
      
      // 2. 計画の有効化 (ACTIVE化)
      await activateSupportPlan(pendingPlan.id, consentRes.consent_log_id);

      setShowConsentModal(false);
      setSignerName('');
      await loadAllData();
    } catch (err: any) {
      console.error(err);
      const errMsg = err.response?.data?.msg || '同意手続きまたは計画の有効化に失敗しました。';
      setConsentError(errMsg);
    } finally {
      setConsentSubmitting(false);
    }
  };

  // 新規計画作成・クローン用
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createSubmitting, setCreateSubmitting] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [editingPlanId, setEditingPlanId] = useState<number | null>(null);
  
  const [formPlanStartDate, setFormPlanStartDate] = useState('');
  const [formPlanEndDate, setFormPlanEndDate] = useState('');
  const [formUserIntentionContent, setFormUserIntentionContent] = useState('');
  const [formSupportPolicyContent, setFormSupportPolicyContent] = useState('');

  const [showCloneConfirmModal, setShowCloneConfirmModal] = useState(false);
  const [cloningSubmitting, setCloningSubmitting] = useState(false);

  // 定期的な日付の自動入力用（本日＋3ヶ月後など）
  const initDefaultDates = () => {
    const today = new Date();
    const formattedToday = today.toISOString().split('T')[0];
    const threeMonthsLater = new Date(today.getFullYear(), today.getMonth() + 3, today.getDate());
    const formattedEndDate = threeMonthsLater.toISOString().split('T')[0];
    
    setFormPlanStartDate(formattedToday);
    setFormPlanEndDate(formattedEndDate);
  };

  // 動的目標フォームの初期値定義
  const DEFAULT_INDIVIDUAL_GOAL = () => ({
    concrete_goal: '',
    user_commitment: '',
    support_actions: '',
    service_type: 'TRAINING',
    is_facility_in_deemed: false,
    is_work_preparation_positioning: false
  });

  const DEFAULT_SHORT_TERM_GOAL = () => ({
    description: '',
    individual_goals: [DEFAULT_INDIVIDUAL_GOAL()]
  });

  const DEFAULT_LONG_TERM_GOAL = () => ({
    description: '',
    short_term_goals: [DEFAULT_SHORT_TERM_GOAL()]
  });

  const [formLongTermGoals, setFormLongTermGoals] = useState<any[]>([DEFAULT_LONG_TERM_GOAL()]);

  // 新規計画作成＆編集ハンドラー
  const handleCreatePlanSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setCreateSubmitting(true);
      setCreateError(null);

      let planId = editingPlanId;

      if (planId) {
        // 編集モード: 計画本体（日付・方針）の更新
        await updateSupportPlanDraft(planId, {
          planStartDate: formPlanStartDate || undefined,
          planEndDate: formPlanEndDate || undefined,
          userIntentionContent: formUserIntentionContent || undefined,
          supportPolicyContent: formSupportPolicyContent || undefined
        });
      } else {
        // 新規作成モード
        const newPlanRes = await createSupportPlanDraft({
          userId,
          planStartDate: formPlanStartDate || undefined,
          planEndDate: formPlanEndDate || undefined,
          userIntentionContent: formUserIntentionContent || undefined,
          supportPolicyContent: formSupportPolicyContent || undefined
        });
        planId = newPlanRes.plan_id;
      }

      // 目標ツリーの一括保存（新規作成・編集共通）
      await saveSupportPlanGoals(planId!, {
        long_term_goals: formLongTermGoals
      });

      setShowCreateModal(false);
      setEditingPlanId(null);
      setFormLongTermGoals([DEFAULT_LONG_TERM_GOAL()]);
      setFormPlanStartDate('');
      setFormPlanEndDate('');
      setFormUserIntentionContent('');
      setFormSupportPolicyContent('');
      await loadAllData();
    } catch (err: any) {
      console.error(err);
      setCreateError(err.response?.data?.msg || '計画の保存または目標の登録に失敗しました。');
    } finally {
      setCreateSubmitting(false);
    }
  };

  // 原案の編集開始ハンドラー
  const handleEditPlanClick = async (planId: number) => {
    try {
      setCreateError(null);
      const details = await getSupportPlanDetails(planId);
      
      setFormPlanStartDate(details.start_date ?? '');
      setFormPlanEndDate(details.end_date ?? '');
      setFormUserIntentionContent(details.holistic_policy?.user_intention_content ?? '');
      setFormSupportPolicyContent(details.holistic_policy?.support_policy_content ?? '');
      
      // 目標ツリーの流し込み
      if (details.long_term_goals && details.long_term_goals.length > 0) {
        setFormLongTermGoals(details.long_term_goals.map(ltg => ({
          description: ltg.description,
          short_term_goals: ltg.short_term_goals.map(stg => ({
            description: stg.description,
            individual_goals: stg.individual_goals.map(ig => ({
              concrete_goal: ig.concrete_goal,
              user_commitment: ig.user_commitment,
              support_actions: ig.support_actions,
              service_type: ig.service_type,
              is_facility_in_deemed: !!ig.is_facility_in_deemed,
              is_work_preparation_positioning: !!ig.is_work_preparation_positioning
            }))
          }))
        })));
      } else {
        setFormLongTermGoals([DEFAULT_LONG_TERM_GOAL()]);
      }
      
      setEditingPlanId(planId);
      setShowCreateModal(true);
    } catch (err: any) {
      console.error(err);
      alert('計画詳細の取得に失敗しました。');
    }
  };

  // 次期計画クローンハンドラー
  const handleCreateNextPlan = async () => {
    if (!activePlan) return;
    try {
      setCloningSubmitting(true);
      await createNextSupportPlanDraft(activePlan.id);
      setShowCloneConfirmModal(false);
      await loadAllData();
    } catch (err: any) {
      console.error(err);
      alert(err.response?.data?.msg || '次期原案の作成に失敗しました。');
    } finally {
      setCloningSubmitting(false);
    }
  };

  // 目標ツリー操作用ヘルパー
  const addLongTermGoal = () => {
    setFormLongTermGoals([...formLongTermGoals, DEFAULT_LONG_TERM_GOAL()]);
  };

  const removeLongTermGoal = (ltgIndex: number) => {
    const next = [...formLongTermGoals];
    next.splice(ltgIndex, 1);
    setFormLongTermGoals(next);
  };

  const addShortTermGoal = (ltgIndex: number) => {
    const next = [...formLongTermGoals];
    next[ltgIndex].short_term_goals.push(DEFAULT_SHORT_TERM_GOAL());
    setFormLongTermGoals(next);
  };

  const removeShortTermGoal = (ltgIndex: number, stgIndex: number) => {
    const next = [...formLongTermGoals];
    next[ltgIndex].short_term_goals.splice(stgIndex, 1);
    setFormLongTermGoals(next);
  };

  const addIndividualGoal = (ltgIndex: number, stgIndex: number) => {
    const next = [...formLongTermGoals];
    next[ltgIndex].short_term_goals[stgIndex].individual_goals.push(DEFAULT_INDIVIDUAL_GOAL());
    setFormLongTermGoals(next);
  };

  const removeIndividualGoal = (ltgIndex: number, stgIndex: number, igIndex: number) => {
    const next = [...formLongTermGoals];
    next[ltgIndex].short_term_goals[stgIndex].individual_goals.splice(igIndex, 1);
    setFormLongTermGoals(next);
  };

  // section クエリパラメータに応じたスクロール＆ハイライト処理
  useEffect(() => {
    if (!loading && sectionParam) {
      setTimeout(() => {
        const targetId = `section-${sectionParam}`;
        const element = document.getElementById(targetId);
        if (element) {
          element.scrollIntoView({ behavior: 'smooth', block: 'center' });
          element.classList.add('ring-4', 'ring-indigo-500/30', 'border-indigo-500');
          setTimeout(() => {
            element.classList.remove('ring-4', 'ring-indigo-500/30', 'border-indigo-500');
          }, 3000);
        }
      }, 300);

      // パラメータをクリアしてURLをクリーンにする
      const newParams = new URLSearchParams(searchParams);
      newParams.delete('section');
      setSearchParams(newParams, { replace: true });
    }
  }, [loading, sectionParam, searchParams, setSearchParams]);

  if (loading) {
    return <div className="flex justify-center p-12"><div className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" /></div>;
  }
  if (error) {
    return <div className="bg-rose-50 text-rose-600 p-4 rounded-xl font-bold flex items-center gap-2"><AlertCircle className="w-5 h-5" />{error}</div>;
  }

  // モニタリングの期日計算
  const daysUntil = getDaysUntil(monitoringData?.next_monitoring_due ?? null);
  const isOverdue = daysUntil !== null && daysUntil < 0;
  const isUrgent = daysUntil !== null && daysUntil <= 30 && daysUntil >= 0;

  // 現在のステータス算出
  const activePlan = plansData?.active_plan;
  const latestPlanStatus = plansData?.plan_history && plansData.plan_history.length > 0 
    ? plansData.plan_history[0].plan_status 
    : 'NONE';

  // 1: アセスメント ➔ 2: 計画原案 ➔ 3: ケース会議 ➔ 4: 計画成案 ➔ 5: 説明・同意 (ACTIVE化) ➔ 6: モニタリング
  let currentStepIndex = 1;
  if (latestPlanStatus === 'DRAFT') currentStepIndex = 2;
  else if (latestPlanStatus === 'PENDING_CONFERENCE') currentStepIndex = 3;
  else if (latestPlanStatus === 'PENDING_CONSENT') {
    currentStepIndex = 5; // 同意待ち状態
  } else if (activePlan) {
    currentStepIndex = 6; // 有効期間＆モニタリング中
  }

  return (
    <div className="space-y-10 animate-in fade-in duration-500 max-w-4xl mx-auto pb-12">
      
      {/* 1. 現在の計画ステータス */}
      <div className="bg-white border border-slate-200 p-6 rounded-3xl shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">Current Status</span>
          <h2 className="text-2xl font-black text-slate-800 flex items-center gap-2.5 mt-1">
            <Compass className="w-6 h-6 text-indigo-600" />
            個別支援計画ステータス
          </h2>
          <p className="text-slate-500 text-sm font-medium mt-1">
            {activePlan 
              ? `現在、第 ${activePlan.id} 期個別支援計画がアクティブです。` 
              : '現在、有効な成案計画はありません。新規作成・会議・同意を進めてください。'}
          </p>
        </div>
        <div className="shrink-0 flex items-center gap-3">
          <span className={`px-4 py-2 rounded-2xl text-sm font-black shadow-sm ${
            activePlan 
              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' 
              : 'bg-rose-50 text-rose-700 border border-rose-200'
          }`}>
            {activePlan ? '計画 ACTIVE' : '計画 未作成'}
          </span>
          {activePlan && (
            <button 
              onClick={() => setShowCloneConfirmModal(true)}
              className="flex items-center gap-1.5 bg-indigo-600 text-white px-4 py-2.5 rounded-xl font-bold text-xs hover:bg-indigo-700 transition-colors shadow-sm"
            >
              <Copy className="w-4 h-4" /> 次期原案を作成
            </button>
          )}
          <button 
            onClick={() => {
              setEditingPlanId(null);
              setFormLongTermGoals([DEFAULT_LONG_TERM_GOAL()]);
              initDefaultDates();
              setFormUserIntentionContent('');
              setFormSupportPolicyContent('');
              setCreateError(null);
              setShowCreateModal(true);
            }}
            className={`flex items-center gap-1.5 px-4 py-2.5 rounded-xl font-bold text-xs transition-colors shadow-sm ${
              activePlan
                ? 'bg-slate-100 text-slate-700 hover:bg-slate-250 border border-slate-200'
                : 'bg-indigo-600 text-white hover:bg-indigo-700'
            }`}
          >
            <Plus className="w-4 h-4" /> 新規計画作成
          </button>
        </div>
      </div>

      {activePlan?.holistic_policy?.support_policy_content?.includes('【暫定支援方針】') && (
        <div className="bg-amber-50 border border-amber-200 p-4 rounded-3xl flex items-start gap-3 text-amber-800 animate-in fade-in duration-300">
          <AlertTriangle className="w-5 h-5 shrink-0 text-amber-600 mt-0.5" />
          <div>
            <p className="text-xs font-black">この計画は暫定支援方針に基づいて作成されています</p>
            <p className="text-[10px] text-amber-700 mt-0.5">アセスメント未実施のため、初期原案作成用の暫定方針が適用されています。後でアセスメント情報を登録してください。</p>
          </div>
        </div>
      )}

      {/* 2. 業務サイクルロードマップ */}
      <div className="bg-white border border-slate-200 p-6 rounded-3xl shadow-sm">
        <h3 className="text-sm font-black text-slate-400 mb-4 uppercase tracking-widest">Support Cycle Roadmap</h3>
        <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
          {[
            { index: 1, name: '1. アセスメント', color: 'indigo' },
            { index: 2, name: '2. 計画原案', color: 'indigo' },
            { index: 3, name: '3. ケース会議', color: 'indigo' },
            { index: 4, name: '4. 計画成案', color: 'indigo' },
            { index: 5, name: '5. 説明・同意', color: 'indigo' },
            { index: 6, name: '6. モニタリング', color: 'indigo' },
          ].map(step => {
            const isActive = step.index === currentStepIndex;
            const isCompleted = step.index < currentStepIndex;
            return (
              <div 
                key={step.index} 
                className={`p-3 rounded-2xl border text-center transition-all flex flex-col justify-between items-center h-24 ${
                  isActive 
                    ? 'bg-indigo-600 text-white border-indigo-600 shadow-md shadow-indigo-100 scale-105 font-black' 
                    : isCompleted 
                    ? 'bg-emerald-50 text-emerald-700 border-emerald-200 font-bold' 
                    : 'bg-slate-50 text-slate-400 border-slate-200/80 font-medium'
                }`}
              >
                <div className="text-[10px] uppercase font-black tracking-wider opacity-85">
                  {isCompleted ? '✓ 完了' : isActive ? '● 進行中' : '未着手'}
                </div>
                <div className="text-xs mt-1 leading-snug">{step.name.split('. ')[1]}</div>
                <div className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold bg-white/20 mt-1">
                  {step.index}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 支援サイクル 各ステップセクション一覧 */}
      <div className="space-y-6">

        {/* 3. アセスメント */}
        <div id="section-assessment" className="bg-white border border-slate-200 p-6 rounded-3xl shadow-sm transition-all duration-300">
          <div className="flex items-start justify-between mb-4">
            <h3 className="text-lg font-black text-slate-800 flex items-center gap-2">
              <span className="w-7 h-7 rounded-xl bg-slate-100 flex items-center justify-center text-slate-500 font-bold text-sm">1</span>
              アセスメント
            </h3>
            <span className="text-xs font-bold text-slate-400 bg-slate-50 px-2.5 py-1 rounded-lg">工程 1/7</span>
          </div>
          <div className="border border-dashed border-slate-200 p-6 rounded-2xl text-center">
            <HelpCircle className="w-8 h-8 text-slate-300 mx-auto mb-2" />
            <p className="text-sm font-bold text-slate-500">直近のアセスメント・面談記録</p>
            <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">アセスメント機能は次期フェーズで提供予定です。現在は紙媒体や外部ツールで実施したアセスメントをもとに個別支援計画を作成してください。</p>
          </div>
        </div>

        {/* 4. 計画原案 */}
        <div id="section-draft" className="bg-white border border-slate-200 p-6 rounded-3xl shadow-sm transition-all duration-300">
          <div className="flex items-start justify-between mb-4">
            <h3 className="text-lg font-black text-slate-800 flex items-center gap-2">
              <span className="w-7 h-7 rounded-xl bg-slate-100 flex items-center justify-center text-slate-500 font-bold text-sm">2</span>
              計画原案
            </h3>
            <span className="text-xs font-bold text-slate-400 bg-slate-50 px-2.5 py-1 rounded-lg">工程 2/7</span>
          </div>
          {latestPlanStatus === 'DRAFT' ? (
            <div className="space-y-3">
              <div className="bg-indigo-50/50 border border-indigo-100 p-5 rounded-2xl flex items-center justify-between">
                <div>
                  <p className="text-sm font-black text-indigo-900">作成中の計画原案があります</p>
                  <p className="text-xs text-indigo-700 mt-0.5">原案を作成後、関係者でケース会議を行い、内容をブラッシュアップします。</p>
                </div>
                <button 
                  onClick={() => {
                    const draftPlanId = plansData?.plan_history.find(p => p.plan_status === 'DRAFT')?.id;
                    if (draftPlanId) {
                      handleEditPlanClick(draftPlanId);
                    }
                  }}
                  className="flex items-center gap-1 bg-indigo-600 text-white px-3.5 py-2 rounded-xl font-bold text-xs hover:bg-indigo-700 transition-colors shadow-sm"
                >
                  原案を編集 <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>

              {plansData?.plan_history.find(p => p.plan_status === 'DRAFT')?.based_on_plan_id && (
                <div className="bg-blue-50 border border-blue-200 p-4 rounded-2xl flex items-start gap-3 text-blue-800 animate-in fade-in duration-300">
                  <AlertCircle className="w-5 h-5 shrink-0 text-blue-600 mt-0.5" />
                  <div>
                    <p className="text-xs font-black">現行計画をもとに作成された原案です</p>
                    <p className="text-[10px] text-blue-700 mt-0.5">モニタリング結果を反映して編集してください。</p>
                  </div>
                </div>
              )}

              {plansData?.plan_history.find(p => p.plan_status === 'DRAFT')?.holistic_policy?.support_policy_content?.includes('【暫定支援方針】') && (
                <div className="bg-amber-50 border border-amber-200 p-4 rounded-2xl flex items-start gap-3 text-amber-800 animate-in fade-in duration-300">
                  <AlertTriangle className="w-5 h-5 shrink-0 text-amber-600 mt-0.5" />
                  <div>
                    <p className="text-xs font-black">この計画は暫定支援方針に基づいて作成されています</p>
                    <p className="text-[10px] text-amber-700 mt-0.5">アセスメント未実施のため、初期原案作成用の暫定方針が適用されています。後でアセスメント情報を登録してください。</p>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="border border-dashed border-slate-200 p-6 rounded-2xl text-center">
              <FileText className="w-8 h-8 text-slate-300 mx-auto mb-2" />
              <p className="text-sm font-bold text-slate-500">計画原案データはありません</p>
              <p className="text-xs text-slate-400 mt-1">「新規計画作成」を行うと、下書きの原案がここに表示されます。</p>
            </div>
          )}
        </div>

        {/* 5. ケース会議 (マージされた履歴) */}
        <div id="section-case_conference" className="bg-white border border-slate-200 p-6 rounded-3xl shadow-sm transition-all duration-300">
          <div className="flex items-start justify-between mb-4">
            <h3 className="text-lg font-black text-slate-800 flex items-center gap-2">
              <span className="w-7 h-7 rounded-xl bg-indigo-50 flex items-center justify-center text-indigo-600 font-bold text-sm">3</span>
              ケース会議
            </h3>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-slate-400 bg-slate-50 px-2.5 py-1 rounded-lg">工程 3/7</span>
              <button className="flex items-center gap-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-600 px-2.5 py-1 rounded-lg font-bold text-xs transition-colors">
                <Plus className="w-3 h-3" /> 新規記録
              </button>
            </div>
          </div>

          {conferences.length === 0 ? (
            <div className="border border-dashed border-slate-200 p-6 rounded-2xl text-center">
              <MessageSquare className="w-8 h-8 text-slate-300 mx-auto mb-2" />
              <p className="text-sm font-bold text-slate-500">ケース会議の記録がありません</p>
              <p className="text-xs text-slate-400 mt-1">計画の作成・変更時や、利用者の状況に重大な変化があった場合に行う会議の記録です。</p>
            </div>
          ) : (
            <div className="space-y-3">
              {conferences.map(conf => (
                <div key={conf.id} className="bg-slate-50/70 border border-slate-200/60 p-4 rounded-2xl">
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <span className="text-[10px] font-black text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-100 mr-2">
                        {conferenceTypeLabel[conf.conference_type] ?? conf.conference_type}
                      </span>
                      <span className="text-xs font-bold text-slate-400">
                        {conf.conference_datetime ? new Date(conf.conference_datetime).toLocaleDateString() : '—'}
                      </span>
                    </div>
                    <span className="text-[10px] font-bold text-slate-500">記録: {conf.initiator_name}</span>
                  </div>
                  <h4 className="text-sm font-black text-slate-800">{conf.concern_summary}</h4>
                  <div className="mt-2 text-xs font-medium text-slate-600">
                    <span className="font-bold text-slate-500">決定事項: </span>
                    {conf.agreed_action}
                  </div>
                  {conf.plan_direction_update && (
                    <div className="mt-1.5 text-xs font-medium text-indigo-700 bg-indigo-50/50 p-2 rounded-lg">
                      <span className="font-bold text-indigo-800">計画への反映: </span>
                      {conf.plan_direction_update}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 6. 計画成案 (承認・合意後の確定原案) */}
        <div id="section-finalized_plan" className="bg-white border border-slate-200 p-6 rounded-3xl shadow-sm transition-all duration-300">
          <div className="flex items-start justify-between mb-4">
            <h3 className="text-lg font-black text-slate-800 flex items-center gap-2">
              <span className="w-7 h-7 rounded-xl bg-slate-100 flex items-center justify-center text-slate-500 font-bold text-sm">4</span>
              計画成案
            </h3>
            <span className="text-xs font-bold text-slate-400 bg-slate-50 px-2.5 py-1 rounded-lg">工程 4/7</span>
          </div>
          {plansData?.plan_history.find(p => p.plan_status === 'PENDING_CONSENT') ? (
            <div className="bg-slate-50 border border-slate-200 p-5 rounded-2xl">
              <div className="flex justify-between items-start">
                <div>
                  <span className="bg-amber-100 text-amber-800 border border-amber-200 px-2.5 py-0.5 rounded-full text-[10px] font-black inline-block mb-1.5">
                    説明・同意待ち
                  </span>
                  <h4 className="text-md font-black text-slate-800">
                    第 {plansData.plan_history.find(p => p.plan_status === 'PENDING_CONSENT')?.plan_version} 期 個別支援計画（成案）
                  </h4>
                </div>
                <div className="text-right shrink-0 ml-4">
                  <div className="text-[10px] font-bold text-slate-400">予定期間</div>
                  <div className="text-xs font-black text-slate-600 mt-0.5">
                    {plansData.plan_history.find(p => p.plan_status === 'PENDING_CONSENT')?.start_date ?? '—'} 〜 {plansData.plan_history.find(p => p.plan_status === 'PENDING_CONSENT')?.end_date ?? '—'}
                  </div>
                </div>
              </div>
              <p className="text-xs text-slate-500 mt-3 font-medium">
                関係者会議（ケース会議）を経て作成された成案です。この計画を有効（ACTIVE）にするには、利用者または家族からの説明と同意の登録が必要です。
              </p>
            </div>
          ) : (
            <div className="border border-dashed border-slate-200 p-6 rounded-2xl text-center">
              <p className="text-sm font-bold text-slate-500">説明・同意待ちの計画成案はありません</p>
              <p className="text-xs text-slate-400 mt-1">ケース会議で合意し、計画が承認されるとここに表示されます。</p>
            </div>
          )}
        </div>

        {/* 7. 説明・同意 */}
        <div id="section-consent" className="bg-white border border-slate-200 p-6 rounded-3xl shadow-sm transition-all duration-300">
          <div className="flex items-start justify-between mb-4">
            <h3 className="text-lg font-black text-slate-800 flex items-center gap-2">
              <span className="w-7 h-7 rounded-xl bg-amber-50 flex items-center justify-center text-amber-600 font-bold text-sm">5</span>
              説明・同意
            </h3>
            <span className="text-xs font-bold text-slate-400 bg-slate-50 px-2.5 py-1 rounded-lg">工程 5/7</span>
          </div>
          {latestPlanStatus === 'PENDING_CONSENT' ? (
            <div className="bg-amber-50/60 border border-amber-200 p-5 rounded-2xl flex items-center justify-between">
              <div>
                <p className="text-sm font-black text-amber-900">利用者同意待ちの計画があります</p>
                <p className="text-xs text-amber-700 mt-0.5">計画案の説明を行い、同意（デジタル署名または受領済登録）を完了させてください。</p>
              </div>
              <button 
                onClick={() => {
                  setConsentError(null);
                  setSignerName('');
                  setShowConsentModal(true);
                }}
                className="flex items-center gap-1 bg-amber-600 text-white px-3.5 py-2 rounded-xl font-bold text-xs hover:bg-amber-700 transition-colors shadow-sm"
              >
                同意手続きに進む <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <div className="border border-dashed border-slate-200 p-6 rounded-2xl text-center">
              <CheckCircle className="w-8 h-8 text-slate-300 mx-auto mb-2" />
              <p className="text-sm font-bold text-slate-500">同意手続き待ちの計画はありません</p>
              <p className="text-xs text-slate-400 mt-1">計画原案が確定し承認されると、同意手続きに進むことができます。</p>
            </div>
          )}
        </div>

        {/* 8. 有効な計画 / ACTIVE計画 */}
        <div id="section-active_plan" className="bg-white border border-slate-200 p-6 rounded-3xl shadow-sm transition-all duration-300">
          <div className="flex items-start justify-between mb-4">
            <h3 className="text-lg font-black text-slate-800 flex items-center gap-2">
              <span className="w-7 h-7 rounded-xl bg-emerald-50 flex items-center justify-center text-emerald-600 font-bold text-sm">6</span>
              有効な計画 / ACTIVE計画
            </h3>
            <span className="text-xs font-bold text-slate-400 bg-slate-50 px-2.5 py-1 rounded-lg">工程 6/7</span>
          </div>

          {activePlan ? (
            <div className="bg-emerald-50/30 border border-emerald-200/80 p-5 rounded-2xl relative overflow-hidden">
              <div className="absolute top-0 left-0 w-2 h-full bg-emerald-500" />
              <div className="flex justify-between items-start mb-4">
                <div>
                  <span className="bg-emerald-100 text-emerald-800 border border-emerald-200 px-2.5 py-0.5 rounded-full text-[10px] font-black inline-block mb-1.5">
                    有効な計画
                  </span>
                  <h4 className="text-md font-black text-slate-800">
                    {activePlan.long_term_goals[0]?.description ?? '長期目標が未設定です'}
                  </h4>
                </div>
                <div className="text-right shrink-0 ml-4">
                  <div className="text-[10px] font-bold text-slate-400">有効期間</div>
                  <div className="text-xs font-black text-slate-600 mt-0.5">
                    {activePlan.start_date ?? '—'} 〜 {activePlan.end_date ?? '—'}
                  </div>
                </div>
              </div>

              {activePlan.long_term_goals.length > 0 && (
                <div className="space-y-3 mt-4 pt-4 border-t border-slate-200/60">
                  <h5 className="text-xs font-black text-slate-400 flex items-center gap-1">
                    <Target className="w-3.5 h-3.5 text-indigo-500" /> 短期目標および支援方針
                  </h5>
                  <div className="grid gap-3 md:grid-cols-2">
                    {activePlan.long_term_goals.flatMap(ltg => ltg.short_term_goals).map(stg => (
                      <div key={stg.id} className="bg-white border border-slate-200 p-3 rounded-xl shadow-2xs">
                        <div className="text-xs font-black text-indigo-600 mb-1">{stg.description}</div>
                        {stg.individual_goals.map(ig => (
                          <div key={ig.id} className="text-[11px] space-y-1 mt-1 text-slate-600 font-medium">
                            <div><span className="font-bold text-slate-400">取組: </span>{ig.user_commitment}</div>
                            <div><span className="font-bold text-slate-400">支援: </span>{ig.support_actions}</div>
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-rose-50 border border-rose-200 text-rose-800 p-5 rounded-2xl font-bold text-center">
              現在、有効な（ACTIVE）個別支援計画はありません。説明と同意を完了して有効化してください。
            </div>
          )}
        </div>

        {/* 9. モニタリング */}
        <div id="section-monitoring" className="bg-white border border-slate-200 p-6 rounded-3xl shadow-sm transition-all duration-300">
          <div className="flex items-start justify-between mb-4">
            <h3 className="text-lg font-black text-slate-800 flex items-center gap-2">
              <span className="w-7 h-7 rounded-xl bg-indigo-50 flex items-center justify-center text-indigo-600 font-bold text-sm">7</span>
              モニタリング
            </h3>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-slate-400 bg-slate-50 px-2.5 py-1 rounded-lg">工程 7/7</span>
              <button className="flex items-center gap-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-600 px-2.5 py-1 rounded-lg font-bold text-xs transition-colors">
                <Plus className="w-3 h-3" /> 新規実施
              </button>
            </div>
          </div>

          {/* 期限表示 */}
          {monitoringData?.next_monitoring_due ? (
            <div className={`border-l-4 p-4 rounded-r-2xl mb-4 flex items-center justify-between ${
              isOverdue ? 'bg-rose-50 border-rose-500' : isUrgent ? 'bg-amber-50 border-amber-500' : 'bg-slate-50 border-slate-300'
            }`}>
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-xl shrink-0 ${
                  isOverdue ? 'bg-rose-100 text-rose-700' : isUrgent ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-600'
                }`}>
                  <AlertTriangle className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-[10px] font-black text-slate-400">次回モニタリング期限（暫定）</div>
                  <div className="text-md font-black text-slate-800 mt-0.5">
                    {monitoringData.next_monitoring_due}
                    <span className="text-xs font-bold ml-2">
                      {isOverdue ? `(${Math.abs(daysUntil!)}日超過)` : daysUntil !== null ? `(残り${daysUntil}日)` : ''}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-slate-50 p-3 rounded-xl border border-slate-100 text-xs text-slate-400 font-bold mb-4">
              次回モニタリング期限が設定されていません。
            </div>
          )}

          {/* 履歴 */}
          {(monitoringData?.history ?? []).length === 0 ? (
            <div className="border border-dashed border-slate-200 p-6 rounded-2xl text-center">
              <Clock className="w-8 h-8 text-slate-300 mx-auto mb-2" />
              <p className="text-sm font-bold text-slate-500">過去のモニタリング報告はありません</p>
              <p className="text-xs text-slate-400 mt-1">日々の支援実績に基づいて、計画の達成状況を定期的に評価した報告書です。</p>
            </div>
          ) : (
            <div className="space-y-3">
              {monitoringData!.history.map(r => (
                <div key={r.id} className="bg-slate-50 border border-slate-200/60 p-4 rounded-2xl">
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <div className="text-[10px] font-bold text-slate-400">実施日: {r.report_date}</div>
                      <h4 className="text-xs font-black text-slate-800 mt-0.5">計画ID: {r.support_plan_id} の進捗評価</h4>
                    </div>
                    <span className="text-[10px] font-bold text-slate-500">評価者: {r.supporter_name}</span>
                  </div>
                  <p className="text-xs font-medium text-slate-700 leading-relaxed">{r.monitoring_summary}</p>
                  {r.target_goal_progress_notes && (
                    <div className="mt-2 text-[10px] font-medium text-slate-500 bg-white p-2 rounded-lg border border-slate-100">
                      <span className="font-bold">目標進捗: </span>{r.target_goal_progress_notes}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 10. 次期計画・見直し (マージされた履歴) */}
        <div id="section-history" className="bg-white border border-slate-200 p-6 rounded-3xl shadow-sm transition-all duration-300">
          <div className="flex items-start justify-between mb-4">
            <h3 className="text-lg font-black text-slate-800 flex items-center gap-2">
              <span className="w-7 h-7 rounded-xl bg-slate-100 flex items-center justify-center text-slate-500 font-bold text-sm">8</span>
              次期計画・計画履歴
            </h3>
            <span className="text-xs font-bold text-slate-400 bg-slate-50 px-2.5 py-1 rounded-lg">履歴</span>
          </div>

          {(!plansData?.plan_history || plansData.plan_history.length === 0) ? (
            <p className="text-xs font-bold text-slate-400 p-6 text-center bg-slate-50 border border-slate-200 rounded-2xl">
              過去の個別支援計画データはありません。
            </p>
          ) : (
            <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-2xs">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-500">
                    <th className="p-3 font-black uppercase">ステータス</th>
                    <th className="p-3 font-black uppercase">期間</th>
                    <th className="p-3 font-black uppercase">作成日</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {plansData.plan_history.map(p => {
                    const st = statusLabel[p.plan_status] ?? { label: p.plan_status, color: 'bg-slate-100 text-slate-500' };
                    return (
                      <tr key={p.id} className="hover:bg-slate-50/50 transition-colors">
                        <td className="p-3">
                          <span className={`text-[10px] font-black px-2 py-0.5 rounded-full ${st.color}`}>{st.label}</span>
                        </td>
                        <td className="p-3 font-bold text-slate-700">{p.start_date ?? '—'} 〜 {p.end_date ?? '—'}</td>
                        <td className="p-3 font-medium text-slate-500">{p.created_at ? new Date(p.created_at).toLocaleDateString() : '—'}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

      </div>

      {/* 同意手続きモーダル */}
      {showConsentModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl shadow-xl border border-slate-200 max-w-md w-full overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between">
              <h3 className="font-black text-slate-800 text-base">個別支援計画の説明と同意の登録</h3>
              <button 
                onClick={() => setShowConsentModal(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-50 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="p-6 space-y-4">
              {consentError && (
                <div className="bg-rose-50 border border-rose-200 text-rose-700 p-3.5 rounded-xl text-xs font-bold flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-rose-500 shrink-0" />
                  <span>{consentError}</span>
                </div>
              )}

              <div>
                <label className="block text-xs font-black text-slate-500 mb-1.5">同意方法</label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => setConsentProofType('DIGITAL_SIGNATURE')}
                    className={`py-3 px-4 rounded-xl border text-center font-bold text-xs transition-all ${
                      consentProofType === 'DIGITAL_SIGNATURE'
                        ? 'border-indigo-600 bg-indigo-50/60 text-indigo-700 font-black ring-2 ring-indigo-500/20'
                        : 'border-slate-200 hover:bg-slate-50 text-slate-600'
                    }`}
                  >
                    電子署名 (手書きサイン)
                  </button>
                  <button
                    type="button"
                    onClick={() => setConsentProofType('IN_PERSON_HANDOVER')}
                    className={`py-3 px-4 rounded-xl border text-center font-bold text-xs transition-all ${
                      consentProofType === 'IN_PERSON_HANDOVER'
                        ? 'border-indigo-600 bg-indigo-50/60 text-indigo-700 font-black ring-2 ring-indigo-500/20'
                        : 'border-slate-200 hover:bg-slate-50 text-slate-600'
                    }`}
                  >
                    対面説明 (受領確認)
                  </button>
                </div>
              </div>

              <div>
                <label htmlFor="signerName" className="block text-xs font-black text-slate-500 mb-1">
                  {consentProofType === 'DIGITAL_SIGNATURE' ? '署名者氏名' : '受領者氏名'} (本人またはご家族)
                </label>
                <input
                  type="text"
                  id="signerName"
                  value={signerName}
                  onChange={(e) => setSignerName(e.target.value)}
                  placeholder="例：山田 太郎"
                  className="w-full border border-slate-200 rounded-xl px-3.5 py-2 text-sm focus:outline-hidden focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500 font-bold"
                  disabled={consentSubmitting}
                />
              </div>

              <div className="bg-slate-50 p-4 rounded-xl border border-slate-100 text-[10px] leading-relaxed text-slate-500 font-medium">
                <p className="font-bold text-slate-600 mb-0.5">⚠️ 業務ルール上の重要な注意事項</p>
                説明と同意の手続きを登録すると、該当の個別支援計画は自動的に <span className="text-emerald-600 font-bold">有効 (ACTIVE)</span> ステータスへ移行し、直ちにサービス実績や日報作成に適用されます。この操作は監査ログに記録され、取り消しできません。
              </div>
            </div>

            <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setShowConsentModal(false)}
                className="px-4 py-2 rounded-xl text-xs font-bold text-slate-500 hover:bg-slate-100 transition-colors"
                disabled={consentSubmitting}
              >
                キャンセル
              </button>
              <button
                type="button"
                onClick={handleConsentSubmit}
                disabled={consentSubmitting}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-black transition-colors shadow-sm disabled:opacity-50 flex items-center gap-1.5"
              >
                {consentSubmitting ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    処理中...
                  </>
                ) : (
                  '同意を登録して有効化'
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 新規計画作成モーダル */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl shadow-xl border border-slate-200 max-w-4xl w-full h-[90vh] flex flex-col overflow-hidden animate-in zoom-in-95 duration-200">
            {/* ヘッダー */}
            <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <div>
                <h3 className="font-black text-slate-800 text-base flex items-center gap-2">
                  <FileText className="w-5 h-5 text-indigo-600" /> {editingPlanId ? '個別支援計画（原案）の編集' : '個別支援計画（原案）の新規作成'}
                </h3>
                <p className="text-[10px] text-slate-400 font-bold mt-0.5">※ 未入力の方針項目は暫定アセスメント / 暫定支援方針として自動生成されます。</p>
              </div>
              <button 
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-100 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* フォーム本体（スクロール可） */}
            <form onSubmit={handleCreatePlanSubmit} className="flex-1 overflow-y-auto p-6 space-y-6">
              {createError && (
                <div className="bg-rose-50 border border-rose-200 text-rose-700 p-4 rounded-2xl text-xs font-bold flex items-center gap-2">
                  <AlertCircle className="w-5 h-5 text-rose-500 shrink-0" />
                  <span>{createError}</span>
                </div>
              )}

              {/* 1. 計画期間 */}
              <div className="bg-slate-50/70 border border-slate-200 p-5 rounded-2xl space-y-4">
                <h4 className="text-xs font-black text-indigo-700 flex items-center gap-1.5 uppercase tracking-wider">
                  <span className="w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-[10px]">1</span>
                  1. 計画期間設定
                </h4>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[10px] font-black text-slate-400 mb-1">開始日 (必須)</label>
                    <input 
                      type="date"
                      required
                      value={formPlanStartDate}
                      onChange={(e) => setFormPlanStartDate(e.target.value)}
                      className="w-full border border-slate-200 rounded-xl px-3.5 py-2 text-xs focus:outline-hidden focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500 font-bold"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-black text-slate-400 mb-1">終了日 (必須)</label>
                    <input 
                      type="date"
                      required
                      value={formPlanEndDate}
                      onChange={(e) => setFormPlanEndDate(e.target.value)}
                      className="w-full border border-slate-200 rounded-xl px-3.5 py-2 text-xs focus:outline-hidden focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500 font-bold"
                    />
                  </div>
                </div>
              </div>

              {/* 2. 本人の希望・支援方針 */}
              <div className="bg-slate-50/70 border border-slate-200 p-5 rounded-2xl space-y-4">
                <h4 className="text-xs font-black text-indigo-700 flex items-center gap-1.5 uppercase tracking-wider">
                  <span className="w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-[10px]">2</span>
                  2. 本人の希望 ＆ 支援方針
                </h4>
                <div className="space-y-3">
                  <div>
                    <label className="block text-[10px] font-black text-slate-400 mb-1">本人の意向・希望</label>
                    <textarea 
                      placeholder="例：自立した生活に向けて、就労のトレーニングを積みたい。"
                      value={formUserIntentionContent}
                      onChange={(e) => setFormUserIntentionContent(e.target.value)}
                      className="w-full border border-slate-200 rounded-xl px-3.5 py-2 text-xs focus:outline-hidden focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500 font-medium min-h-[60px]"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-black text-slate-400 mb-1">総合的な支援方針</label>
                    <textarea 
                      placeholder="例：本人の希望に配慮し、作業スキルの向上と情緒の安定を目指した支援を行う。"
                      value={formSupportPolicyContent}
                      onChange={(e) => setFormSupportPolicyContent(e.target.value)}
                      className="w-full border border-slate-200 rounded-xl px-3.5 py-2 text-xs focus:outline-hidden focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500 font-medium min-h-[60px]"
                    />
                  </div>
                </div>
              </div>

              {/* 3. 長期目標 */}
              <div className="bg-slate-50/70 border border-slate-200 p-5 rounded-2xl space-y-4">
                <div className="flex justify-between items-center">
                  <h4 className="text-xs font-black text-indigo-700 flex items-center gap-1.5 uppercase tracking-wider">
                    <span className="w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-[10px]">3</span>
                    3. 目標設定 (長期 ➔ 短期 ➔ 個別支援内容)
                  </h4>
                  <button
                    type="button"
                    onClick={addLongTermGoal}
                    className="flex items-center gap-1 text-[10px] bg-indigo-50 text-indigo-600 px-2.5 py-1 rounded-lg font-black hover:bg-indigo-100 transition-colors"
                  >
                    <Plus className="w-3.5 h-3.5" /> 長期目標を追加
                  </button>
                </div>

                {formLongTermGoals.map((ltg, ltgIdx) => (
                  <div key={ltgIdx} className="bg-white border border-slate-200 p-4 rounded-xl space-y-4 shadow-2xs relative">
                    {formLongTermGoals.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeLongTermGoal(ltgIdx)}
                        className="absolute top-3 right-3 text-slate-400 hover:text-rose-600 p-1.5 rounded-lg hover:bg-rose-50 transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                    
                    <div>
                      <label className="block text-[10px] font-black text-slate-500 mb-1">【長期目標 {ltgIdx + 1}】目標記述</label>
                      <input 
                        type="text"
                        required
                        placeholder="例：毎日休まずに通所し、作業に集中できるようになる"
                        value={ltg.description}
                        onChange={(e) => {
                          const next = [...formLongTermGoals];
                          next[ltgIdx].description = e.target.value;
                          setFormLongTermGoals(next);
                        }}
                        className="w-full border border-slate-200 rounded-xl px-3.5 py-2 text-xs focus:outline-hidden focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500 font-bold"
                      />
                    </div>

                    {/* 短期目標ループ */}
                    <div className="pl-4 border-l-2 border-slate-100 space-y-4">
                      <div className="flex justify-between items-center">
                        <span className="text-[10px] font-black text-slate-400">【短期目標】</span>
                        <button
                          type="button"
                          onClick={() => addShortTermGoal(ltgIdx)}
                          className="flex items-center gap-1 text-[9px] text-indigo-600 hover:text-indigo-800 font-bold"
                        >
                          + 短期目標を追加
                        </button>
                      </div>

                      {ltg.short_term_goals.map((stg: any, stgIdx: number) => (
                        <div key={stgIdx} className="bg-slate-50/50 p-3.5 rounded-lg space-y-3 relative border border-slate-100">
                          {ltg.short_term_goals.length > 1 && (
                            <button
                              type="button"
                              onClick={() => removeShortTermGoal(ltgIdx, stgIdx)}
                              className="absolute top-2 right-2 text-slate-400 hover:text-rose-600 p-1"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}

                          <div>
                            <label className="block text-[9px] font-black text-slate-500 mb-1">短期目標 {stgIdx + 1} の内容</label>
                            <input 
                              type="text"
                              required
                              placeholder="例：作業開始時に課題を確認し、自己判断で進められる"
                              value={stg.description}
                              onChange={(e) => {
                                const next = [...formLongTermGoals];
                                next[ltgIdx].short_term_goals[stgIdx].description = e.target.value;
                                setFormLongTermGoals(next);
                              }}
                              className="w-full border border-slate-200 rounded-lg px-3 py-1.5 text-xs focus:outline-hidden focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500 font-medium"
                            />
                          </div>

                          {/* 個別支援内容ループ */}
                          <div className="pl-3 border-l-2 border-indigo-150 space-y-3">
                            <div className="flex justify-between items-center">
                              <span className="text-[9px] font-bold text-slate-400">個別支援内容</span>
                              <button
                                type="button"
                                onClick={() => addIndividualGoal(ltgIdx, stgIdx)}
                                className="text-[8px] text-indigo-500 hover:text-indigo-700 font-bold"
                              >
                                + 支援内容を追加
                              </button>
                            </div>

                            {stg.individual_goals.map((ig: any, igIdx: number) => (
                              <div key={igIdx} className="bg-white p-3 rounded-lg border border-slate-200/80 space-y-2.5 relative">
                                {stg.individual_goals.length > 1 && (
                                  <button
                                    type="button"
                                    onClick={() => removeIndividualGoal(ltgIdx, stgIdx, igIdx)}
                                    className="absolute top-1.5 right-1.5 text-slate-400 hover:text-rose-600 p-1"
                                  >
                                    <Trash2 className="w-3 h-3" />
                                  </button>
                                )}

                                <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
                                  <div>
                                    <label className="block text-[8px] font-bold text-slate-400 mb-0.5">具体的な目標</label>
                                    <input 
                                      type="text"
                                      required
                                      placeholder="例：手順書を見ながら進める"
                                      value={ig.concrete_goal}
                                      onChange={(e) => {
                                        const next = [...formLongTermGoals];
                                        next[ltgIdx].short_term_goals[stgIdx].individual_goals[igIdx].concrete_goal = e.target.value;
                                        setFormLongTermGoals(next);
                                      }}
                                      className="w-full border border-slate-200 rounded-md px-2 py-1 text-[11px] focus:outline-hidden font-medium"
                                    />
                                  </div>
                                  <div>
                                    <label className="block text-[8px] font-bold text-slate-400 mb-0.5">本人の取り組み</label>
                                    <input 
                                      type="text"
                                      placeholder="例：分からない時は支援員に確認する"
                                      value={ig.user_commitment}
                                      onChange={(e) => {
                                        const next = [...formLongTermGoals];
                                        next[ltgIdx].short_term_goals[stgIdx].individual_goals[igIdx].user_commitment = e.target.value;
                                        setFormLongTermGoals(next);
                                      }}
                                      className="w-full border border-slate-200 rounded-md px-2 py-1 text-[11px] focus:outline-hidden font-medium"
                                    />
                                  </div>
                                  <div>
                                    <label className="block text-[8px] font-bold text-slate-400 mb-0.5">主な支援内容</label>
                                    <input 
                                      type="text"
                                      placeholder="例：視覚的支援ツール(手順書)の整備"
                                      value={ig.support_actions}
                                      onChange={(e) => {
                                        const next = [...formLongTermGoals];
                                        next[ltgIdx].short_term_goals[stgIdx].individual_goals[igIdx].support_actions = e.target.value;
                                        setFormLongTermGoals(next);
                                      }}
                                      className="w-full border border-slate-200 rounded-md px-2 py-1 text-[11px] focus:outline-hidden font-medium"
                                    />
                                  </div>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1 border-t border-slate-100">
                                  <div>
                                    <label className="block text-[8px] font-bold text-slate-400 mb-0.5">サービス種別</label>
                                    <select
                                      value={ig.service_type}
                                      onChange={(e) => {
                                        const next = [...formLongTermGoals];
                                        next[ltgIdx].short_term_goals[stgIdx].individual_goals[igIdx].service_type = e.target.value;
                                        setFormLongTermGoals(next);
                                      }}
                                      className="w-full border border-slate-200 rounded-md px-2 py-1 text-[11px] bg-white focus:outline-hidden font-bold text-slate-700"
                                    >
                                      <option value="TRAINING">自立訓練(生活)</option>
                                      <option value="WORK_TRANSITION">就労移行支援</option>
                                      <option value="B_EMPLOYMENT">就労継続B型</option>
                                      <option value="A_EMPLOYMENT">就労継続A型</option>
                                    </select>
                                  </div>
                                  <div className="flex items-center gap-1.5 pt-2">
                                    <input 
                                      type="checkbox"
                                      id={`deemed-${ltgIdx}-${stgIdx}-${igIdx}`}
                                      checked={ig.is_facility_in_deemed}
                                      onChange={(e) => {
                                        const next = [...formLongTermGoals];
                                        next[ltgIdx].short_term_goals[stgIdx].individual_goals[igIdx].is_facility_in_deemed = e.target.checked;
                                        setFormLongTermGoals(next);
                                      }}
                                      className="rounded text-indigo-600 focus:ring-indigo-500 w-3.5 h-3.5"
                                    />
                                    <label htmlFor={`deemed-${ltgIdx}-${stgIdx}-${igIdx}`} className="text-[9px] font-bold text-slate-500">
                                      施設外支援・みなし設定
                                    </label>
                                  </div>
                                  <div className="flex items-center gap-1.5 pt-2">
                                    <input 
                                      type="checkbox"
                                      id={`prep-${ltgIdx}-${stgIdx}-${igIdx}`}
                                      checked={ig.is_work_preparation_positioning}
                                      onChange={(e) => {
                                        const next = [...formLongTermGoals];
                                        next[ltgIdx].short_term_goals[stgIdx].individual_goals[igIdx].is_work_preparation_positioning = e.target.checked;
                                        setFormLongTermGoals(next);
                                      }}
                                      className="rounded text-indigo-600 focus:ring-indigo-500 w-3.5 h-3.5"
                                    />
                                    <label htmlFor={`prep-${ltgIdx}-${stgIdx}-${igIdx}`} className="text-[9px] font-bold text-slate-500">
                                      就労準備移行等連携
                                    </label>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </form>

            {/* フッター */}
            <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex items-center justify-end gap-3 shrink-0">
              <button
                type="button"
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 rounded-xl text-xs font-bold text-slate-500 hover:bg-slate-100 transition-colors"
                disabled={createSubmitting}
              >
                キャンセル
              </button>
              <button
                type="submit"
                onClick={handleCreatePlanSubmit}
                disabled={createSubmitting}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-black transition-colors shadow-sm disabled:opacity-50 flex items-center gap-1.5"
              >
                {createSubmitting ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    {editingPlanId ? '更新中...' : '作成中...'}
                  </>
                ) : (
                  editingPlanId ? '原案を更新' : '原案を作成して目標保存'
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 次期原案作成確認モーダル */}
      {showCloneConfirmModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl shadow-xl border border-slate-200 max-w-md w-full overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between">
              <h3 className="font-black text-slate-800 text-base flex items-center gap-1.5">
                <Copy className="w-4 h-4 text-indigo-600" /> 次期計画原案の作成
              </h3>
              <button 
                onClick={() => setShowCloneConfirmModal(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-50 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="p-6 space-y-4">
              <div className="bg-indigo-50 text-indigo-900 p-4 rounded-2xl border border-indigo-100 text-xs font-bold">
                現行の成案をもとに、次期原案を作成します。目標や支援内容はコピーされます。モニタリング結果を反映して編集してください。
              </div>

              <div className="bg-slate-50 p-4 rounded-xl border border-slate-100 text-[10px] leading-relaxed text-slate-500 font-medium">
                <p className="font-bold text-slate-600 mb-0.5">💡 コピー後の挙動について</p>
                作成された計画は必ず <span className="font-black">DRAFT (原案)</span> 状態となり、計画期間は自動的に現行計画の終了日の翌日から開始するように設定されます。
              </div>
            </div>

            <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setShowCloneConfirmModal(false)}
                className="px-4 py-2 rounded-xl text-xs font-bold text-slate-500 hover:bg-slate-100 transition-colors"
                disabled={cloningSubmitting}
              >
                キャンセル
              </button>
              <button
                type="button"
                onClick={handleCreateNextPlan}
                disabled={cloningSubmitting}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-black transition-colors shadow-sm disabled:opacity-50 flex items-center gap-1.5"
              >
                {cloningSubmitting ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    複製中...
                  </>
                ) : (
                  '次期原案を作成する'
                )}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
