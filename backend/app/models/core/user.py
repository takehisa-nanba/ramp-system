# backend/app/models/core/user.py

from backend.app.extensions import db, bcrypt
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, Text, UniqueConstraint, CheckConstraint, func

# 修正点: 循環参照を避けるため、security_serviceやcore_serviceは
# 各メソッド内で実行時にインポートします。
import datetime

# ====================================================================
# 1. User (利用者の業務データ / システムの核)
# ====================================================================
class User(db.Model):
    """
    利用者の業務データ（システムの核）。
    個人特定可能情報(PII)や認証情報を一切含まず、匿名IDのみで管理する。
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
    
    # PII（個人特定可能情報＆認証）保管庫への1対1リレーション
    pii = db.relationship('UserPII', back_populates='user', uselist=False, cascade="all, delete-orphan")
    
    # マスター関連 (mastersパッケージのモデルを参照)
    status = db.relationship('StatusMaster', foreign_keys=[status_id], back_populates='users')
    
    # Supporter関連 (core/supporter.py の Supporter モデルを参照)
    primary_supporter = db.relationship('Supporter', back_populates='primary_users', foreign_keys=[primary_supporter_id])
    
    # --- 利用者の中核的な子テーブル ---
    certificates = db.relationship('ServiceCertificate', back_populates='user', lazy='dynamic', cascade="all, delete-orphan")
    profile = db.relationship('UserProfile', back_populates='user', uselist=False, cascade="all, delete-orphan")
    holistic_policies = db.relationship('HolisticSupportPolicy', back_populates='user', lazy='dynamic', cascade="all, delete-orphan")
    skills = db.relationship('UserSkill', back_populates='user', lazy='dynamic', cascade="all, delete-orphan")
    documents = db.relationship('UserDocument', back_populates='user', lazy='dynamic', cascade="all, delete-orphan")
    family_members = db.relationship('FamilyMember', back_populates='user', lazy='dynamic', cascade="all, delete-orphan")
    emergency_contacts = db.relationship('EmergencyContact', back_populates='user', lazy='dynamic', cascade="all, delete-orphan")

    # --- 支援プロセスの子テーブル ---
    support_plans = db.relationship('SupportPlan', back_populates='user', lazy='dynamic', cascade="all, delete-orphan")
    daily_logs = db.relationship('DailyLog', back_populates='user', lazy='dynamic', cascade="all, delete-orphan")

    # --- 請求・会計の子テーブル ---
    billings = db.relationship('BillingData', back_populates='user', lazy='dynamic', cascade="all, delete-orphan")
    
    # --- コミュニケーションの子テーブル ---
    support_threads = db.relationship('SupportThread', back_populates='user', lazy='dynamic', cascade="all, delete-orphan")
    user_requests = db.relationship('UserRequest', back_populates='user', lazy='dynamic', cascade="all, delete-orphan")
    organization_links = db.relationship('UserOrganizationLink', back_populates='user', lazy='dynamic')
    
    # --- 定着支援の子テーブル ---
    retention_contracts = db.relationship('JobRetentionContract', back_populates='user', lazy='dynamic')
    follow_ups = db.relationship('PostTransitionFollowUp', back_populates='user', lazy='dynamic')
    
    # --- 就労先の子テーブル ---
    job_placements = db.relationship('JobPlacementLog', back_populates='user', lazy='dynamic')
    
    # --- ★ 追加: 危機対応計画 (今回のエラー原因) ---
    crisis_plans = db.relationship('CrisisPlan', back_populates='user', lazy='dynamic', cascade="all, delete-orphan")
    # --- ★ 追加: インシデント・苦情 ---
    incident_reports = db.relationship('IncidentReport', back_populates='user', lazy='dynamic')
    # ComplaintLogは foreign_keys 指定が必要
    # ★ 修正: 参照先カラム名を 'target_user_id' に変更
    complaints = db.relationship(
        'ComplaintLog', 
        foreign_keys='ComplaintLog.target_user_id', # ここを修正
        lazy='dynamic',
        overlaps="target_user" # 相手側のリレーション名に合わせる
    )    # --- ★ 追加: ケース会議 ---
    case_conferences = db.relationship('CaseConferenceLog', back_populates='user', lazy='dynamic')
    # --- 監査・コンプライアンス ---
    compliance_events = db.relationship('ComplianceEventLog', back_populates='user', lazy='dynamic')
    # ★ 追加: スケジュールへの明示的なリレーション
    # (secondaryは文字列で指定して循環参照を回避)
    user_schedules = db.relationship(
        'Schedule', 
        secondary='schedule_participants', 
        back_populates='participants_user',
        overlaps="participants_supporter, supporter_schedules" # ★ ここ！
    )

    def __repr__(self):
        return f'<User {self.id}: {self.display_name}>'

# ====================================================================
# 2. UserPII (個人特定可能情報 & 認証 / 3階層暗号化)
# ====================================================================
class UserPII(db.Model):
    """
    利用者の最高機密情報（PII）および認証情報。
    Userモデルと1対1で紐づき、データは3階層の暗号化戦略で隔離される（原理6）。
    """
    __tablename__ = 'user_pii'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    
    # --- 階層1：最高機密（エンベロープ暗号化） ---
    encrypted_certificate_number = Column(String(512)) # 受給者証番号
    encrypted_data_key = Column(String(512)) # ★ 法人KEKで暗号化されたDEK

    # --- 階層2：機密PII（システム共通鍵暗号化） ---
    # 氏名、住所、連絡先などは「階層2」の鍵で暗号化
    encrypted_last_name = Column(String(255))
    encrypted_first_name = Column(String(255))
    encrypted_last_name_kana = Column(String(255))
    encrypted_first_name_kana = Column(String(255))
    encrypted_address = Column(String(512))
    
    # --- 平文（検索・計算・ユニーク制約用） ---
    # 原理4（パフォーマンス）と原理6（セキュリティ）のバランス調整結果
    birth_date = Column(Date) # 年齢計算・検索のため平文
    phone_number = Column(String(20), index=True) # 重複チェックのため平文
    email = Column(String(120), unique=True, index=True) # ログインIDのため平文
    
    sns_account_id = Column(String(255), index=True)
    sns_provider = Column(String(50), index=True) 

    # --- 階層3：認証情報（ハッシュ化） ---
    password_hash = Column(String(128)) 
    pin_hash = Column(String(128))
    
    # --- 平文（暗号化不要）の業務データ ---
    gender_legal_id = Column(Integer, ForeignKey('gender_legal_master.id')) 
    gender_identity = Column(String(100))
    disability_type_id = Column(Integer, ForeignKey('disability_type_master.id')) 
    disability_details = Column(Text)
    support_needs = Column(Text)
    handbook_level = Column(String(20))
    is_handbook_certified = Column(Boolean, default=False, nullable=False)
    
    # --- リレーションシップ ---
    user = db.relationship('User', back_populates='pii', uselist=False)
    gender_legal = db.relationship('GenderLegalMaster', foreign_keys=[gender_legal_id])
    disability_type = db.relationship('DisabilityTypeMaster', foreign_keys=[disability_type_id])

    # === プロパティ（ゲッター/セッター）による暗号化の抽象化 ===
    
    def _get_corporation_id(self) -> int:
        """
        このPIIが属する「法人ID」を取得する。
        """
        #  暫定的なフォールバック（本来は契約情報から取得）
        return 1 

    # --- 階層1：受給者証番号 (エンベロープ暗号化) ---
    @property
    def certificate_number(self):
        """受給者証番号（平文）を読み出す (階層1)"""
        if not self.encrypted_certificate_number or not self.encrypted_data_key:
            return None
        
        # 実行時インポート（循環参照回避）
        from backend.app.services.core_service import get_corporation_id_for_user, get_corporation_kek
        from backend.app.services.security_service import decrypt_data_envelope
        
        corp_id = get_corporation_id_for_user(self.user)
        kek_bytes = get_corporation_kek(corp_id)
        
        return decrypt_data_envelope(
            self.encrypted_certificate_number, 
            self.encrypted_data_key, 
            kek_bytes
        )

    @certificate_number.setter
    def certificate_number(self, plaintext):
        """受給者証番号（平文）を暗号化して保存する (階層1)"""
        from backend.app.services.core_service import get_corporation_id_for_user, get_corporation_kek
        from backend.app.services.security_service import encrypt_data_envelope
        
        if plaintext:
            corp_id = get_corporation_id_for_user(self.user)
            kek_bytes = get_corporation_kek(corp_id)
            
            encrypted_data, encrypted_key = encrypt_data_envelope(plaintext, kek_bytes)
            self.encrypted_certificate_number = encrypted_data
            self.encrypted_data_key = encrypted_key
        else:
            self.encrypted_certificate_number = None
            self.encrypted_data_key = None

    # --- 階層2：機密PII (システム共通鍵) ---
    
    @property
    def last_name(self):
        from backend.app.services.core_service import get_system_pii_key
        from backend.app.services.security_service import decrypt_data_pii
        key = get_system_pii_key()
        return decrypt_data_pii(self.encrypted_last_name, key)

    @last_name.setter
    def last_name(self, plaintext):
        from backend.app.services.core_service import get_system_pii_key
        from backend.app.services.security_service import encrypt_data_pii
        key = get_system_pii_key()
        self.encrypted_last_name = encrypt_data_pii(plaintext, key)

    @property
    def first_name(self):
        from backend.app.services.core_service import get_system_pii_key
        from backend.app.services.security_service import decrypt_data_pii
        key = get_system_pii_key()
        return decrypt_data_pii(self.encrypted_first_name, key)

    @first_name.setter
    def first_name(self, plaintext):
        from backend.app.services.core_service import get_system_pii_key
        from backend.app.services.security_service import encrypt_data_pii
        key = get_system_pii_key()
        self.encrypted_first_name = encrypt_data_pii(plaintext, key)

    @property
    def last_name_kana(self):
        from backend.app.services.core_service import get_system_pii_key
        from backend.app.services.security_service import decrypt_data_pii
        key = get_system_pii_key()
        return decrypt_data_pii(self.encrypted_last_name_kana, key)

    @last_name_kana.setter
    def last_name_kana(self, plaintext):
        from backend.app.services.core_service import get_system_pii_key
        from backend.app.services.security_service import encrypt_data_pii
        key = get_system_pii_key()
        self.encrypted_last_name_kana = encrypt_data_pii(plaintext, key)

    @property
    def first_name_kana(self):
        from backend.app.services.core_service import get_system_pii_key
        from backend.app.services.security_service import decrypt_data_pii
        key = get_system_pii_key()
        return decrypt_data_pii(self.encrypted_first_name_kana, key)

    @first_name_kana.setter
    def first_name_kana(self, plaintext):
        from backend.app.services.core_service import get_system_pii_key
        from backend.app.services.security_service import encrypt_data_pii
        key = get_system_pii_key()
        self.encrypted_first_name_kana = encrypt_data_pii(plaintext, key)
        
    @property
    def address(self):
        from backend.app.services.core_service import get_system_pii_key
        from backend.app.services.security_service import decrypt_data_pii
        key = get_system_pii_key()
        return decrypt_data_pii(self.encrypted_address, key)

    @address.setter
    def address(self, plaintext):
        from backend.app.services.core_service import get_system_pii_key
        from backend.app.services.security_service import encrypt_data_pii
        key = get_system_pii_key()
        self.encrypted_address = encrypt_data_pii(plaintext, key)

    # --- 階層3：認証 ---
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