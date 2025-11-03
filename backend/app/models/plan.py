# app/models/plan.py

from app.extensions import db
from datetime import datetime
from sqlalchemy.orm import relationship
from .master import StatusMaster, MeetingTypeMaster

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

    # リレーションシップ（堅牢性対応）
    user = db.relationship('User', back_populates='support_plans')
    sabikan = db.relationship('Supporter', back_populates='plan_approvals', foreign_keys=[sabikan_id])
    status = db.relationship('StatusMaster', foreign_keys=[status_id])
    
    # 子要素（双方向リレーションシップの追加）
    short_term_goals = db.relationship('ShortTermGoal', back_populates='support_plan')
    monitorings = db.relationship('Monitoring', back_populates='plan')
    meeting_minutes = db.relationship('MeetingMinute', back_populates='support_plan') # MeetingMinuteとの連携

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
    specific_goals = db.relationship('SpecificGoal', back_populates='short_term_goal')

class SpecificGoal(db.Model):
    __tablename__ = 'specific_goals'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    short_term_goal_id = db.Column(db.Integer, db.ForeignKey('short_term_goals.id'), nullable=False)
    task_name = db.Column(db.String(500), nullable=False) # 具体的タスクのテキスト
    
    priority = db.Column(db.Integer) # 優先度
    
    # 担当職員（FK to Supporter）
    responsible_supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id')) 
    template_id = db.Column(db.Integer, db.ForeignKey('service_templates.id'))

    is_custom_task = db.Column(db.Boolean, default=True) # テンプレートからの派生ではない場合

    # リレーションシップ（堅牢性対応）
    short_term_goal = db.relationship('ShortTermGoal', back_populates='specific_goals')
    template = db.relationship('ServiceTemplate', back_populates='specific_goals')
    responsible_supporter = db.relationship(
        'Supporter', 
        back_populates='responsible_tasks',
        foreign_keys=[responsible_supporter_id]
    )
    # 関連する日報記録
    daily_logs = db.relationship('DailyLog', back_populates='specific_goal')

class Monitoring(db.Model):
    __tablename__ = 'monitorings'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('support_plans.id'), nullable=False)
    
    # サビ管責任者
    sabikan_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=False)
    monitoring_date = db.Column(db.Date, nullable=False)
    
    progress_summary = db.Column(db.Text) # 進捗サマリー
    next_plan = db.Column(db.Text)        # 次期計画への提案

    # リレーションシップ（堅牢性対応）
    plan = db.relationship('SupportPlan', back_populates='monitorings')
    sabikan = db.relationship('Supporter', back_populates='monitoring_approvals', foreign_keys=[sabikan_id])

class Assessment(db.Model):
    __tablename__ = 'assessments'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # サビ管責任者
    sabikan_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=False)
    assessment_date = db.Column(db.Date, nullable=False)
    
    assessment_detail = db.Column(db.Text) # アセスメント記録本体

    # リレーションシップ（堅牢性対応）
    user = db.relationship('User', back_populates='assessments')
    sabikan = db.relationship('Supporter', back_populates='assessment_approvals', foreign_keys=[sabikan_id])

class MeetingMinute(db.Model):
    __tablename__ = 'meeting_minutes'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # ★ 追加: どの支援計画に関連するか
    support_plan_id = db.Column(db.Integer, db.ForeignKey('support_plans.id'))
    
    meeting_date = db.Column(db.Date, nullable=False)
    meeting_type_id = db.Column(db.Integer, db.ForeignKey('meeting_type_master.id'))
    
    attendees = db.Column(db.String(500)) # 参加者リスト（カンマ区切りなど）
    summary = db.Column(db.Text)
    
    # リレーションシップ（堅牢性対応）
    user = db.relationship('User', back_populates='meeting_minutes')
    meeting_type = db.relationship('MeetingTypeMaster')
    support_plan = db.relationship('SupportPlan', back_populates='meeting_minutes')

