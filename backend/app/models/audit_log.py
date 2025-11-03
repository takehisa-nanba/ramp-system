# app/models/audit_log.py

from app.extensions import db
from datetime import datetime
from sqlalchemy.orm import relationship

class SystemLog(db.Model):
    __tablename__ = 'system_logs'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    
    action = db.Column(db.String(100), nullable=False) # 例: 'plan_consent', 'user_login'
    supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=False)
    
    # UserやSupportPlanへの参照をNullableで持つ
    user_id = db.Column(db.Integer, db.ForeignKey('users.id')) 
    support_plan_id = db.Column(db.Integer, db.ForeignKey('support_plans.id'))
    
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # リレーションシップ
    supporter = db.relationship('Supporter')
    user = db.relationship('User', back_populates='system_logs')
    support_plan = db.relationship('SupportPlan')

class GovernmentOffice(db.Model):
    __tablename__ = 'government_offices'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    office_name = db.Column(db.String(100), nullable=False, unique=True)
    office_type = db.Column(db.String(50), nullable=False) # 例: '市区町村', '県', 'ハローワーク'
    address = db.Column(db.String(255))
    phone_number = db.Column(db.String(20))
    email = db.Column(db.String(120))
    remarks = db.Column(db.Text)
    
    # リレーションシップ (Contact からの逆参照)
    contacts = relationship('Contact', back_populates='government_office')

class ServiceTemplate(db.Model):
    __tablename__ = 'service_templates'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    
    # リレーションシップ（逆参照）
    specific_goals = db.relationship('SpecificGoal', back_populates='template') # SpecificGoal.template_id から参照

class PreparationActivityMaster(db.Model):
    __tablename__ = 'preparation_activity_master'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    activity_name = db.Column(db.String(150), nullable=False, unique=True)
    is_billable = db.Column(db.Boolean, nullable=False, default=False) # 加算対象フラグ
    
    # リレーションシップ（逆参照）
    daily_logs = db.relationship('DailyLog', back_populates='preparation_activity') # DailyLog.preparation_activity_id から参照

