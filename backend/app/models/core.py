# backend/app/models/core.py

from app.extensions import db, bcrypt
from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy import UniqueConstraint
from .master import(
    RoleMaster, StatusMaster, AttendanceStatusMaster, ServiceLocationMaster,
    ContactCategoryMaster, DisabilityTypeMaster, PreparationActivityMaster,
    GovernmentOffice # Contactモデルが参照するためインポート
)
from .plan import SpecificGoal # DailyLogモデルが参照するためインポート

# --- コアユーザーおよび活動記録テーブル ---

class Supporter(db.Model):
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
    
    # 人事/常勤換算計算のための拡張
    is_full_time = db.Column(db.Boolean, default=False, nullable=False)
    scheduled_work_hours = db.Column(db.Integer, default=40, nullable=False) # 週の所定労働時間（時間）
    employment_type = db.Column(db.String(50), default='正社員', nullable=False)

    role_id = db.Column(db.Integer, db.ForeignKey('role_master.id'), nullable=False)
    
    # ★ 新規追加: 職員個人の印影画像URL
    seal_image_url = db.Column(db.String(500), nullable=True)
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) 
    remarks = db.Column(db.Text)

    # --- リレーションシップ ---
    role = db.relationship('RoleMaster', back_populates='supporters')
    
    # Userへのリレーション
    primary_users = db.relationship(
        'User', 
        back_populates='primary_supporter',
        foreign_keys='User.primary_supporter_id'
    )
    
    # Planへのリレーション (外部キー定義は各モデル側にある)
    # (Planモデル側で back_populates が定義されていれば、ここは不要な場合もある)
    plan_approvals = db.relationship('SupportPlan', back_populates='sabikan', foreign_keys='SupportPlan.sabikan_id')
    assessment_approvals = db.relationship('Assessment', back_populates='sabikan', foreign_keys='Assessment.sabikan_id')
    monitoring_approvals = db.relationship('Monitoring', back_populates='sabikan', foreign_keys='Monitoring.sabikan_id')
    responsible_tasks = db.relationship('SpecificGoal', back_populates='responsible_supporter', foreign_keys='SpecificGoal.responsible_supporter_id')

    # 記録系へのリレーション
    daily_logs = db.relationship('DailyLog', foreign_keys='[DailyLog.supporter_id]', back_populates='creator')
    approved_daily_logs = db.relationship('DailyLog', foreign_keys='[DailyLog.approved_by_id]', back_populates='approver')
    onsite_daily_logs = db.relationship('DailyLog', foreign_keys='[DailyLog.supporter_on_site_id]', back_populates='supporter_on_site')
    timecards = db.relationship('SupporterTimecard', back_populates='supporter')
    
    # Scheduleへのリレーション
    created_schedules = db.relationship('Schedule', back_populates='creator_supporter', foreign_keys='Schedule.creator_supporter_id')
    scheduled_participations = db.relationship('ScheduleParticipant', back_populates='supporter')

    # ★ 修正: Communication (チャット) へのリレーション
    sent_support_messages = db.relationship('ChatMessage', back_populates='sender_supporter', foreign_keys='ChatMessage.sender_supporter_id')
    staff_channel_participations = db.relationship('StaffChannelParticipant', back_populates='supporter')
    sent_staff_messages = db.relationship('StaffChannelMessage', back_populates='sender', foreign_keys='StaffChannelMessage.sender_id')


    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    last_name = db.Column(db.String(50), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name_kana = db.Column(db.String(50))
    first_name_kana = db.Column(db.String(50))
    birth_date = db.Column(db.Date)
    gender = db.Column(db.String(10)) 
    
    # 住所・連絡先
    postal_code = db.Column(db.String(10))
    address = db.Column(db.String(255))
    phone_number = db.Column(db.String(20))
    
    # ★ 修正: nullable=True に変更 (LINE登録/見学者対応)
    email = db.Column(db.String(120), unique=True, nullable=True)
    
    # ★ 新規追加: 印影画像URL
    seal_image_url = db.Column(db.String(500), nullable=True)
    
    # ★ 新規追加: LINE ID (OAuth用)
    line_id = db.Column(db.String(255), unique=True, nullable=True, index=True)

    # サービス・契約状況
    service_start_date = db.Column(db.Date) 
    service_end_date = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_archivable = db.Column(db.Boolean, default=False, nullable=False) # アーカイブ移行トリガー
    remote_service_allowed = db.Column(db.Boolean, default=False, nullable=False)
    plan_consultation_office = db.Column(db.String(100))
    
    # 就職・定着支援
    is_currently_working = db.Column(db.Boolean, default=False, nullable=False)
    employment_start_date = db.Column(db.Date)
    employment_status = db.Column(db.String(50))
    
    # 障害情報
    disability_type_id = db.Column(db.Integer, db.ForeignKey('disability_type_master.id'))
    handbook_level = db.Column(db.String(20))
    is_handbook_certified = db.Column(db.Boolean, default=False, nullable=False)

    pin_hash = db.Column(db.String(128)) 
    primary_supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'))
    
    # ★ 修正: status_id は NULL を許可しない (必ず'新規問合せ'などが入る)
    status_id = db.Column(db.Integer, db.ForeignKey('status_master.id'), nullable=False)
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) 
    remarks = db.Column(db.Text)

    # --- リレーションシップ ---
    status = db.relationship('StatusMaster', foreign_keys=[status_id]) 
    disability_type = db.relationship('DisabilityTypeMaster')
    primary_supporter = db.relationship(
        'Supporter', 
        back_populates='primary_users',
        foreign_keys=[primary_supporter_id]
    )
    
    # 記録系
    attendance_plans = db.relationship('AttendancePlan', back_populates='user')
    daily_logs = db.relationship('DailyLog', back_populates='user')
    service_records = db.relationship('ServiceRecord', backref='user', lazy=True)
    attendance_records = db.relationship('AttendanceRecord', back_populates='user', lazy=True)

    # 計画系
    support_plans = db.relationship('SupportPlan', back_populates='user')
    assessments = db.relationship('Assessment', back_populates='user')
    meeting_minutes = db.relationship('MeetingMinute', back_populates='user')
    
    # 監査・その他
    system_logs = db.relationship('SystemLog', back_populates='user', foreign_keys='SystemLog.user_id')
    contacts = relationship('Contact', back_populates='user')
    
    # 関連情報
    emergency_contacts = db.relationship('EmergencyContact', backref='user', lazy=True)
    medical_institutions = db.relationship('MedicalInstitution', backref='user', lazy=True)
    beneficiary_certificates = db.relationship('BeneficiaryCertificate', backref='user', lazy=True) 
    
    # 定着支援
    retention_contracts = db.relationship('JobRetentionContract', back_populates='user', lazy=True)
    
    # コンプライアンス
    compliance_facts = db.relationship('ComplianceFact', back_populates='user', lazy=True)
    
    # Schedule
    scheduled_participations = db.relationship('ScheduleParticipant', back_populates='user')

    # ★ 修正: Communication (チャット)
    support_threads = db.relationship('SupportThread', back_populates='user', lazy=True)
    sent_messages = db.relationship('ChatMessage', back_populates='sender_user', foreign_keys='ChatMessage.sender_user_id')
    
    # ★ 新規追加: 見学者時代の記録 (Prospectから移動)
    pre_enrollment_logs = db.relationship('PreEnrollmentLog', back_populates='user', lazy=True)


# --- (Prospect モデルは削除) ---


class AttendancePlan(db.Model):
    __tablename__ = 'attendance_plans'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    planned_date = db.Column(db.Date, nullable=False)
    planned_check_in = db.Column(db.String(5), nullable=False)
    planned_check_out = db.Column(db.String(5), nullable=True)
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
    
    # リレーションシップ
    user = db.relationship('User', back_populates='daily_logs')
    creator = db.relationship('Supporter', foreign_keys=[supporter_id], back_populates='daily_logs')
    approver = db.relationship('Supporter', foreign_keys=[approved_by_id], back_populates='approved_daily_logs')
    supporter_on_site = db.relationship('Supporter', foreign_keys=[supporter_on_site_id], back_populates='onsite_daily_logs')
    attendance_status = db.relationship('AttendanceStatusMaster', back_populates='daily_logs')
    service_location = db.relationship('ServiceLocationMaster', back_populates='daily_logs')
    preparation_activity = db.relationship('PreparationActivityMaster', back_populates='daily_logs')
    specific_goal = db.relationship('SpecificGoal', back_populates='daily_logs')

class Contact(db.Model):
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
    
    # リレーションシップ
    user = relationship('User', back_populates='contacts')
    category = relationship('ContactCategoryMaster', back_populates='contacts')
    government_office = relationship('GovernmentOffice', back_populates='contacts')
    