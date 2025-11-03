from app.extensions import db, bcrypt
from datetime import datetime, timezone  # timezone をインポート
from sqlalchemy.orm import relationship

class User(db.Model):
    __tablename__ = 'users'
    # 既存の定義との衝突を避けるため、extend_existing=True を追加
    __table_args__ = ({"extend_existing": True},) 
    
    id = db.Column(db.Integer, primary_key=True)
    
    # --- 基本情報 ---
    last_name = db.Column(db.String(50), nullable=False, index=True)
    first_name = db.Column(db.String(50), nullable=False, index=True)
    last_name_kana = db.Column(db.String(50), index=True)
    first_name_kana = db.Column(db.String(50), index=True)
    
    # --- フェイスシート（基本） ---
    birth_date = db.Column(db.Date)
    gender_legal_id = db.Column(db.Integer, db.ForeignKey('gender_legal_master.id')) 
    gender_identity = db.Column(db.String(100)) # 自己申告 (nullable=True)
    postal_code = db.Column(db.String(10))
    address = db.Column(db.String(255))
    phone_number = db.Column(db.String(20))
    email = db.Column(db.String(120), unique=True, index=True)

    # --- 障害・支援情報（フェイスシート） ---
    disability_type_id = db.Column(db.Integer, db.ForeignKey('disability_type_master.id')) 
    disability_details = db.Column(db.Text)
    support_needs = db.Column(db.Text)
    
    # --- システム管理情報 ---
    pin_hash = db.Column(db.String(128))
    status_id = db.Column(db.Integer, db.ForeignKey('status_master.id'), nullable=False, index=True)
    primary_supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), index=True)
    start_date = db.Column(db.Date, index=True)
    end_date = db.Column(db.Date)
    
    # --- タイムスタンプ (utcnow() を修正) ---
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    remarks = db.Column(db.Text)

    # --- パスワード（PIN）管理メソッド ---
    def set_pin(self, pin):
        self.pin_hash = bcrypt.generate_password_hash(pin).decode('utf-8')

    def check_pin(self, pin):
        if not self.pin_hash:
            return False
        return bcrypt.check_password_hash(self.pin_hash, pin)

    # --- リレーションシップ定義 (循環参照回避のため文字列で指定) ---
    
    # (app/models/master/...)
    status = db.relationship('StatusMaster', foreign_keys=[status_id])
    disability_type = db.relationship('DisabilityTypeMaster', foreign_keys=[disability_type_id])
    gender_legal = db.relationship('GenderLegalMaster', foreign_keys=[gender_legal_id])

    # (app/models/staff/supporter.py)
    primary_supporter = db.relationship('Supporter', back_populates='primary_users', foreign_keys=[primary_supporter_id])
    
    # (app/models/user/profile.py)
    family_members = db.relationship('FamilyMember', back_populates='user', lazy='dynamic', cascade="all, delete-orphan")
    emergency_contacts = db.relationship('EmergencyContact', back_populates='user', lazy='dynamic', cascade="all, delete-orphan")
    developmental_history_items = db.relationship('DevelopmentalHistoryItem', back_populates='user', lazy='dynamic', order_by='DevelopmentalHistoryItem.sort_order', cascade="all, delete-orphan")

    # (app/models/user/compliance.py)
    certificates = db.relationship('Certificate', back_populates='user', lazy='dynamic', cascade="all, delete-orphan")

    # (app/models/user/skill.py)
    qualifications = db.relationship('Qualification', back_populates='user', lazy='dynamic', cascade="all, delete-orphan")

    # (app/models/activity/...)
    attendance_plans = db.relationship('AttendancePlan', back_populates='user', cascade="all, delete-orphan")
    daily_logs = db.relationship('DailyLog', back_populates='user', cascade="all, delete-orphan")
    contacts = db.relationship('Contact', back_populates='user', cascade="all, delete-orphan")

    # (app/models/plan/...)
    support_plans = db.relationship('SupportPlan', back_populates='user', cascade="all, delete-orphan")
    assessments = db.relationship('Assessment', back_populates='user', cascade="all, delete-orphan")
    meeting_minutes = db.relationship('MeetingMinute', back_populates='user', cascade="all, delete-orphan")
    medical_reports = db.relationship('MedicalReport', back_populates='user', cascade="all, delete-orphan")
    intents = db.relationship('UserIntent', back_populates='user', cascade="all, delete-orphan")
    readiness_assessments = db.relationship('ReadinessAssessment', back_populates='user', lazy='dynamic', cascade="all, delete-orphan")

    # (app/models/audit/system_log.py)
    system_logs = db.relationship('SystemLog', back_populates='user', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<User {self.id}: {self.last_name} {self.first_name}>'