# app/models/plan.py

from app.extensions import db
from datetime import datetime
from sqlalchemy.orm import relationship
from .master import (
    StatusMaster, MeetingTypeMaster,
    ### ----------------------------------------------------
    ### 1. インポートの追加
    ### ----------------------------------------------------
    AssessmentItemMaster, AssessmentScoreMaster 
)

class SupportPlan(db.Model):
    __tablename__ = 'support_plans'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    sabikan_id = db.Column(db.Integer, db.ForeignKey('supporters.id'))
    status_id = db.Column(db.Integer, db.ForeignKey('status_master.id'))
    
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)

    user_consent_date = db.Column(db.DateTime) 
    main_goal = db.Column(db.Text)            
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    remarks = db.Column(db.Text)

    user = db.relationship('User', back_populates='support_plans')
    sabikan = db.relationship('Supporter', back_populates='plan_approvals', foreign_keys=[sabikan_id])
    status = db.relationship('StatusMaster', foreign_keys=[status_id])
    
    short_term_goals = db.relationship('ShortTermGoal', back_populates='support_plan')
    monitorings = db.relationship('Monitoring', back_populates='plan')
    meeting_minutes = db.relationship('MeetingMinute', back_populates='support_plan')

    ### ----------------------------------------------------
    ### 2. SystemLog への逆参照リレーションシップを追加
    ### ----------------------------------------------------
    system_logs = db.relationship('SystemLog', back_populates='support_plan', foreign_keys='SystemLog.support_plan_id')


class ShortTermGoal(db.Model):
    # (変更なし)
    __tablename__ = 'short_term_goals'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    support_plan_id = db.Column(db.Integer, db.ForeignKey('support_plans.id'), nullable=False)
    short_goal = db.Column(db.String(500), nullable=False)
    
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)

    support_plan = db.relationship('SupportPlan', back_populates='short_term_goals')
    specific_goals = db.relationship('SpecificGoal', back_populates='short_term_goal')

class SpecificGoal(db.Model):
    # (変更なし)
    __tablename__ = 'specific_goals'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    short_term_goal_id = db.Column(db.Integer, db.ForeignKey('short_term_goals.id'), nullable=False)
    task_name = db.Column(db.String(500), nullable=False) 
    
    priority = db.Column(db.Integer) 
    
    responsible_supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'))  
    template_id = db.Column(db.Integer, db.ForeignKey('service_templates.id'))
    is_custom_task = db.Column(db.Boolean, default=True) 

    short_term_goal = db.relationship('ShortTermGoal', back_populates='specific_goals')
    template = db.relationship('ServiceTemplate', back_populates='specific_goals')
    responsible_supporter = db.relationship(
        'Supporter',  
        back_populates='responsible_tasks',
        foreign_keys=[responsible_supporter_id]
    )
    daily_logs = db.relationship('DailyLog', back_populates='specific_goal')

class Monitoring(db.Model):
    # (変更なし)
    __tablename__ = 'monitorings'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('support_plans.id'), nullable=False)
    
    sabikan_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=False)
    monitoring_date = db.Column(db.Date, nullable=False)
    
    progress_summary = db.Column(db.Text) 
    next_plan = db.Column(db.Text)      

    plan = db.relationship('SupportPlan', back_populates='monitorings')
    sabikan = db.relationship('Supporter', back_populates='monitoring_approvals', foreign_keys=[sabikan_id])

class Assessment(db.Model):
    __tablename__ = 'assessments'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    sabikan_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=False)
    assessment_date = db.Column(db.Date, nullable=False)
    
    assessment_detail = db.Column(db.Text) 

    user = db.relationship('User', back_populates='assessments')
    sabikan = db.relationship('Supporter', back_populates='assessment_approvals', foreign_keys=[sabikan_id])

    ### ----------------------------------------------------
    ### 3. ReadinessAssessmentResult へのリレーションシップを追加
    ### ----------------------------------------------------
    results = db.relationship('ReadinessAssessmentResult', back_populates='assessment', lazy=True, cascade="all, delete-orphan")


class MeetingMinute(db.Model):
    # (変更なし)
    __tablename__ = 'meeting_minutes'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    support_plan_id = db.Column(db.Integer, db.ForeignKey('support_plans.id'))
    
    meeting_date = db.Column(db.Date, nullable=False)
    meeting_type_id = db.Column(db.Integer, db.ForeignKey('meeting_type_master.id'))
    
    attendees = db.Column(db.String(500)) 
    summary = db.Column(db.Text)
    
    user = db.relationship('User', back_populates='meeting_minutes')
    meeting_type = db.relationship('MeetingTypeMaster')
    support_plan = db.relationship('SupportPlan', back_populates='meeting_minutes')


### ----------------------------------------------------
### 4. 不足していた ReadinessAssessmentResult モデルを新規追加
### ----------------------------------------------------
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
    assessment_score = db.relationship('AssessmentScoreMaster')