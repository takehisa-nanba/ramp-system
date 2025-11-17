# 🚨 修正点: 'from app.extensions...' を相対パスに変更
from ...extensions import db, bcrypt
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, Text, UniqueConstraint, CheckConstraint, func

# 🚨 修正点: 'from app.services...' を相対パスに変更
from ...services.security_service import encrypt_data, decrypt_data 

# ====================================================================
# 1. User (利用者の業務データ / システムの核)
# ====================================================================
class User(db.Model):
    """
    利用者の業務データ（システムの核）。
    個人特定可能情報(PII)を一切含まず、匿名IDとステータスで管理する。
    """
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    
    # ★ 必須: 匿名化後も使用する表示名（原理5）
    display_name = Column(String(100), nullable=False, index=True) 
    
    # --- システム管理情報 ---
    status_id = Column(Integer, ForeignKey('status_master.id'), nullable=False, index=True)
    primary_supporter_id = Column(Integer, ForeignKey('supporters.id'), index=True)
    service_start_date = Column(Date, index=True)
    service_end_date = Column(Date)
    
    # ★ 復職支援ケースフラグ（原理14）
    is_return_to_work_case = Column(Boolean, default=False)
    
    remarks = Column(Text) # 職員が使用する内部的な備考欄

    # --- タイムスタンプ ---
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # --- リレーションシップ ---
    
    # PII（個人特定可能情報）保管庫への1対1リレーション
    pii = relationship('UserPII', back_populates='user', uselist=False, cascade="all, delete-orphan")
    
    # マスター関連 (mastersパッケージのモデルを参照)
    status = relationship('StatusMaster', foreign_keys=[status_id], back_populates='users')
    
    # Supporter関連 (core/supporter.py の Supporter モデルを参照)
    primary_supporter = relationship('Supporter', back_populates='primary_users', foreign_keys=[primary_supporter_id])
    
    # --- 利用者の中核的な子テーブル ---
    certificates = relationship('ServiceCertificate', back_populates='user', lazy='dynamic', cascade="all, delete-orphan")
    profile = relationship('UserProfile', back_populates='user', uselist=False, cascade="all, delete-orphan")
    holistic_policies = relationship('HolisticSupportPolicy', back_populates='user', lazy='dynamic', cascade="all, delete-orphan")
    skills = relationship('UserSkill', back_populates='user', lazy='dynamic', cascade="all, delete-orphan")
    documents = relationship('UserDocument', back_populates='user', lazy='dynamic', cascade="all, delete-orphan")

    # --- 支援プロセスの子テーブル ---
    support_plans = relationship('SupportPlan', back_populates='user', lazy='dynamic', cascade="all, delete-orphan")
    daily_logs = relationship('DailyLog', back_populates='user', lazy='dynamic', cascade="all, delete-orphan")
    
    # --- コミュニケーションの子テーブル ---
    support_threads = relationship('SupportThread', back_populates='user', lazy='dynamic', cascade="all, delete-orphan")
    user_requests = relationship('UserRequest', back_populates='user', lazy='dynamic', cascade="all, delete-orphan")
    organization_links = relationship('UserOrganizationLink', back_populates='user', lazy='dynamic')
    
    # --- 定着支援の子テーブル ---
    retention_contracts = relationship('JobRetentionContract', back_populates='user', lazy='dynamic')
    follow_ups = relationship('PostTransitionFollowUp', back_populates='user', lazy='dynamic')
    
    # --- 就労先の子テーブル ---
    job_placements = relationship('JobPlacementLog', back_populates='user', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.id}: {self.display_name}>'

# ====================================================================
# 2. UserPII (個人特定可能情報 / 暗号化隔離)
# ====================================================================
class UserPII(db.Model):
    """
    利用者の最高機密情報（PII）。
    Userモデルと1対1で紐づき、データは暗号化されて隔離される（原理6）。
    """
    __tablename__ = 'user_pii'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    
    # --- 基本情報 (匿名化対象) ---
    last_name = Column(String(50), index=True, nullable=True) 
    first_name = Column(String(50), index=True, nullable=True)
    last_name_kana = Column(String(50), index=True)
    first_name_kana = Column(String(50), index=True)
    
    birth_date = Column(Date)
    gender_legal_id = Column(Integer, ForeignKey('gender_legal_master.id')) 
    gender_identity = Column(String(100))
    postal_code = Column(String(10))
    address = Column(String(255))
    phone_number = Column(String(20))
    
    # --- 認証情報 (セキュリティの責務) ---
    email = Column(String(120), unique=True, index=True)
    password_hash = Column(String(128)) 
    pin_hash = Column(String(128))
    
    # 汎用SNS認証情報
    sns_provider = Column(String(50), index=True) 
    sns_account_id = Column(String(255), index=True)
    
    # ★ 最高機密: 受給者証番号
    encrypted_certificate_number = Column(String(512)) 
    
    # --- 障害・支援情報 ---
    disability_type_id = Column(Integer, ForeignKey('disability_type_master.id')) 
    disability_details = Column(Text)
    support_needs = Column(Text)
    handbook_level = Column(String(20))
    is_handbook_certified = Column(Boolean, default=False, nullable=False)
    
    # --- リレーションシップ ---
    user = relationship('User', back_populates='pii', uselist=False)
    gender_legal = relationship('GenderLegalMaster', foreign_keys=[gender_legal_id], back_populates='users')
    disability_type = relationship('DisabilityTypeMaster', foreign_keys=[disability_type_id], back_populates='users')

    # --- 受給者証番号のゲッター/セッター（暗号化ロジック） ---
    @property
    def certificate_number(self):
        """受給者証番号（平文）を読み出す"""
        if self.encrypted_certificate_number:
            return decrypt_data(self.encrypted_certificate_number)
        return None

    @certificate_number.setter
    def certificate_number(self, plaintext):
        """受給者証番号（平文）を暗号化して保存する"""
        if plaintext:
            self.encrypted_certificate_number = encrypt_data(plaintext)
        else:
            self.encrypted_certificate_number = None

    # --- 認証メソッド ---
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        if self.password_hash is None: return False
        return bcrypt.check_password_hash(self.password_hash, password)

    def set_pin(self, pin):
        self.pin_hash = bcrypt.generate_password_hash(pin).decode('utf-8')

    def check_pin(self, pin):
        if self.pin_hash is None: return False
        return bcrypt.check_password_hash(self.pin_hash, pin)

    __table_args__ = (
        CheckConstraint(
            '(sns_provider IS NULL AND sns_account_id IS NULL) OR '
            '(sns_provider IS NOT NULL AND sns_account_id IS NOT NULL)',
            name='ck_userpii_sns_auth_pair'
        ),
        UniqueConstraint('sns_provider', 'sns_account_id', name='uq_userpii_sns_auth')
    )