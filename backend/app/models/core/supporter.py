from backend.app.extensions import db, bcrypt
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, UniqueConstraint, Text, func
# RBAC連携テーブルをインポート
from backend.app.models.core.rbac_links import supporter_role_link

# ====================================================================
# 1. Supporter (職員情報 / 契約の責務)
# ====================================================================
class Supporter(db.Model):
    """
    職員（支援者）情報。
    契約情報(身分)と常勤換算の基礎(所定労働時間)を定義する。
    """
    __tablename__ = 'supporters'
    
    id = Column(Integer, primary_key=True)
    
    # --- A. 人事情報 (HRの責務) ---
    last_name = Column(String(50), nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name_kana = Column(String(50), nullable=False)
    first_name_kana = Column(String(50), nullable=False)
    
    hire_date = Column(Date, nullable=False) # 入社日 (監査証跡)
    retirement_date = Column(Date, nullable=True) # 退職日 (監査証跡)

    # --- B. 認証情報 (セキュリティの責務) ---
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(128))
    
    # --- C. 常勤換算の土台 (法令遵守の責務) ---
    # (例: 'FULL_TIME', 'SHORTENED_FT', 'PART_TIME')
    employment_type = Column(String(50), nullable=False) 
    # 個人の週所定労働時間（分）。常勤/非常勤の判定に使用
    weekly_scheduled_minutes = Column(Integer, nullable=False) 
    
    # --- D. 書類（証憑） ---
    employment_contract_url = Column(String(500)) # 雇用契約書URL
    resume_url = Column(String(500)) # 履歴書URL

    # --- リレーションシップ (子テーブル) ---
    timecards = relationship('SupporterTimecard', back_populates='supporter', lazy='dynamic', cascade="all, delete-orphan")
    job_assignments = relationship('SupporterJobAssignment', back_populates='supporter', lazy='dynamic', cascade="all, delete-orphan")
    qualifications = relationship('SupporterQualification', back_populates='supporter', lazy='dynamic', cascade="all, delete-orphan")
    
    # ★ RBAC（役割）へのリレーションシップ
    roles = relationship('RoleMaster', secondary=supporter_role_link, back_populates='supporters')
    
    # --- 逆参照 ---
    # Userへの逆参照 (User.primary_supporter)
    primary_users = relationship('User', back_populates='primary_supporter', lazy='dynamic')
    # OfficeSetting (core/office.py) からの逆参照
    owned_offices = relationship('OfficeSetting', back_populates='owner_supporter', foreign_keys='OfficeSetting.owner_supporter_id')
    managed_services = relationship('OfficeServiceConfiguration', back_populates='manager_supporter', foreign_keys='OfficeServiceConfiguration.manager_supporter_id')
    
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        if self.password_hash is None: return False
        return bcrypt.check_password_hash(self.password_hash, password)

# ====================================================================
# 2. SupporterTimecard (日々の勤怠 / みなし時間の責務)
# ====================================================================
class SupporterTimecard(db.Model):
    """職員の勤怠記録と常勤換算基礎データ（日次）"""
    __tablename__ = 'supporter_timecards'
    
    id = Column(Integer, primary_key=True)
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False, index=True)
    
    # ★「事業所間兼務」の有給按分のため、どのサービスでの勤怠かを紐づける
    office_service_configuration_id = Column(Integer, ForeignKey('office_service_configurations.id'), nullable=False, index=True)
    
    work_date = Column(Date, nullable=False)
    
    # --- 実績時間 ---
    check_in = Column(DateTime, nullable=True) # 打刻忘れ対応のためNULL許容
    check_out = Column(DateTime, nullable=True)
    total_break_minutes = Column(Integer, default=0, nullable=False) # 休憩時間の合計

    # --- 常勤換算と法令遵守（みなし時間） ---
    scheduled_work_minutes = Column(Integer, default=0, nullable=False) # その日の予定勤務時間（分）
    
    is_absent = Column(Boolean, default=False)
    # 休暇種別 (例: 'PAID_LEAVE', 'SICK_LEAVE', 'TRAINING', 'MATERNITY_LEAVE')
    absence_type = Column(String(50)) 
    # みなし時間（常勤換算に算入する時間、分）
    deemed_work_minutes = Column(Integer, default=0) 
    
    # 施設外支援・就労の担当時間（日次人員配置チェック用）
    facility_out_minutes = Column(Integer, default=0) 

    supporter = relationship('Supporter', back_populates='timecards')
    service_config = relationship('OfficeServiceConfiguration')


# ====================================================================
# 3. SupporterJobAssignment (職務割り当て / 兼務の責務)
# ====================================================================
class SupporterJobAssignment(db.Model):
    """職員の職務割り当て履歴（兼務割合と履歴管理）"""
    __tablename__ = 'supporter_job_assignments'
    
    id = Column(Integer, primary_key=True)
    
    # 誰が (Supporter)
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False, index=True)
    
    # どの職務を (JobTitleMaster)
    job_title_id = Column(Integer, ForeignKey('job_title_master.id'), nullable=False, index=True)
    
    # どのサービス（事業所番号）で (事業所間兼務の判定キー)
    office_service_configuration_id = Column(Integer, ForeignKey('office_service_configurations.id'), nullable=False, index=True)
    
    # いつから
    start_date = Column(Date, nullable=False)
    
    # いつまで (NULLの場合は現在も有効)
    end_date = Column(Date, nullable=True)
    
    # ★ 常勤換算割合の明示（兼務計算の基礎） ★
    assigned_minutes = Column(Integer, nullable=False) 
    
    # --- サビ管みなし配置の証跡（原理1） ---
    is_deemed_assignment = Column(Boolean, default=False) # 「みなし配置」であるフラグ
    deemed_document_url = Column(String(500)) # 根拠となる行政協議書URL
    deemed_expiry_date = Column(Date) # 「みなし」の有効期限
    
    # --- リレーションシップ ---
    supporter = relationship('Supporter', back_populates='job_assignments')
    job_title = relationship('JobTitleMaster', back_populates='assignments') 
    service_config = relationship('OfficeServiceConfiguration') 

    __table_args__ = (
        UniqueConstraint('supporter_id', 'job_title_id', 'start_date', 'office_service_configuration_id', name='uq_supporter_job_assignment'),
    )

# ====================================================================
# 4. SupporterQualification (保有資格 / 証憑の責務)
# ====================================================================
class SupporterQualification(db.Model):
    """
    職員の保有資格・スキル・実務経験証明書（監査証憑）。
    法令（守り）と得意分野（攻め）の両方を管理する。
    """
    __tablename__ = 'supporter_qualifications'
    
    id = Column(Integer, primary_key=True)
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False, index=True)
    
    # どの資格か (QualificationMasterを参照)
    qualification_master_id = Column(Integer, ForeignKey('qualification_master.id'), nullable=False)
    
    # --- 証憑としての必須情報（原理1） ---
    certification_date = Column(Date) # 取得日
    expiry_date = Column(Date) # 有効期限 (サビ管更新研修など)
    certificate_document_url = Column(String(500)) # 資格証・実務経験証明書のURL (証憑)
    
    # 支援の質向上（原理2）
    training_evaluation_score = Column(Integer) # 職員の得意分野としての評価
    
    supporter = relationship('Supporter', back_populates='qualifications')
    qualification_master = relationship('QualificationMaster', back_populates='supporter_qualifications')

# ====================================================================
# 5. AttendanceCorrectionRequest (勤怠修正ワークフローの責務)
# ====================================================================
class AttendanceCorrectionRequest(db.Model):
    """職員による勤怠修正申請のログ（監査証跡）"""
    # 🚨 利用者による申請(UserAttendanceCorrectionRequest)とは別モデル
    __tablename__ = 'supporter_attendance_correction_requests'
    
    id = Column(Integer, primary_key=True)
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False, index=True) # 申請者(または対象者)
    
    target_date = Column(Date, nullable=False) # 修正対象日
    record_type = Column(String(20), nullable=False) # 'CHECK_IN', 'CHECK_OUT', 'ABSENCE'
    requested_timestamp = Column(DateTime, nullable=False) # 修正希望時刻
    
    request_reason = Column(Text, nullable=False) # 申請理由 (NULL禁止)
    
    # PENDING, APPROVED, REJECTED
    request_status = Column(String(20), default='PENDING') 
    approver_id = Column(Integer, ForeignKey('supporters.id')) # 承認した職員
    processed_at = Column(DateTime)
    
    supporter = relationship('Supporter', foreign_keys=[supporter_id])
    approver = relationship('Supporter', foreign_keys=[approver_id])

# ====================================================================
# 6. StaffActivityAllocationLog (職員活動配分ログ / 生産性分析)
# ====================================================================
class StaffActivityAllocationLog(db.Model):
    """
    職員の日次の活動時間配分（支援、事務、移動など）。
    業務改善（ムダ取り）の基礎データとなる。
    """
    __tablename__ = 'staff_activity_allocation_logs'
    
    id = Column(Integer, primary_key=True)
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False, index=True)
    
    activity_date = Column(Date, nullable=False)
    
    # どの活動か (masters/master_definitions.py の StaffActivityMaster を参照)
    staff_activity_master_id = Column(Integer, ForeignKey('staff_activity_master.id'), nullable=False)
    
    allocated_minutes = Column(Integer, nullable=False) # 時間（分）
    
    # --- リレーションシップ ---
    supporter = relationship('Supporter')
    activity_type = relationship('StaffActivityMaster', back_populates='logs')