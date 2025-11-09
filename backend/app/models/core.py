# backend/app/models/core.py

from app.extensions import db, bcrypt
from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy import UniqueConstraint, CheckConstraint, ForeignKey # ★ 追加
from .master import(
    RoleMaster, StatusMaster, AttendanceStatusMaster, ServiceLocationMaster,
    ContactCategoryMaster, DisabilityTypeMaster, PreparationActivityMaster,
    GovernmentOffice # Contactモデルが参照するためインポート
)
# from .plan import SpecificGoal  # DailyLogが参照するが、Planのインポート後に解決

# --- 1. Supporter (職員) ---
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
    
    # 人事/常勤換算
    is_full_time = db.Column(db.Boolean, default=False, nullable=False)
    scheduled_work_hours = db.Column(db.Integer, default=40, nullable=False)
    employment_type = db.Column(db.String(50), default='正社員', nullable=False)

    # 組織ロール: 所属事業所 (ForeignKey)
    office_id = db.Column(db.Integer, db.ForeignKey('office_settings.id'), nullable=True) 
    
    # システム責任: PINハッシュと印影
    pin_hash = db.Column(db.String(128), nullable=True) # ★ 責任承認用PIN
    seal_image_url = db.Column(db.String(500), nullable=True) # ★ 職員個人の印影
    
    # システムロール（レガシー互換性のため残す。JobTitleに移行すべき）
    role_id = db.Column(db.Integer, db.ForeignKey('role_master.id'), nullable=False)
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) 
    remarks = db.Column(db.Text)

    # --- リレーションシップ ---
    role = db.relationship('RoleMaster', back_populates='supporters')
    office = db.relationship('OfficeSetting', foreign_keys=[office_id], back_populates='staff_members') # 組織ロール
    
    # 法令上の職務
    job_assignments = db.relationship('SupporterJobAssignment', back_populates='supporter', lazy='dynamic')
    
    # パーミッション上書き
    permission_overrides = db.relationship('SupporterPermissionOverride', back_populates='supporter', cascade="all, delete-orphan") # ★ パーミッション
    
    # 責任承認ログ
    admin_action_logs = db.relationship('SystemAdminActionLog', back_populates='supporter')
    
    # ... (その他リレーションシップ) ...
    primary_users = db.relationship('User', back_populates='primary_supporter', foreign_keys='User.primary_supporter_id')
    plan_approvals = db.relationship('SupportPlan', back_populates='sabikan', foreign_keys='SupportPlan.sabikan_id')
    assessment_approvals = db.relationship('Assessment', back_populates='sabikan', foreign_keys='Assessment.sabikan_id')
    monitoring_approvals = db.relationship('Monitoring', back_populates='sabikan', foreign_keys='Monitoring.sabikan_id')
    responsible_tasks = db.relationship('SpecificGoal', back_populates='responsible_supporter', foreign_keys='SpecificGoal.responsible_supporter_id')
    daily_logs = db.relationship('DailyLog', foreign_keys='[DailyLog.supporter_id]', back_populates='creator')
    approved_daily_logs = db.relationship('DailyLog', foreign_keys='[DailyLog.approved_by_id]', back_populates='approver')
    onsite_daily_logs = db.relationship('DailyLog', foreign_keys='[DailyLog.supporter_on_site_id]', back_populates='supporter_on_site')
    timecards = db.relationship('SupporterTimecard', back_populates='supporter')
    approved_requests = db.relationship('UserRequest', back_populates='approver_supporter', foreign_keys='UserRequest.approver_supporter_id')
    created_schedules = db.relationship('Schedule', back_populates='creator_supporter', foreign_keys='Schedule.creator_supporter_id')
    scheduled_participations = db.relationship('ScheduleParticipant', back_populates='supporter')
    sent_support_messages = db.relationship('ChatMessage', back_populates='sender_supporter', foreign_keys='ChatMessage.sender_supporter_id')
    staff_channel_participations = db.relationship('ChannelParticipant', back_populates='supporter')
    sent_staff_messages = db.relationship('ChannelMessage', back_populates='sender_supporter', foreign_keys='ChannelMessage.sender_supporter_id')


    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def set_pin(self, pin):
        """職員用PIN設定メソッド"""
        self.pin_hash = bcrypt.generate_password_hash(pin).decode('utf-8')

    def check_pin(self, pin):
        """職員用PINチェックメソッド"""
        if self.pin_hash is None: return False
        return bcrypt.check_password_hash(self.pin_hash, pin)


# --- 2. User (利用者・見学者) ---
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    
    # ★ 修正: display_name（必須）と実名（任意）の分離
    last_name = db.Column(db.String(50), nullable=True) 
    first_name = db.Column(db.String(50), nullable=True)
    display_name = db.Column(db.String(100), nullable=False) 
    
    last_name_kana = db.Column(db.String(50))
    first_name_kana = db.Column(db.String(50))
    birth_date = db.Column(db.Date)
    gender = db.Column(db.String(10)) 
    
    # 連絡先
    postal_code = db.Column(db.String(10))
    address = db.Column(db.String(255))
    phone_number = db.Column(db.String(20))
    
    # 認証
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(128), nullable=True) 
    pin_hash = db.Column(db.String(128), nullable=True)
    
    # 汎用SNSカラム (LINE, X, Googleなど)
    sns_provider = db.Column(db.String(50), nullable=True, index=True) 
    sns_account_id = db.Column(db.String(255), nullable=True, index=True)
    
    # 印影
    seal_image_url = db.Column(db.String(500), nullable=True)
    
    # サービス・契約状況
    service_start_date = db.Column(db.Date) 
    service_end_date = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_archivable = db.Column(db.Boolean, default=False, nullable=False)
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
    
    # 外部キー
    primary_supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'))
    status_id = db.Column(db.Integer, db.ForeignKey('status_master.id'), nullable=False)

    # マーケティング（流入経路）
    utm_source = db.Column(db.String(100), nullable=True, index=True) 
    utm_medium = db.Column(db.String(100), nullable=True) 
    utm_campaign = db.Column(db.String(100), nullable=True) 
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) 
    remarks = db.Column(db.Text)

    # --- リレーションシップ ---
    status = db.relationship('StatusMaster', foreign_keys=[status_id]) 
    disability_type = db.relationship('DisabilityTypeMaster', back_populates='users')
    primary_supporter = db.relationship(
        'Supporter', 
        back_populates='primary_users',
        foreign_keys=[primary_supporter_id]
    )
    
    # ... (その他リレーションシップ) ...
    
    def set_password(self, password):
        from app.extensions import bcrypt 
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        from app.extensions import bcrypt
        if self.password_hash is None: return False
        return bcrypt.check_password_hash(self.password_hash, password)

    def set_pin(self, pin):
        from app.extensions import bcrypt
        self.pin_hash = bcrypt.generate_password_hash(pin).decode('utf-8')

    def check_pin(self, pin):
        from app.extensions import bcrypt
        if self.pin_hash is None: return False
        return bcrypt.check_password_hash(self.pin_hash, pin)
        
    # ★ 汎用カラムを使う場合の制約
    __table_args__ = (
        CheckConstraint(
            '(sns_provider IS NULL AND sns_account_id IS NULL) OR '
            '(sns_provider IS NOT NULL AND sns_account_id IS NOT NULL)',
            name='ck_user_sns_auth_pair'
        ),
        UniqueConstraint('sns_provider', 'sns_account_id', name='uq_user_sns_auth')
    )

# --- 3. AttendancePlan (通所予定 - 旧) ---
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

# --- 4. DailyLog (日報 - 旧) ---
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

# --- 5. Contact (関連機関・連絡先) ---
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
