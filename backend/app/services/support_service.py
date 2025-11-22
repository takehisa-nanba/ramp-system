# backend/app/services/support_service.py

from backend.app.extensions import db
from backend.app.models import (
    User, Supporter, 
    SupportPlan, LongTermGoal, ShortTermGoal, IndividualSupportGoal,
    SupportConferenceLog, DocumentConsentLog,
    DailyLog,
    HolisticSupportPolicy
)
from sqlalchemy import func, exc
# ★ 修正: timezone 対応
from datetime import datetime, timezone

class SupportService:
    """
    Handles the entire support plan workflow (Principle 8) and
    validates daily logs against active plans (Principle 9).
    """

    def create_plan_draft(self, user_id: int, sabikan_id: int, based_on_policy_id: int) -> SupportPlan:
        """原案(DRAFT)を作成する"""
        policy = db.session.get(HolisticSupportPolicy, based_on_policy_id)
        if not policy or policy.user_id != user_id:
            raise Exception("Invalid HolisticSupportPolicy ID.")

        new_plan = SupportPlan(
            user_id=user_id,
            plan_version=1,
            plan_status='DRAFT',
            sabikan_approved_by_id=sabikan_id,
            holistic_support_policy_id=based_on_policy_id
        )
        db.session.add(new_plan)
        return new_plan

    def log_support_conference_and_approve(
        self, 
        plan_id: int, 
        sabikan_id: int, 
        conference_date: datetime, 
        content: str, 
        user_participated: bool,
        reason_for_absence: str = None
    ) -> SupportConferenceLog:
        """
        支援会議ログを記録し、サビ管が承認して「同意待ち」ステータスへ移行する（Lock 1）。
        """
        plan = db.session.get(SupportPlan, plan_id)
        if not plan or plan.plan_status != 'DRAFT':
            raise Exception("Plan is not in DRAFT status.")
            
        # 不在時の理由チェック
        if not user_participated and not (reason_for_absence and len(reason_for_absence) > 0):
            raise Exception("Reason for absence is required.")
            
        conference_log = SupportConferenceLog(
            plan_id=plan_id,
            conference_date=conference_date,
            minutes_content=content,
            participant_user_flag=user_participated,
            reason_for_user_absence=reason_for_absence
        )
        
        # ★ LOCK 1: サビ管承認
        plan.plan_status = 'PENDING_CONSENT'
        plan.sabikan_approved_by_id = sabikan_id
        plan.sabikan_approved_at = datetime.now(timezone.utc)
        
        db.session.add(conference_log)
        db.session.add(plan)
        return conference_log

    def finalize_and_activate_plan(self, plan_id: int, consent_log_id: int) -> SupportPlan:
        """
        利用者同意に基づき、計画を「有効（ACTIVE）」化して最終ロックする（Lock 2）。
        """
        plan = db.session.get(SupportPlan, plan_id)
        consent_log = db.session.get(DocumentConsentLog, consent_log_id)
        
        if not plan or plan.plan_status != 'PENDING_CONSENT':
            raise Exception("Plan is not in 'PENDING_CONSENT' status.")
        
        if not consent_log or consent_log.document_id != plan_id:
            raise Exception("Consent log mismatch.")

        # 既存のACTIVE計画があればアーカイブ
        old_active_plan = SupportPlan.query.filter_by(
            user_id=plan.user_id,
            plan_status='ACTIVE'
        ).first()
        if old_active_plan:
            old_active_plan.plan_status = 'ARCHIVED'
            db.session.add(old_active_plan)

        # ★ LOCK 2: 最終確定
        plan.plan_status = 'ACTIVE'
        consent_log.plan = plan 
        
        db.session.add(plan)
        db.session.add(consent_log)
        return plan
        
    def validate_daily_log_against_plan(self, user_id: int, goal_id: int) -> bool:
        """
        Plan-Activity ガードレール。
        日報が有効な計画（ACTIVE）の目標に紐づいているか検証する。
        """
        goal = db.session.get(IndividualSupportGoal, goal_id)
        if not goal:
            return False

        # Goal -> Short -> Long -> Plan のリレーションを辿り、ACTIVEかつUser一致を確認
        plan = (
            SupportPlan.query
            .join(LongTermGoal, SupportPlan.id == LongTermGoal.plan_id)
            .join(ShortTermGoal, LongTermGoal.id == ShortTermGoal.long_term_goal_id)
            .join(IndividualSupportGoal, ShortTermGoal.id == IndividualSupportGoal.short_term_goal_id)
            .filter(IndividualSupportGoal.id == goal_id)
            .filter(SupportPlan.user_id == user_id)
            .filter(SupportPlan.plan_status == 'ACTIVE')
            .first()
        )
        return plan is not None