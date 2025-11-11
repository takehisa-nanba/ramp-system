# backend/app/models/plan.py

from app.extensions import db
from datetime import datetime
from sqlalchemy.orm import relationship
from .master import StatusMaster, MeetingTypeMaster, AssessmentItemMaster, AssessmentScoreMaster, ServiceTemplate
# (plan.pyが他のモデルを参照しないように、core/masterからのインポートを修正)

# ----------------------------------------------------
# 1. SupportPlan (個別支援計画)
# ----------------------------------------------------
class SupportPlan(db.Model):
    __tablename__ = 'support_plans'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # 法令責任者（サビ管）
    sabikan_id = db.Column(db.Integer, db.ForeignKey('supporters.id'))
    status_id = db.Column(db.Integer, db.ForeignKey('status_master.id')) # Draft, Approvedなど
    
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)

    user_consent_date = db.Column(db.DateTime) # 利用者サイン完了日時
    main_goal = db.Column(db.Text)             # 長期目標
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    remarks = db.Column(db.Text)

    # リレーションシップ
    user = db.relationship('User', back_populates='support_plans')
    sabikan = db.relationship('Supporter', back_populates='plan_approvals', foreign_keys=[sabikan_id])
    status = db.relationship('StatusMaster', foreign_keys=[status_id])
    
    # 子要素
    short_term_goals = db.relationship('ShortTermGoal', back_populates='support_plan', cascade="all, delete-orphan")
    monitorings = db.relationship('Monitoring', back_populates='plan', cascade="all, delete-orphan")
    meeting_minutes = db.relationship('MeetingMinute', back_populates='support_plan')
    system_logs = db.relationship('SystemLog', back_populates='support_plan', foreign_keys='SystemLog.support_plan_id') # 監査ログ

# ----------------------------------------------------
# 2. ShortTermGoal (短期目標)
# ----------------------------------------------------
class ShortTermGoal(db.Model):
    __tablename__ = 'short_term_goals'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    support_plan_id = db.Column(db.Integer, db.ForeignKey('support_plans.id'), nullable=False)
    short_goal = db.Column(db.String(500), nullable=False) # 短期目標のテキスト
    
    # 期間を明確化
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)

    # リレーションシップ
    support_plan = db.relationship('SupportPlan', back_populates='short_term_goals')
    specific_goals = db.relationship('SpecificGoal', back_populates='short_term_goal', cascade="all, delete-orphan")

# ----------------------------------------------------
# 3. SpecificGoal (具体的タスク)
# ----------------------------------------------------
class SpecificGoal(db.Model):
    __tablename__ = 'specific_goals'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    short_term_goal_id = db.Column(db.Integer, db.ForeignKey('short_term_goals.id'), nullable=False)
    task_name = db.Column(db.String(500), nullable=False) # 具体的タスクのテキスト
    
    priority = db.Column(db.Integer) # 優先度
    
    # ユーザー
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # 担当職員（FK to Supporter）
    responsible_supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id')) 
    template_id = db.Column(db.Integer, db.ForeignKey('service_templates.id'))

    is_custom_task = db.Column(db.Boolean, default=True) # テンプレートからの派生ではない場合

    # リレーションシップ
    short_term_goal = db.relationship('ShortTermGoal', back_populates='specific_goals')
    template = db.relationship('ServiceTemplate', back_populates='specific_goals')
    responsible_supporter = db.relationship(
        'Supporter', 
        back_populates='responsible_tasks',
        foreign_keys=[responsible_supporter_id]
    )
    # 関連する日報記録
    daily_logs = db.relationship('DailyLog', back_populates='specific_goal')

# ----------------------------------------------------
# 4. Monitoring (モニタリング)
# ----------------------------------------------------
class Monitoring(db.Model):
    __tablename__ = 'monitorings'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('support_plans.id'), nullable=False)
    
    # サビ管責任者
    sabikan_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=False)
    monitoring_date = db.Column(db.Date, nullable=False)
    
    progress_summary = db.Column(db.Text) # 進捗サマリー
    next_plan = db.Column(db.Text)       # 次期計画への提案

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # リレーションシップ
    plan = db.relationship('SupportPlan', back_populates='monitorings')
    sabikan = db.relationship('Supporter', back_populates='monitoring_approvals', foreign_keys=[sabikan_id])
    user = db.relationship('User', back_populates='monitorings')

# ----------------------------------------------------
# 5. Assessment (アセスメント)
# ----------------------------------------------------
class Assessment(db.Model):
    __tablename__ = 'assessments'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # サビ管責任者
    sabikan_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=False)
    assessment_date = db.Column(db.Date, nullable=False)
    
    assessment_detail = db.Column(db.Text) # アセスメント記録本体

    # リレーションシップ
    user = db.relationship('User', back_populates='assessments')
    sabikan = db.relationship('Supporter', back_populates='assessment_approvals', foreign_keys=[sabikan_id])
    results = db.relationship('ReadinessAssessmentResult', back_populates='assessment', lazy=True, cascade="all, delete-orphan") # ★ 逆参照

# ----------------------------------------------------
# 6. MeetingMinute (議事録)
# ----------------------------------------------------
class MeetingMinute(db.Model):
    __tablename__ = 'meeting_minutes'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # どの支援計画に関連するか
    support_plan_id = db.Column(db.Integer, db.ForeignKey('support_plans.id'))
    
    meeting_date = db.Column(db.Date, nullable=False)
    meeting_type_id = db.Column(db.Integer, db.ForeignKey('meeting_type_master.id'))
    
    attendees = db.Column(db.String(500)) # 参加者リスト
    summary = db.Column(db.Text)
    
    # リレーションシップ
    user = db.relationship('User', back_populates='meeting_minutes')
    meeting_type = db.relationship('MeetingTypeMaster')
    support_plan = db.relationship('SupportPlan', back_populates='meeting_minutes')

# ----------------------------------------------------
# 7. ReadinessAssessmentResult (アセスメント結果)
# ----------------------------------------------------
class ReadinessAssessmentResult(db.Model):
    __tablename__ = 'readiness_assessment_results'
    id = db.Column(db.Integer, primary_key=True)
    
    # 親となるアセスメント
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessments.id'), nullable=False)
    
    # 参照するマスター
    item_id = db.Column(db.Integer, db.ForeignKey('assessment_item_master.id'), nullable=False) 
    score_id = db.Column(db.Integer, db.ForeignKey('assessment_score_master.id'))
    
    # 評価結果
    supporter_comment = db.Column(db.Text)

    # リレーションシップ
    assessment = db.relationship('Assessment', back_populates='results')
    assessment_item = db.relationship('AssessmentItemMaster', back_populates='assessment_results')
    assessment_score = db.relationship('AssessmentScoreMaster', back_populates='readiness_assessment_results')

# ----------------------------------------------------
# 8. PreEnrollmentLog (★ initial_support.py から移動 ★)
# 見学者・体験利用時の記録 (Userモデルに紐づく)
# ----------------------------------------------------
class PreEnrollmentLog(db.Model):
    __tablename__ = 'pre_enrollment_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # ★ 修正: prospect_id ではなく user_id に紐づく
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    contact_date = db.Column(db.DateTime, nullable=False)
    log_type = db.Column(db.String(50), nullable=False) # '見学', '体験', '初期アセスメント', '電話相談'
    supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=False)
    
    summary = db.Column(db.Text)
    initial_assessment_memo = db.Column(db.Text)

    # リレーションシップ
    user = db.relationship('User', back_populates='pre_enrollment_logs')
    supporter = db.relationship('Supporter', backref='pre_enrollment_logs')
    
    # 初期アセスメントスコア
    assessment_scores = db.relationship('PreEnrollmentAssessmentScore', back_populates='enrollment_log', lazy=True, cascade="all, delete-orphan")

# ----------------------------------------------------
# 9. PreEnrollmentAssessmentScore (★ initial_support.py から移動 ★)
# ----------------------------------------------------
class PreEnrollmentAssessmentScore(db.Model):
    __tablename__ = 'pre_enrollment_assessment_scores'
    
    id = db.Column(db.Integer, primary_key=True)
    log_id = db.Column(db.Integer, db.ForeignKey('pre_enrollment_logs.id'), nullable=False)
    
    # 評価項目マスタを参照
    item_id = db.Column(db.Integer, db.ForeignKey('assessment_item_master.id'), nullable=False) 
    
    score = db.Column(db.Integer) # 初期評価スコア (例: 1-5点)
    comment = db.Column(db.Text) # 職員の評価メモ

    # リレーションシップ
    enrollment_log = db.relationship('PreEnrollmentLog', back_populates='assessment_scores')
    assessment_item = db.relationship('AssessmentItemMaster', back_populates='pre_enrollment_assessment_scores')
