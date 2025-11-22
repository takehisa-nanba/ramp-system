# backend/app/models/support/support_plan.py
from backend.app.extensions import db
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, Text, func

# ====================================================================
# 1. SupportPlan (個別支援計画 - 親)
# ====================================================================
class SupportPlan(db.Model):
    """
    個別支援計画（親モデル）。
    ワークフローの状態(plan_status)とサビ管の承認(sabikan_approved_by_id)で
    法令遵守(原理1)と監査証跡を管理する。
    """
    __tablename__ = 'support_plans'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    plan_version = Column(Integer, nullable=False, default=1)
    
    # ワークフローの状態 (DRAFT, PENDING_CONFERENCE, PENDING_CONSENT, ACTIVE, ARCHIVED_DRAFT, ARCHIVED)
    plan_status = Column(String(30), nullable=False, default='DRAFT')
    
    # --- 監査証跡（原理1） ---
    # サビ管の最終承認（必須）
    sabikan_approved_by_id = Column(Integer, ForeignKey('supporters.id'))
    sabikan_approved_at = Column(DateTime)
    
    # 原案と成案の紐づけ（2つで1つ）
    based_on_plan_id = Column(Integer, ForeignKey('support_plans.id'), nullable=True)
    
    # ★ 修正: テキストコピーをやめ、根拠となる「方針ID」を紐づける (ムダの排除)
    # これにより、計画作成当時の「意向」や「方針」を正確かつムダなく参照できる
    holistic_support_policy_id = Column(Integer, ForeignKey('holistic_support_policies.id'))
    
    created_at = Column(DateTime, default=func.now())
    
    # --- リレーションシップ ---
    user = db.relationship('User', back_populates='support_plans')
    
    # 根拠となる方針へのリレーション
    holistic_policy = db.relationship('HolisticSupportPolicy')
    
    # 自己参照リレーション
    draft_plan = db.relationship('SupportPlan', remote_side=[id], foreign_keys=[based_on_plan_id])
    finalized_plan = db.relationship('SupportPlan', back_populates='draft_plan', remote_side=[based_on_plan_id])

    long_term_goals = db.relationship('LongTermGoal', back_populates='plan', cascade="all, delete-orphan")
    conferences = db.relationship('SupportConferenceLog', back_populates='plan', lazy='dynamic', cascade="all, delete-orphan")
    consent_log = db.relationship(
        'DocumentConsentLog',
        primaryjoin="and_(DocumentConsentLog.document_id == SupportPlan.id, DocumentConsentLog.document_type == 'SUPPORT_PLAN')",
        foreign_keys="DocumentConsentLog.document_id",
        back_populates='plan',
        lazy='dynamic'
    )    
    # 見直し申請からの逆参照
    review_requests = db.relationship('PlanReviewRequest', back_populates='plan', lazy='dynamic')

# ====================================================================
# 2. LongTermGoal (長期目標)
# ====================================================================
class LongTermGoal(db.Model):
    """長期目標"""
    __tablename__ = 'long_term_goals'
    id = Column(Integer, primary_key=True)
    plan_id = Column(Integer, ForeignKey('support_plans.id'), nullable=False, index=True)
    
    description = Column(Text, nullable=False)
    target_period_start = Column(Date)
    target_period_end = Column(Date)
    
    plan = db.relationship('SupportPlan', back_populates='long_term_goals')
    short_term_goals = db.relationship('ShortTermGoal', back_populates='long_term_goal', cascade="all, delete-orphan")

# ====================================================================
# 3. ShortTermGoal (短期目標 / 見直し期限)
# ====================================================================
class ShortTermGoal(db.Model):
    """短期目標（PDCAサイクルの見直し単位）"""
    __tablename__ = 'short_term_goals'
    id = Column(Integer, primary_key=True)
    long_term_goal_id = Column(Integer, ForeignKey('long_term_goals.id'), nullable=False, index=True)
    
    description = Column(Text, nullable=False)
    
    # --- 期間と見直し（原理1, 2） ---
    target_period_start = Column(Date)
    target_period_end = Column(Date)
    
    # 次回見直し予定日 (減算リスク回避の核)
    next_review_date = Column(Date) 
    
    long_term_goal = db.relationship('LongTermGoal', back_populates='short_term_goals')
    individual_goals = db.relationship('IndividualSupportGoal', back_populates='short_term_goal', cascade="all, delete-orphan")

# ====================================================================
# 4. IndividualSupportGoal (支援の最小単位 / ガードレール)
# ====================================================================
class IndividualSupportGoal(db.Model):
    """
    具体的目標、本人の取組、支援の内容の3点セット。
    DailyLogはこのIDに紐づき、計画外活動（ムダ）を排除する。
    """
    __tablename__ = 'individual_support_goals'
    id = Column(Integer, primary_key=True)
    short_term_goal_id = Column(Integer, ForeignKey('short_term_goals.id'), nullable=False, index=True)
    
    # --- 3点セット（原理2） ---
    concrete_goal = Column(Text, nullable=False) # 具体的目標
    user_commitment = Column(Text, nullable=False) # 本人の取組
    support_actions = Column(Text, nullable=False) # 支援の内容
    
    # --- 請求と算定のガードレール（原理3） ---
    # (例: 'HOME_SUPPORT', 'OUTSIDE_WORK', 'GROUP_TRAINING')
    service_type = Column(String(50), nullable=False) 
    
    # 在宅訓練を施設内訓練とみなすフラグ
    is_facility_in_deemed = Column(Boolean, default=False, nullable=False)
    
    # 就労準備加算対象の活動か
    is_work_preparation_positioning = Column(Boolean, default=False, nullable=False)
    
    short_term_goal = db.relationship('ShortTermGoal', back_populates='individual_goals')

# ====================================================================
# 5. SupportConferenceLog (支援会議ログ / 議事録)
# ====================================================================
class SupportConferenceLog(db.Model):
    """
    支援会議ログ（プロセス証跡）。
    """
    __tablename__ = 'support_conference_logs'
    
    id = Column(Integer, primary_key=True)
    plan_id = Column(Integer, ForeignKey('support_plans.id'), nullable=False, index=True)
    
    conference_date = Column(DateTime, nullable=False, default=func.now())
    participant_user_flag = Column(Boolean, default=False) # 本人参加フラグ
    
    # 本人不在の「やむを得ない理由」（原理1）
    reason_for_user_absence = Column(Text, nullable=True)
    
    # --- 議事録（原理4） ---
    minutes_content = Column(Text) 
    
    # --- サービス担当者会議加算（原理3） ---
    is_charge_meeting = Column(Boolean, default=False) 
    external_participant_id = Column(Integer, ForeignKey('organizations.id')) 
    external_participant_signature_url = Column(String(500)) 
    
    plan = db.relationship('SupportPlan', back_populates='conferences')

# ====================================================================
# 6. PlanReviewRequest (計画見直し申請)
# ====================================================================
class PlanReviewRequest(db.Model):
    """計画見直し申請（現場からのフィードバックループ）"""
    __tablename__ = 'plan_review_requests'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    support_plan_id = Column(Integer, ForeignKey('support_plans.id'), nullable=False, index=True)
    
    # 'USER' or 'STAFF'
    request_originator_type = Column(String(20), nullable=False) 
    request_reason = Column(Text, nullable=False) 
    
    request_status = Column(String(20), default='PENDING') 
    
    requested_at = Column(DateTime, default=func.now())
    approver_id = Column(Integer, ForeignKey('supporters.id')) 
    
    user = db.relationship('User')
    plan = db.relationship('SupportPlan', back_populates='review_requests')
    approver = db.relationship('Supporter')

# ====================================================================
# 7. AssessorType & GoalAssessment (多角評価)
# ====================================================================
class AssessorType(db.Model):
    """評価主体（誰が評価したか）のマスタテーブル"""
    __tablename__ = 'assessor_types'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False) # 例: 'サービス管理責任者', '利用者本人', '支援員'
    
    goal_assessments = db.relationship('GoalAssessment', back_populates='assessor_type', lazy='dynamic')

class GoalAssessment(db.Model):
    """目標（長期、短期、個別）に対する多角評価ログ"""
    __tablename__ = 'goal_assessments'
    
    id = Column(Integer, primary_key=True)
    assessor_type_id = Column(Integer, ForeignKey('assessor_types.id'), nullable=False)
    supporter_id = Column(Integer, ForeignKey('supporters.id')) 
    
    # どの目標に対する評価か（汎用リレーション）
    goal_type = Column(String(50), nullable=False) # 'LONG', 'SHORT', 'INDIVIDUAL'
    goal_id = Column(Integer, nullable=False, index=True) 
    
    assessment_date = Column(Date, nullable=False)
    # 評価結果（定性的評価を重視）
    comment = Column(Text) 
    
    assessor_type = db.relationship('AssessorType', back_populates='goal_assessments')
    supporter = db.relationship('Supporter', foreign_keys=[supporter_id])