from ...extensions import db
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, Text, func

# ====================================================================
# 1. SupportPlan (個別支援計画 - 親)
# ====================================================================
class SupportPlan(db.Model):
    """
    個別支援計画（親モデル）。
    ワークフローの状態(plan_status)とサビ管の承認(sabikan_approved_by_id)で
    法令遵守(原理1)と監査証跡を管理する。
    「原案」と「成案」は、based_on_plan_idで紐づく「2つで1つ」の構造。
    """
    __tablename__ = 'support_plans'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    plan_version = Column(Integer, nullable=False, default=1)
    
    # ワークフローの状態 (DRAFT, PENDING_CONFERENCE, PENDING_CONSENT, ACTIVE, ARCHIVED_DRAFT)
    plan_status = Column(String(30), nullable=False, default='DRAFT')
    
    # --- 監査証跡（原理1） ---
    # 計画の根拠となったアセスメント/モニタリングID (汎用)
    # assessment_id = Column(Integer, ForeignKey('assessments.id')) 
    # monitoring_id = Column(Integer, ForeignKey('monitoring_reports.id'))
    
    # サビ管の最終承認（必須）
    sabikan_approved_by_id = Column(Integer, ForeignKey('supporters.id'))
    sabikan_approved_at = Column(DateTime)
    
    # ★ NEW: 原案と成案の紐づけ（原理1）
    # 「成案」が、どの「原案」に基づいているかを示す
    based_on_plan_id = Column(Integer, ForeignKey('support_plans.id'), nullable=True)
    
    created_at = Column(DateTime, default=func.now())
    
    # --- リレーションシップ ---
    user = relationship('User', back_populates='support_plans')
    
    # ★ NEW: 原案/成案の自己参照リレーション
    # 「成案」から「原案」を参照する (例: plan.draft_plan)
    draft_plan = relationship('SupportPlan', remote_side=[id], foreign_keys=[based_on_plan_id])
    # 「原案」から「成案」を参照する（逆参照） (例: draft.finalized_plan)
    finalized_plan = relationship('SupportPlan', back_populates='draft_plan', remote_side=[based_on_plan_id])

    long_term_goals = relationship('LongTermGoal', back_populates='plan', cascade="all, delete-orphan")
    conferences = relationship('SupportConferenceLog', back_populates='plan', lazy='dynamic', cascade="all, delete-orphan")
    consent_log = relationship('DocumentConsentLog', back_populates='plan', lazy='dynamic') # 計画への同意

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
    
    plan = relationship('SupportPlan', back_populates='long_term_goals')
    short_term_goals = relationship('ShortTermGoal', back_populates='long_term_goal', cascade="all, delete-orphan")

# ====================================================================
# 3. ShortTermGoal (短期目標 / 見直し期限 / 売上予測)
# ====================================================================
class ShortTermGoal(db.Model):
    """短期目標（PDCAサイクルの見直し単位 / 売上予測の土台）"""
    __tablename__ = 'short_term_goals'
    id = Column(Integer, primary_key=True)
    long_term_goal_id = Column(Integer, ForeignKey('long_term_goals.id'), nullable=False, index=True)
    
    description = Column(Text, nullable=False) # 短期目標全体の説明
    
    # --- 期間と見直し（原理1, 2） ---
    target_period_start = Column(Date)
    target_period_end = Column(Date)
    
    # ★ 次回見直し予定日 (減算リスク回避の核)
    next_review_date = Column(Date) 
    
    long_term_goal = relationship('LongTermGoal', back_populates='short_term_goals')
    individual_goals = relationship('IndividualSupportGoal', back_populates='short_term_goal', cascade="all, delete-orphan")

# ====================================================================
# 4. IndividualSupportGoal (支援の最小単位 / ガードレール)
# ====================================================================
class IndividualSupportGoal(db.Model):
    """
    具体的目標、本人の取組、支援の内容の3点セット（支援の最小単位）。
    DailyLogはこのIDに紐づき、計画外活動（ムダ）を排除する。
    """
    __tablename__ = 'individual_support_goals'
    id = Column(Integer, primary_key=True)
    short_term_goal_id = Column(Integer, ForeignKey('short_term_goals.id'), nullable=False, index=True)
    
    # --- 3点セット（原理2） ---
    concrete_goal = Column(Text, nullable=False) # 具体的目標
    user_commitment = Column(Text, nullable=False) # 本人の取組 (利用者ダッシュボードへ反映)
    support_actions = Column(Text, nullable=False) # 支援の内容
    
    # --- 請求と算定のガードレール（原理3） ---
    # (例: 'HOME_SUPPORT', 'OUTSIDE_WORK', 'GROUP_TRAINING')
    service_type = Column(String(50), nullable=False) 
    
    # 在宅訓練を施設内訓練とみなすフラグ
    is_facility_in_deemed = Column(Boolean, default=False, nullable=False)
    
    # 就労準備加算対象の活動か
    is_work_preparation_positioning = Column(Boolean, default=False, nullable=False)
    
    short_term_goal = relationship('ShortTermGoal', back_populates='individual_goals')

# ====================================================================
# 5. SupportConferenceLog (支援会議ログ / 議事録)
# ====================================================================
class SupportConferenceLog(db.Model):
    """
    支援会議ログ（プロセス証跡）。
    計画作成の必須プロセス（原案→成案）を担保する。
    """
    __tablename__ = 'support_conference_logs'
    
    id = Column(Integer, primary_key=True)
    plan_id = Column(Integer, ForeignKey('support_plans.id'), nullable=False, index=True)
    
    conference_date = Column(DateTime, nullable=False, default=func.now())
    participant_user_flag = Column(Boolean, default=False) # 本人参加フラグ
    # participant_supporter_ids (JSON or Link Table)
    
    # --- 議事録（原理4） ---
    minutes_content = Column(Text) # 議事録のテキスト内容（システムがPDF化）
    
    # --- サービス担当者会議加算（原理3） ---
    is_charge_meeting = Column(Boolean, default=False) # 加算対象会議フラグ
    external_participant_id = Column(Integer, ForeignKey('organizations.id')) # 外部専門職
    external_participant_signature_url = Column(String(500)) # 外部署名URL (OTLまたはスキャン)
    
    plan = relationship('SupportPlan', back_populates='conferences')

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
    request_reason = Column(Text, nullable=False) # 申請理由 (NULL禁止)
    
    # PENDING, APPROVED, REJECTED
    request_status = Column(String(20), default='PENDING') 
    
    requested_at = Column(DateTime, default=func.now())
    approver_id = Column(Integer, ForeignKey('supporters.id')) # 承認したサビ管
    
    user = relationship('User')
    plan = relationship('SupportPlan')
    approver = relationship('Supporter')

# ====================================================================
# 7. AssessorType & GoalAssessment (多角評価)
# ====================================================================
class AssessorType(db.Model):
    """評価主体（誰が評価したか）のマスタテーブル"""
    __tablename__ = 'assessor_types'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False) # 例: 'サービス管理責任者', '利用者本人', '支援員'
    
    goal_assessments = relationship('GoalAssessment', back_populates='assessor_type', lazy='dynamic')

class GoalAssessment(db.Model):
    """目標（長期、短期、個別）に対する多角評価ログ"""
    __tablename__ = 'goal_assessments'
    
    id = Column(Integer, primary_key=True)
    assessor_type_id = Column(Integer, ForeignKey('assessor_types.id'), nullable=False)
    supporter_id = Column(Integer, ForeignKey('supporters.id')) # 評価した職員
    
    # どの目標に対する評価か（汎用リレーション）
    goal_type = Column(String(50), nullable=False) # 'LONG', 'SHORT', 'INDIVIDUAL'
    goal_id = Column(Integer, nullable=False, index=True) 
    
    assessment_date = Column(Date, nullable=False)
    score = Column(Integer) # 例: 5段階評価
    comment = Column(Text) # 評価コメント
    
    assessor_type = relationship('AssessorType', back_populates='goal_assessments')
    supporter = relationship('Supporter', foreign_keys=[supporter_id])