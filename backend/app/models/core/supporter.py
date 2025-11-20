# 🚨 修正点: 'from backend.app.extensions' (絶対参照)
from backend.app.extensions import db, bcrypt
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, UniqueConstraint, Text, func

# 🚨 修正点: rbac_links を絶対参照でインポート
from backend.app.models.core.rbac_links import supporter_role_link

# ====================================================================
# 1. Supporter (職員の業務エンティティ / 表)
# ====================================================================
class Supporter(db.Model):
    """
    職員（支援者）の業務情報（表）。
    検索可能・公開可能な情報のみを保持する。
    """
    __tablename__ = 'supporters'
    
    id = Column(Integer, primary_key=True)
    
    # --- 基本情報 (平文・業務上必須) ---
    last_name = Column(String(50), nullable=False, index=True)
    first_name = Column(String(50), nullable=False, index=True)
    last_name_kana = Column(String(50), nullable=False)
    first_name_kana = Column(String(50), nullable=False)
    
    # 所属事業所 (ホームベース / JOBロールの基本単位)
    office_id = Column(Integer, ForeignKey('office_settings.id'), nullable=True, index=True)
    
    # --- 契約ステータス (常勤換算の基礎) ---
    hire_date = Column(Date, nullable=False) # 入社日
    retirement_date = Column(Date, nullable=True) # 退職日
    
    # (例: 'FULL_TIME', 'SHORTENED_FT', 'PART_TIME')
    employment_type = Column(String(50), nullable=False) 
    
    # 個人の週所定労働時間（分）。常勤/非常勤の判定に使用
    weekly_scheduled_minutes = Column(Integer, nullable=False) 
    
    # アカウント有効化フラグ
    is_active = Column(Boolean, default=True, nullable=False)

    # --- リレーションシップ ---
    
    # PII（機密情報）保管庫への1対1リレーション
    pii = relationship('SupporterPII', back_populates='supporter', uselist=False, cascade="all, delete-orphan")
    
    # 子テーブル
    timecards = relationship('SupporterTimecard', back_populates='supporter', lazy='dynamic', cascade="all, delete-orphan")
    job_assignments = relationship('SupporterJobAssignment', back_populates='supporter', lazy='dynamic', cascade="all, delete-orphan")
    qualifications = relationship('SupporterQualification', back_populates='supporter', lazy='dynamic', cascade="all, delete-orphan")
    
    # 活動配分ログ（あいまい回避のため foreign_keys を明示）
    activity_allocations = relationship(
        'StaffActivityAllocationLog', 
        back_populates='supporter', 
        foreign_keys='StaffActivityAllocationLog.supporter_id', 
        lazy='dynamic', 
        cascade="all, delete-orphan"
    )
    
    # 勤怠修正申請（あいまい回避のため foreign_keys を明示）
    attendance_correction_requests = relationship(
        'AttendanceCorrectionRequest', 
        back_populates='supporter',
        foreign_keys='AttendanceCorrectionRequest.supporter_id', 
        lazy='dynamic'
    )
    
    # ★ RBAC（役割）へのリレーションシップ
    roles = relationship('RoleMaster', secondary=supporter_role_link, back_populates='supporters')
    
    # 逆参照 (User)
    primary_users = relationship('User', back_populates='primary_supporter', lazy='dynamic')
    
    # 逆参照 (Office - 管理者など)
    # ※ owned_offices は削除しました（OfficeSetting側のカラム削除に伴い）
    
    # サービス管理責任者としての担当サービス
    managed_services = relationship('OfficeServiceConfiguration', back_populates='manager_supporter', foreign_keys='OfficeServiceConfiguration.manager_supporter_id')
    
    # 内省ログ
    reflection_logs = relationship('StaffReflectionLog', back_populates='supporter', lazy='dynamic')
    
    # ★ 追加: 所属事業所へのリレーション
    office = relationship('OfficeSetting', back_populates='staff_members', foreign_keys=[office_id])
    
    def __repr__(self):
        return f'<Supporter {self.id}: {self.last_name} {self.first_name}>'


# ====================================================================
# 2. SupporterPII (職員機密情報 / 裏 / 暗号化)
# ====================================================================
class SupporterPII(db.Model):
    """
    職員の機密情報保管庫。
    CORPORATEロールのみがアクセス可能（原理6）。
    """
    __tablename__ = 'supporter_pii'
    
    id = Column(Integer, primary_key=True)
    supporter_id = Column(Integer, ForeignKey('supporters.id'), unique=True, nullable=False)
    
    # --- 認証情報 (ログインIDは平文・検索用) ---
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(128)) # ハッシュ化
    
    # --- 機密個人情報 (階層2：システム共通鍵で暗号化) ---
    encrypted_personal_phone = Column(String(255))
    encrypted_address = Column(String(512))
    encrypted_bank_account_info = Column(String(512)) # 給与振込先など
    
    # --- 契約書類 (証憑) ---
    encrypted_employment_contract_url = Column(String(500)) # 雇用契約書URL
    encrypted_resume_url = Column(String(500)) # 履歴書URL
    
    supporter = relationship('Supporter', back_populates='pii', uselist=False)

    # === 暗号化プロパティ ===
    
    @property
    def personal_phone(self):
        from backend.app.services.security_service import decrypt_data_pii
        return decrypt_data_pii(self.encrypted_personal_phone)

    @personal_phone.setter
    def personal_phone(self, plaintext):
        from backend.app.services.security_service import encrypt_data_pii
        self.encrypted_personal_phone = encrypt_data_pii(plaintext)

    @property
    def address(self):
        from backend.app.services.security_service import decrypt_data_pii
        return decrypt_data_pii(self.encrypted_address)

    @address.setter
    def address(self, plaintext):
        from backend.app.services.security_service import encrypt_data_pii
        self.encrypted_address = encrypt_data_pii(plaintext)

    @property
    def employment_contract_url(self):
        from backend.app.services.security_service import decrypt_data_pii
        return decrypt_data_pii(self.encrypted_employment_contract_url)

    @employment_contract_url.setter
    def employment_contract_url(self, plaintext):
        from backend.app.services.security_service import encrypt_data_pii
        self.encrypted_employment_contract_url = encrypt_data_pii(plaintext)

    # --- 認証メソッド ---
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        if self.password_hash is None: return False
        return bcrypt.check_password_hash(self.password_hash, password)


# ====================================================================
# 3. SupporterTimecard (日々の勤怠 / 常勤換算の実績)
# ====================================================================
class SupporterTimecard(db.Model):
    """
    職員の勤怠記録。
    常勤換算の分子となる「事実」を記録する。
    """
    __tablename__ = 'supporter_timecards'
    
    id = Column(Integer, primary_key=True)
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False, index=True)
    
    # ★ 事業所間兼務対応: どのサービス(事業所番号)での勤務か
    office_service_configuration_id = Column(Integer, ForeignKey('office_service_configurations.id'), nullable=False, index=True)
    
    work_date = Column(Date, nullable=False, index=True)
    
    # --- 実績時間 ---
    check_in = Column(DateTime) 
    check_out = Column(DateTime)
    total_break_minutes = Column(Integer, default=0, nullable=False)
    
    # --- 常勤換算と法令遵守（みなし時間） ---
    scheduled_work_minutes = Column(Integer, default=0, nullable=False)
    
    is_absent = Column(Boolean, default=False)
    absence_type = Column(String(50)) # 'PAID_LEAVE', 'TRAINING', etc.
    deemed_work_minutes = Column(Integer, default=0) # 有給などのみなし時間
    
    # 施設外就労の担当時間 (日次人員配置チェック用)
    facility_out_minutes = Column(Integer, default=0)
    
    supporter = relationship('Supporter', back_populates='timecards')
    service_config = relationship('OfficeServiceConfiguration')


# ====================================================================
# 4. SupporterJobAssignment (職務割り当て / 兼務の責務)
# ====================================================================
class SupporterJobAssignment(db.Model):
    """
    職員の職務割り当て履歴。
    「誰が、いつ、どこで、何の職務を、どれくらいの割合で」担うかを管理。
    """
    __tablename__ = 'supporter_job_assignments'
    
    id = Column(Integer, primary_key=True)
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False, index=True)
    job_title_id = Column(Integer, ForeignKey('job_title_master.id'), nullable=False, index=True)
    
    # どのサービス（事業所番号）で (事業所間兼務の判定キー)
    office_service_configuration_id = Column(Integer, ForeignKey('office_service_configurations.id'), nullable=False, index=True)
    
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    
    # ★ 常勤換算割合の明示
    assigned_minutes = Column(Integer, nullable=False)
    
    # --- サビ管みなし配置の証跡 ---
    is_deemed_assignment = Column(Boolean, default=False) # みなし配置フラグ
    deemed_expiry_date = Column(Date) # みなし期限
    
    supporter = relationship('Supporter', back_populates='job_assignments')
    job_title = relationship('JobTitleMaster', back_populates='assignments')
    
    __table_args__ = (
        UniqueConstraint('supporter_id', 'job_title_id', 'start_date', 'office_service_configuration_id', name='uq_supporter_job_assignment'),
    )


# ====================================================================
# 5. SupporterQualification (保有資格 / 証憑と公開設定)
# ====================================================================
class SupporterQualification(db.Model):
    """
    職員の保有資格・スキル・実務経験証明書。
    """
    __tablename__ = 'supporter_qualifications'
    
    id = Column(Integer, primary_key=True)
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False, index=True)
    qualification_master_id = Column(Integer, ForeignKey('qualification_master.id'), nullable=False)
    
    # --- 証憑 (原理1) ---
    certification_date = Column(Date) 
    expiry_date = Column(Date) 
    certificate_document_url = Column(String(500)) # 証憑
    
    # 公開設定（自己決定権 / 原理2）
    # 'PUBLIC', 'MANAGERS_ONLY', 'PRIVATE'
    visibility_scope = Column(String(20), default='PUBLIC', nullable=False)
    
    supporter = relationship('Supporter', back_populates='qualifications')
    qualification_master = relationship('QualificationMaster', back_populates='supporter_qualifications')


# ====================================================================
# 6. StaffActivityAllocationLog (活動配分 / ムダ取り)
# ====================================================================
class StaffActivityAllocationLog(db.Model):
    """
    職員の日次の活動時間配分（支援、事務、移動など）。
    時間帯の強制を廃止し、合計分数で管理する（自由と規律の両立）。
    """
    __tablename__ = 'staff_activity_allocation_logs'
    
    id = Column(Integer, primary_key=True)
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False, index=True)
    activity_date = Column(Date, nullable=False)
    
    staff_activity_master_id = Column(Integer, ForeignKey('staff_activity_master.id'), nullable=False)
    
    # 合計時間 (分)
    allocated_minutes = Column(Integer, nullable=False)
    
    # 管理業務フラグ（同時刻の二重計上の例外判定などに使用）
    is_governance_task = Column(Boolean, default=False)
    
    # --- 承認 ---
    approver_id = Column(Integer, ForeignKey('supporters.id'))
    
    supporter = relationship('Supporter', foreign_keys=[supporter_id], back_populates='activity_allocations')
    activity_type = relationship('StaffActivityMaster', back_populates='logs')
    approver = relationship('Supporter', foreign_keys=[approver_id])


# ====================================================================
# 7. AttendanceCorrectionRequest (勤怠修正申請)
# ====================================================================
class AttendanceCorrectionRequest(db.Model):
    """職員による勤怠修正申請ログ。"""
    __tablename__ = 'supporter_attendance_correction_requests'
    
    id = Column(Integer, primary_key=True)
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False, index=True)
    
    target_date = Column(Date, nullable=False)
    record_type = Column(String(20), nullable=False)
    requested_timestamp = Column(DateTime, nullable=False)
    
    request_reason = Column(Text, nullable=False) # 申請理由 (NULL禁止)
    
    request_status = Column(String(20), default='PENDING') 
    approver_id = Column(Integer, ForeignKey('supporters.id'))
    processed_at = Column(DateTime)
    
    supporter = relationship('Supporter', foreign_keys=[supporter_id], back_populates='attendance_correction_requests')
    approver = relationship('Supporter', foreign_keys=[approver_id])