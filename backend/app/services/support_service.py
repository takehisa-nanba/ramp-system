# backend/app/services/support_service.py

from backend.app.extensions import db
from backend.app.models import (
    User, Supporter, 
    SupportPlan, LongTermGoal, ShortTermGoal, IndividualSupportGoal,
    SupportConferenceLog, DocumentConsentLog,
    DailyLog,
    HolisticSupportPolicy,
    ServiceTypeMaster, # 法定期間取得用
    AbsenceResponseLog, # 不在時の証拠取得用
    # Continuity Log モデル
    ISP_Continuity_Gap_Log, 
    GapReasonType
)
from sqlalchemy import func, exc
from datetime import datetime, timezone, timedelta, date
from typing import Optional 
import logging
logger = logging.getLogger(__name__)

# カスタム例外の定義 (API層にSoft/Hard Blockの区別を伝えるための核)
class ContinuityGapRequiredError(Exception):
    """L2 Soft Block: ギャップ記録が必要だが、未入力の場合に発生"""
    def __init__(self, previous_plan_id: int):
        self.message = "Previous ISP ended, but new plan start date is discontinuous. ISP_Continuity_Gap_Log input is mandatory."
        self.previous_plan_id = previous_plan_id
        super().__init__(self.message)

class FinalizationPendingError(Exception):
    """L3 Hard Block: ギャップ記録は存在するが、承認(Responsible_ID)が未完了の場合に発生"""
    pass

class SupportService:
    """
    個別支援計画のライフサイクル（作成、承認、有効化）と、
    日報に対する計画の整合性検証（ガードレール）を担う。
    """
    
    # 【新規追加】依存性注入のためのコンストラクタ
    def __init__(self, compliance_service=None):
        self.compliance_service = compliance_service

    def create_plan_draft(self, user_id: int, sabikan_id: int, based_on_policy_id: int) -> SupportPlan:
        """
        原案(DRAFT)を作成する。
        開始日は、初回利用日または前計画の終了日の翌日に設定し、遡及的連続性を担保する。
        """
        policy = db.session.get(HolisticSupportPolicy, based_on_policy_id)
        if not policy or policy.user_id != user_id:
            logger.error(f"❌ User {user_id}: Invalid HolisticSupportPolicy ID {based_on_policy_id}.")
            raise Exception("Invalid HolisticSupportPolicy ID.")

        user_entity = db.session.get(User, user_id)
        
        # 1. 前の計画とユーザーのサービス開始日を取得
        # SupportPlan.plan_start_date がモデルに存在することを前提
        last_plan = SupportPlan.query.filter_by(user_id=user_id).order_by(SupportPlan.plan_start_date.desc()).first()
        
        # 2. 計画の開始日 (plan_start_date) を決定
        if last_plan and last_plan.plan_end_date:
            # ★ 継続利用の場合: 前計画の翌日 (遡及的連続性の強制)
            plan_start_date = last_plan.plan_end_date + timedelta(days=1)
            logger.info(f"🔍 Plan start date set to next day: {plan_start_date}")
            
        elif user_entity and user_entity.service_start_date:
            # ★ 初回利用の場合: Userモデルのサービス開始日 (初回利用日) を使用
            plan_start_date = user_entity.service_start_date
            logger.info(f"🔍 Plan start date set to Service Start Date: {plan_start_date}")
            
        else:
            # データ不完全な場合: 緊急策として今日の日付を設定
            logger.critical(f"🔥 CRITICAL: Service start date missing for User {user_id}. Using today.")
            plan_start_date = datetime.now(timezone.utc).date()

        # 3. 法定見直し期間と終了日の設定
        review_months = 3 # 仮定
        plan_end_date = plan_start_date + timedelta(days=30 * review_months)

        new_plan = SupportPlan(
            user_id=user_id,
            plan_version=1,
            plan_status='DRAFT',
            sabikan_approved_by_id=sabikan_id,
            holistic_support_policy_id=based_on_policy_id,
            plan_start_date=plan_start_date,
            plan_end_date=plan_end_date 
        )
        db.session.add(new_plan)
        logger.info(f"✅ DRAFT Plan {new_plan.id} created. Start: {plan_start_date}")
        return new_plan

    def log_support_conference_and_approve(
        self, 
        plan_id: int, 
        sabikan_id: int, 
        conference_date: datetime, 
        content: str, 
        user_participated: bool,
        reason_for_absence: Optional[str] = None,
        is_sabikan_digital_declaration: bool = False,
        absence_monitoring_summary: Optional[str] = None
    ) -> SupportConferenceLog:
        """
        支援会議ログを記録し、サビ管が承認して「同意待ち（PENDING_CONSENT）」ステータスへ移行する（Lock 1）。
        不在時はデジタル宣誓と不在証拠の提出を強制し、実質的関与の欠如を防ぐ。
        """
        plan = db.session.get(SupportPlan, plan_id)
        if not plan or plan.plan_status != 'DRAFT':
            logger.warning(f"❌ Plan {plan_id} must be in DRAFT status for approval.")
            raise Exception("Plan is not in DRAFT status.")

        # --- 🚨 哲学の実装: 不在時の厳格なチェック（関与の欠如防止） ---
        if not user_participated:
            
            # 1. デジタル宣誓 (サビ管の直感) の強制
            if not is_sabikan_digital_declaration:
                # 【STEP 3-2: URACフックの活性化ロジックを追記】
                if self.compliance_service:
                    risk_context = {
                        "source_service": "SupportService",
                        "action_attempted": "log_support_conference_and_approve",
                        "reason_for_failure": "Digital Declaration Missing",
                        "plan_id": plan_id
                    }
                    try:
                        self.compliance_service.log_unresponsive_risk_increment(
                            user_id=plan.user_id,
                            risk_context=risk_context
                        )
                        logger.warning(f"⚠️ URAC incremented for Plan {plan_id} due to missing digital declaration.")
                    except Exception as e:
                        logger.critical(f"🔥 CRITICAL: Failed to log URAC increment. Error: {e}")
                
                logger.error(f"❌ Plan {plan_id}: User absent, Digital Declaration missing.")
                raise Exception("User is absent. Digital Declaration required for PENDING_CONSENT transition.")

            # 2. 実態反映の証明 (不在時の状況モニタリング概要) の強制
            if not (absence_monitoring_summary and len(absence_monitoring_summary.strip()) > 10):
                logger.error(f"❌ Plan {plan_id}: Absence Monitoring Summary missing (Duty 2 breach).")
                raise Exception("Absence Monitoring Summary (10+ chars) is required when user is absent.")
            
            # 3. 不在時の管理努力の証拠 (AbsenceResponseLog) の存在確認 (義務)
            absence_logs_count = db.session.query(AbsenceResponseLog).filter(
                AbsenceResponseLog.user_id == plan.user_id,
                AbsenceResponseLog.linked_plan_id == plan_id
            ).count()

            if absence_logs_count == 0:
                logger.error(f"❌ Plan {plan_id}: No AbsenceResponseLog linked to this plan found. Cannot approve.")
                raise Exception("Missing mandatory AbsenceResponseLog evidence for absent user.")
            
        # --- ログの作成（Step 3 会議の記録）---
        conference_log = SupportConferenceLog(
            plan_id=plan_id,
            conference_date=conference_date,
            minutes_content=content,
            participant_user_flag=user_participated,
            reason_for_user_absence=reason_for_absence
        )
        
        # ★ LOCK 1: サビ管承認とデジタル宣誓の実行点
        plan.plan_status = 'PENDING_CONSENT'
        plan.sabikan_approved_by_id = sabikan_id
        plan.sabikan_approved_at = datetime.now(timezone.utc)
        
        db.session.add(conference_log)
        db.session.add(plan)
        logger.info(f"✅ Plan {plan_id} approved by Sabikan {sabikan_id}. Status: PENDING_CONSENT.")
        return conference_log
    
    def validate_plan_continuity_on_finalize(
        self, 
        plan_id: int, 
        gap_log_data: Optional[dict] = None, # フロントから送られるギャップデータ
        responsible_id_approving: Optional[str] = None # 最終承認を実行した職員ID
    ) -> bool:
        """
        L1-L4ロジックを実行し、計画の連続性を検証・確定する。
        これは /api/v1/isp/finalize の前段で実行される。
        """
        new_plan = db.session.get(SupportPlan, plan_id)
        if not new_plan or new_plan.plan_status != 'PENDING_CONSENT':
            raise Exception("Plan must be PENDING_CONSENT status for continuity validation.")
        
        # 1. 直前の計画を取得
        previous_plan = SupportPlan.query.filter_by(user_id=new_plan.user_id).order_by(SupportPlan.plan_end_date.desc()).first()
        
        # 前の計画が存在しない場合、連続性チェックは不要
        if not previous_plan:
            logger.info("🔍 Continuity check skipped: No previous plan found.")
            return True # L1-L4パス
        
        previous_end_date = previous_plan.plan_end_date
        expected_start_date = previous_end_date + timedelta(days=1)
        proposed_start_date = new_plan.plan_start_date

        # L1. 連続性のチェック
        is_continuous = (proposed_start_date == expected_start_date)
        is_gap_case = (proposed_start_date > expected_start_date)

        if is_continuous:
            return True # L1 PASS: 連続。ムダのない処理。
        
        if is_gap_case:
            # L1. 不一致発生 (断続的) -> L2, L3へ移行
            
            # 既存のギャップ記録をチェック（既にL2 Soft Blockが処理され、DBに一時保存されている可能性を排除）
            existing_gap_log = db.session.query(ISP_Continuity_Gap_Log).filter(
                ISP_Continuity_Gap_Log.Previous_Plan_ID == previous_plan.id
            ).first()

            # L2. 不一致時の対応 (Soft Block要求)
            if not existing_gap_log and not gap_log_data:
                # L2.1: 不一致の場合、直ちに処理を停止せず、Soft Block例外を投げる
                raise ContinuityGapRequiredError(previous_plan_id=previous_plan.id) 

            # L3. ギャップ記録 (Hard Block制御)
            log_to_process = gap_log_data if gap_log_data else existing_gap_log
            
            # L3.1: 記録と承認（Responsible_ID）が必須
            responsible_id = log_to_process.get('Responsible_ID') or responsible_id_approving
            
            if not responsible_id:
                raise FinalizationPendingError("ISP_Continuity_Gap_Log must be finalized with Responsible_ID before plan finalization.")
            
            # L4. 最終承認: ギャップ記録の永続化
            if not existing_gap_log: # 新規記録の場合のみDBに追加
                try:
                    gap_log_entry = ISP_Continuity_Gap_Log(
                        Previous_Plan_ID=previous_plan.id,
                        Gap_Reason_Type=GapReasonType(log_to_process['Gap_Reason_Type']), # Enum変換を強制
                        Gap_Reason_Detail=log_to_process['Gap_Reason_Detail'],
                        Gap_Start_Date=expected_start_date,
                        Gap_End_Date=proposed_start_date - timedelta(days=1),
                        Responsible_ID=responsible_id
                    )
                    db.session.add(gap_log_entry)
                    logger.info(f"✅ Gap Log for Plan {plan_id} created. Gap: {expected_start_date} to {proposed_start_date - timedelta(days=1)}")
                except KeyError as e:
                    logger.error(f"❌ Gap Log data missing required field: {e}")
                    raise Exception(f"Incomplete Gap Log Data: {e}")
                except exc.SQLAlchemyError as e:
                    logger.critical(f"🔥 DB Write Error for Gap Log: {e}")
                    raise Exception("Critical DB error during Gap Log creation.")
            
            # L4. ISP_Start_Dateの再確定は不要（既にproposed_start_dateとして利用）
            return True

        else: # proposed_start_date < expected_start_date (遡及)
            # これは仕様の制約 (II.4) に反する。 Hard Block
            logger.error(f"❌ Plan {plan_id}: Proposed start date {proposed_start_date} predates expected start {expected_start_date}.")
            raise ValueError("Proposed ISP_Start_Date cannot predate the expected continuous start date.")

    def finalize_and_activate_plan(self, plan_id: int, consent_log_id: int) -> SupportPlan:
        """
        利用者同意に基づき、計画を「有効（ACTIVE）」化して最終ロックする（Lock 2）。
        """
        plan = db.session.get(SupportPlan, plan_id)
        consent_log = db.session.get(DocumentConsentLog, consent_log_id)
        
        if not plan or plan.plan_status != 'PENDING_CONSENT':
            logger.warning(f"❌ Plan {plan_id} must be in PENDING_CONSENT status for final activation.")
            raise Exception("Plan is not in 'PENDING_CONSENT' status.")
        
        if not consent_log or consent_log.document_id != plan_id or consent_log.document_type != 'SUPPORT_PLAN':
            logger.warning(f"❌ Consent log {consent_log_id} mismatch with Plan {plan_id}.")
            raise Exception("Consent log mismatch.")

        # 既存のACTIVE計画があればアーカイブ（連続性を実現）
        old_active_plan = SupportPlan.query.filter_by(
            user_id=plan.user_id,
            plan_status='ACTIVE'
        ).first()
        if old_active_plan:
            old_active_plan.plan_status = 'ARCHIVED'
            db.session.add(old_active_plan)

        # ★ LOCK 2: 最終確定 (ACTIVE化)
        plan.plan_status = 'ACTIVE'
        consent_log.plan = plan 
        
        db.session.add(plan)
        db.session.add(consent_log)
        logger.info(f"🔥 Plan {plan_id} ACTIVATED and fully consented by User {plan.user_id}.")
        return plan
        
    def validate_daily_log_against_plan(self, user_id: int, goal_id: int, log_date: datetime, location_type: str) -> bool:
        """
        Plan-Activity & Location ガードレール。
        日報が有効な計画の目標に紐づき、かつ場所の整合性を検証する。
        """
        goal = db.session.get(IndividualSupportGoal, goal_id)
        if not goal:
            logger.warning(f"❌ Log for User {user_id}: Goal ID {goal_id} not found.")
            return False

        # Goal -> Plan へのリレーションを辿り、ACTIVEかつUser一致を確認
        plan = (
            SupportPlan.query
            .join(LongTermGoal, SupportPlan.id == LongTermGoal.plan_id)
            .join(ShortTermGoal, LongTermGoal.id == ShortTermGoal.long_term_goal_id)
            .join(IndividualSupportGoal, ShortTermGoal.id == IndividualSupportGoal.short_term_goal_id)
            .filter(IndividualSupportGoal.id == goal_id)
            .filter(SupportPlan.user_id == user_id)
            .filter(SupportPlan.plan_status == 'ACTIVE')
            # ★ 計画の有効期間内であることのチェックを追加
            .filter(SupportPlan.plan_start_date <= log_date.date())
            .filter(SupportPlan.plan_end_date >= log_date.date())
            .first()
        )

        if plan is None:
            logger.warning(f"❌ Log for User {user_id}: No ACTIVE plan covers date {log_date.date()}.")
            return False

        # ★ 場所の整合性チェック（簡易版）は、ここでは監査上の懸念として WARNING のみを発行
        if location_type == 'OFF_SITE_EXTERNAL' and plan.plan_status == 'ACTIVE':
             # 厳密なロジックとして、外部活動用の目標（IndividualSupportGoal）に紐づいているかをチェックすべきだが、
             # 現状は警告に留める
             pass
        
        return True