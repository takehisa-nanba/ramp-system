# 🚨 修正点: 'from app...' を 'backend.app...' に修正
from backend.app.extensions import db
from backend.app.models import (
    User, Supporter, 
    SupportPlan, LongTermGoal, ShortTermGoal, IndividualSupportGoal,
    SupportConferenceLog, DocumentConsentLog,
    DailyLog,
    HolisticSupportPolicy # 総合方針を参照
)
from sqlalchemy import func, exc
from datetime import datetime

class SupportService:
    """
    Handles the entire support plan workflow (Principle 8) and
    validates daily logs against active plans (Principle 9).
    This ensures the PDCA cycle and prevents billing errors (Gensan risk).
    """

    def create_plan_draft(self, user_id: int, sabikan_id: int, based_on_policy_id: int) -> SupportPlan:
        """
        Creates a new SupportPlan in 'DRAFT' status.
        This is the entry point for the plan creation workflow.
        """
        
        # 1. 根拠となる「総合方針」の存在確認
        policy = HolisticSupportPolicy.query.get(based_on_policy_id)
        if not policy or policy.user_id != user_id:
            raise Exception("Invalid HolisticSupportPolicy ID.")

        # 2. 新しい計画（原案）を作成
        new_plan = SupportPlan(
            user_id=user_id,
            plan_version=1, # 最初のバージョン
            plan_status='DRAFT', # 状態は「原案」
        )
        
        db.session.add(new_plan)
        
        # 3. 必要な目標(Goals)をここで追加するロジック...
        # (例: new_goal = LongTermGoal(plan=new_plan, ...))
        # db.session.add(new_goal)
        
        return new_plan

    def log_support_conference_and_approve(
        self, 
        plan_id: int, 
        sabikan_id: int, # 承認するサビ管
        conference_date: datetime, 
        content: str, 
        user_participated: bool,
        reason_for_absence: str = None
    ) -> SupportConferenceLog:
        """
        Logs the support conference (Principle 8) for a DRAFT plan.
        
        ★ 修正 (user_292) ★
        Moves the plan state to 'PENDING_CONSENT' (Lock 1) ONLY IF
        the user participated OR a valid reason for absence is provided.
        
        議事録を記録し、
        「本人が参加」または「不在理由が明記」されている場合のみ、「同意待ち」に移行する。
        """
        plan = SupportPlan.query.get(plan_id)
        if not plan or plan.plan_status != 'DRAFT':
            raise Exception("Plan is not in DRAFT status or does not exist.")
            
        # ★ NEW: 「不在」かつ「理由なし」は、法令遵守違反
        if not user_participated and not (reason_for_absence and len(reason_for_absence) > 0):
            # この時点ではログは作成するが、ステータスはDRAFTのままにする
            # (または、例外を発生させて理由の入力を強制する)
            raise Exception("A reason (reason_for_user_absence) is required if the user did not participate.")
            
        # 1. 支援会議の議事録（証憑）を作成
        conference_log = SupportConferenceLog(
            plan_id=plan_id,
            conference_date=conference_date,
            minutes_content=content,
            participant_user_flag=user_participated,
            reason_for_user_absence=reason_for_absence # ★ 不在理由を記録
        )
        
        # 2. 計画のステータスを「同意待ち」に更新（ガードレール通過時のみ）
        # ★ LOCK 1 (二重ロック) ★
        plan.plan_status = 'PENDING_CONSENT'
        plan.sabikan_approved_by_id = sabikan_id
        plan.sabikan_approved_at = datetime.utcnow()
        
        db.session.add(conference_log)
        db.session.add(plan)
        
        return conference_log

    def finalize_and_activate_plan(self, plan_id: int, consent_log_id: int) -> SupportPlan:
        """
        ★ 修正 (user_291) ★
        Applies the final lock (Lock 2) to the plan upon user consent.
        Moves the plan from 'PENDING_CONSENT' to 'ACTIVE'.
        
        「同意」に基づき、計画を「有効（ACTIVE）」にし、最終ロックをかける。
        """
        
        plan = SupportPlan.query.get(plan_id)
        consent_log = DocumentConsentLog.query.get(consent_log_id)
        
        if not plan or plan.plan_status != 'PENDING_CONSENT':
            raise Exception("Plan is not in 'PENDING_CONSENT' status.")
        
        # 証憑(consent_log)が正しい計画(plan_id)を指しているか検証
        if not consent_log or consent_log.document_id != plan_id:
            raise Exception("Consent log does not match the plan ID.")

        # 1. 古い有効な計画があれば 'ARCHIVED' にする (ムダのない移行)
        old_active_plan = SupportPlan.query.filter_by(
            user_id=plan.user_id,
            plan_status='ACTIVE'
        ).first()
        if old_active_plan:
            old_active_plan.plan_status = 'ARCHIVED'
            db.session.add(old_active_plan)

        # 2. 計画を「有効」として最終確定する
        # ★ LOCK 2 (二重ロック) ★
        plan.plan_status = 'ACTIVE'
        
        # 3. 同意ログを計画に紐づける (既に行われている場合は不要)
        consent_log.plan = plan 
        
        db.session.add(plan)
        db.session.add(consent_log)
            
        return plan
        
    def validate_daily_log_against_plan(self, user_id: int, goal_id: int) -> bool:
        """
        The "Plan-Activity Guardrail" (Principle 9).
        Checks if a DailyLog (activity) is linked to a valid and active goal.
        
        「計画外活動の防衛」ロジック。
        日々の記録(DailyLog)が、有効な(ACTIVE)計画の目標(Goal)に紐づいているか検証する。
        """
        
        goal = IndividualSupportGoal.query.get(goal_id)
        if not goal:
            return False # そもそも目標が存在しない

        # 1. goal_id から SupportPlan を逆引き
        # 2. SupportPlan.plan_status == 'ACTIVE' であること
        # 3. SupportPlan.user_id == user_id であること
        
        plan = (
            SupportPlan.query
            .join(LongTermGoal, SupportPlan.id == LongTermGoal.plan_id)
            .join(ShortTermGoal, LongTermGoal.id == ShortTermGoal.long_term_goal_id)
            .join(IndividualSupportGoal, ShortTermGoal.id == IndividualSupportGoal.short_term_goal_id)
            .filter(IndividualSupportGoal.id == goal_id)
            .filter(SupportPlan.user_id == user_id)
            .filter(SupportPlan.plan_status == 'ACTIVE') # ★「成案」のみを許可
            .first()
        )
        
        # If a valid, active plan is found linked to this goal and user,
        # the activity is validated.
        return plan is not None