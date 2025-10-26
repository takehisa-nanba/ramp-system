# app/models/master.py

from app.extensions import db
from sqlalchemy.orm import relationship

# --- マスターテーブル群 ---

class StatusMaster(db.Model):
    __tablename__ = 'status_master'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    # prospect, user, plan などの分類
    category = db.Column(db.String(50), nullable=False) 
    name = db.Column(db.String(50), nullable=False)
    
    # リレーションシップ（逆参照）
    # User.status_id, Prospect.status_id, SupportPlan.status_id から参照される

class ReferralSourceMaster(db.Model):
    __tablename__ = 'referral_source_master'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    
    # リレーションシップ（逆参照）
    # Prospect.referral_source_id から参照される

class RoleMaster(db.Model):
    __tablename__ = 'role_master'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    
    # リレーションシップ（逆参照）
    supporters = db.relationship('Supporter', back_populates='role') # Supporter.role_id から参照

class AttendanceStatusMaster(db.Model):
    __tablename__ = 'attendance_status_master'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False) # 通所, 欠席, 午前休, など
    
    # リレーションシップ（逆参照）
    daily_logs = db.relationship('DailyLog', back_populates='attendance_status') # DailyLog.attendance_status_id から参照

class ServiceLocationMaster(db.Model):
    __tablename__ = 'service_location_master'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    location_name = db.Column(db.String(100), nullable=False, unique=True)
    is_offsite = db.Column(db.Boolean, default=False) # 施設外支援フラグ
    
    # リレーションシップ（逆参照）
    daily_logs = db.relationship('DailyLog', back_populates='service_location') # DailyLog.location_id から参照

class PreparationActivityMaster(db.Model):
    __tablename__ = 'preparation_activity_master'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    activity_name = db.Column(db.String(150), nullable=False, unique=True)
    is_billable = db.Column(db.Boolean, nullable=False, default=False) # 加算対象フラグ
    
    # リレーションシップ（逆参照）
    daily_logs = db.relationship('DailyLog', back_populates='preparation_activity') # DailyLog.preparation_activity_id から参照

class EmploymentTypeMaster(db.Model):
    __tablename__ = 'employment_type_master'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

class WorkStyleMaster(db.Model):
    __tablename__ = 'work_style_master'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

class DisclosureTypeMaster(db.Model):
    __tablename__ = 'disclosure_type_master'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

class ContactCategoryMaster(db.Model):
    __tablename__ = 'contact_category_master'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

    # リレーションシップ (Contact からの逆参照)
    contacts = relationship('Contact', back_populates='category') 

class MeetingTypeMaster(db.Model):
    __tablename__ = 'meeting_type_master'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

class ServiceTemplate(db.Model):
    __tablename__ = 'service_templates'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    
    # リレーションシップ（逆参照）
    specific_goals = db.relationship('SpecificGoal', back_populates='template') # SpecificGoal.template_id から参照


# 本棚Y：行政機関マスタ (GovernmentOffice)
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
