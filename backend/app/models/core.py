# backend/app/models/core.py

from app.extensions import db, bcrypt
from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy import UniqueConstraint
from .master import(
    RoleMaster, StatusMaster, AttendanceStatusMaster, ServiceLocationMaster,
    ### 'ReferralSourceMaster' を削除 (Prospectが移動したため)
    ContactCategoryMaster, DisabilityTypeMaster,
    PreparationActivityMaster ### 追加 (audit_log.py から master.py に移動したため)
)

# --- コアユーザーおよび活動記録テーブル ---

class Supporter(db.Model):
    # (変更なし)
    __tablename__ = 'supporters'
    id = db.Column(db.Integer, primary_key=True)
    last_name = db.Column(db.String(50), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name_kana = db.Column(db.String(50))
    first_name_kana = db.Column(db.String(50))
    
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(128), nullable=False)
    
    hire_date = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True)
    
    is_full_time = db.Column(db.Boolean, default=False, nullable=False)
    scheduled_work_hours = db.Column(db.Integer, default=40, nullable=False) 
    employment_type = db.Column(db.String(50), default='正社員', nullable=False)

    role_id = db.Column(db.Integer, db.ForeignKey('role_master.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) 
    remarks = db.Column(db.Text)

    role = db.relationship('RoleMaster', back_populates='supporters')
    primary_users = db.relationship(
        'User', 
        back_populates='primary_supporter',
        foreign_keys='User.primary_supporter_id'
    )
    plan_approvals = db.relationship(
        'SupportPlan',
        back_populates='sabikan',
        foreign_keys='SupportPlan.sabikan_id'
    )
    daily_logs = db.relationship('DailyLog', foreign_keys='[DailyLog.supporter_id]', back_populates='creator')
    approved_daily_logs = db.relationship('DailyLog', foreign_keys='[DailyLog.approved_by_id]', back_populates='approver')
    onsite_daily_logs = db.relationship('DailyLog', foreign_keys='[DailyLog.supporter_on_site_id]', back_populates='supporter_on_site')
    
    timecards = db.relationship('SupporterTimecard', back_populates='supporter')
    created_schedules = db.relationship('Schedule', back_populates='creator', foreign_keys='Schedule.creator_supporter_id')
    
    assessment_approvals = db.relationship('Assessment', back_populates='sabikan', foreign_keys='Assessment.sabikan_id')
    monitoring_approvals = db.relationship('Monitoring', back_populates='sabikan', foreign_keys='Monitoring.sabikan_id')
    responsible_tasks = db.relationship('SpecificGoal', back_populates='responsible_supporter', foreign_keys='SpecificGoal.responsible_supporter_id')
    
    ### (Supporterモデルに紐づくリレーションシップは元からあったので省略)
    ### sent_messages, received_messages, scheduled_participations, expense_claims, expenses_approved...

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

class User(db.Model):
    # (変更なし)
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    last_name = db.Column(db.String(50), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name_kana = db.Column(db.String(50))
    first_name_kana = db.Column(db.String(50))
    birth_date = db.Column(db.Date)
    gender = db.Column(db.String(10)) 
    
    postal_code = db.Column(db.String(10))
    address = db.Column(db.String(255))
    phone_number = db.Column(db.String(20))
    email = db.Column(db.String(120), unique=True)
    
    service_start_date = db.Column(db.Date) 
    service_end_date = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_archivable = db.Column(db.Boolean, default=False, nullable=False) 
    remote_service_allowed = db.Column(db.Boolean, default=False)
    plan_consultation_office = db.Column(db.String(100))
    
    is_currently_working = db.Column(db.Boolean, default=False, nullable=False)
    employment_start_date = db.Column(db.Date)
    employment_status = db.Column(db.String(50))
    
    disability_type_id = db.Column(db.Integer, db.ForeignKey('disability_type_master.id'))
    handbook_level = db.Column(db.String(20))
    is_handbook_certified = db.Column(db.Boolean, default=False)

    pin_hash = db.Column(db.String(128)) 
    primary_supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'))
    status_id = db.Column(db.Integer, db.ForeignKey('status_master.id'))
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) 
    remarks = db.Column(db.Text)

    status = db.relationship('StatusMaster') 
    disability_type = db.relationship('DisabilityTypeMaster')
    primary_supporter = db.relationship(
        'Supporter', 
        back_populates='primary_users',
        foreign_keys='User.primary_supporter_id'
    )
    
    attendance_plans = db.relationship('AttendancePlan', back_populates='user')
    daily_logs = db.relationship('DailyLog', back_populates='user')
    support_plans = db.relationship('SupportPlan', back_populates='user')
    assessments = db.relationship('Assessment', back_populates='user')
    meeting_minutes = db.relationship('MeetingMinute', back_populates='user')
    system_logs = db.relationship('SystemLog', back_populates='user', foreign_keys='SystemLog.user_id')
    contacts = relationship('Contact', back_populates='user')
    
    emergency_contacts = db.relationship('EmergencyContact', backref='user', lazy=True)
    medical_institutions = db.relationship('MedicalInstitution', backref='user', lazy=True)
    beneficiary_certificates = db.relationship('BeneficiaryCertificate', backref='user', lazy=True) 
    service_records = db.relationship('ServiceRecord', backref='user', lazy=True)
    external_records = db.relationship('ExternalSupportRecord', backref='user', lazy=True)
    attendance_records = db.relationship('AttendanceRecord', backref='user', lazy=True)
    retention_contracts = db.relationship('JobRetentionContract', back_populates='user', lazy=True)
    compliance_facts = db.relationship('ComplianceFact', back_populates='user', lazy=True)
    ### (Userモデルに紐づくリレーションシップは元からあったので省略)
    ### scheduled_participations...


### ----------------------------------------------------
### 2. Prospect (見込み客) モデルを削除
### ----------------------------------------------------
# class Prospect(db.Model):
#    ... (initial_support.py に定義を一本化するため、ここの定義はすべて削除)


class AttendancePlan(db.Model):
    # (変更なし)
    __tablename__ = 'attendance_plans'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    planned_date = db.Column(db.Date, nullable=False)
    planned_check_in = db.Column(db.String(5), nullable=False)
    planned_check_out = db.Column(db.String(5))
    is_recurring = db.Column(db.Boolean, default=False)
    remarks = db.Column(db.Text)

    user = db.relationship('User', back_populates='attendance_plans')
    
    __table_args__ = (UniqueConstraint('user_id', 'planned_date', name='uq_user_date'),)

class DailyLog(db.Model):
    __tablename__ = 'daily_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id')) 
    approved_by_id = db.Column(db.Integer, db.ForeignKey('supporters.id')) 
    supporter_on_site_id = db.Column(db.Integer, db.ForeignKey('supporters.id')) 
    
    activity_date = db.Column(db.Date, nullable=False)
    attendance_status_id = db.Column(db.Integer, db.ForeignKey('attendance_status_master.id'))
    service_location_id = db.Column(db.Integer, db.ForeignKey('service_location_master.id')) 
    preparation_activity_id = db.Column(db.Integer, db.ForeignKey('preparation_activity_master.id'))
    
    service_duration_min = db.Column(db.Integer)
    
    staff_check_in = db.Column(db.DateTime)
    staff_check_out = db.Column(db.DateTime)
    
    activity_summary = db.Column(db.Text) 
    user_voice = db.Column(db.Text) 
    supporter_insight = db.Column(db.Text) 
    
    check_in_time = db.Column(db.DateTime) 
    check_out_time = db.Column(db.DateTime) 
    
    specific_goal_id = db.Column(db.Integer, db.ForeignKey('specific_goals.id'))
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) 
    remarks = db.Column(db.Text)

    user = db.relationship('User', back_populates='daily_logs')
    creator = db.relationship('Supporter', foreign_keys=[supporter_id], back_populates='daily_logs')
    approver = db.relationship('Supporter', foreign_keys=[approved_by_id], back_populates='approved_daily_logs')
    supporter_on_site = db.relationship('Supporter', foreign_keys=[supporter_on_site_id], back_populates='onsite_daily_logs')
    attendance_status = db.relationship('AttendanceStatusMaster', back_populates='daily_logs')
    service_location = db.relationship('ServiceLocationMaster', back_populates='daily_logs')
    
    ### ----------------------------------------------------
    ### 3. リレーションシップの追加
    ### ----------------------------------------------------
    preparation_activity = db.relationship('PreparationActivityMaster', back_populates='daily_logs')
    
    specific_goal = db.relationship('SpecificGoal', back_populates='daily_logs')

class Contact(db.Model):
    # (変更なし)
    __tablename__ = 'contacts'
    id = db.Column(db.Integer, primary_key=True)
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    contact_category_id = db.Column(db.Integer, db.ForeignKey('contact_category_master.id'), nullable=False)
    government_office_id = db.Column(db.Integer, db.ForeignKey('government_offices.id')) 

    organization_name = db.Column(db.String(150), nullable=False)
    contact_person = db.Column(db.String(100))
    phone_number = db.Column(db.String(20))
    email = db.Column(db.String(120))
    remarks = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = relationship('User', back_populates='contacts') 
    category = relationship('ContactCategoryMaster', back_populates='contacts') 
    government_office = relationship('GovernmentOffice', back_populates='contacts')