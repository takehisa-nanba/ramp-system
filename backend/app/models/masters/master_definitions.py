# backend/app/models/masters/master_definitions.py

# 修正点: 'from backend.app.extensions' (絶対参照)
from backend.app.extensions import db
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, Text, Numeric, DateTime
from sqlalchemy.sql import func

#  修正点: 'backend.app.models.core.rbac_links' (絶対参照)
from backend.app.models.core.rbac_links import supporter_role_link, role_permission_link

# ====================================================================
# 法令上の定義と分類
# ====================================================================

class StatusMaster(db.Model):
    """利用者のステータス（利用中、相談中、利用終了など）"""
    __tablename__ = 'status_master'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    sort_order = Column(Integer, default=0)
    users = db.relationship('User', back_populates='status', lazy='dynamic') 

class DisabilityTypeMaster(db.Model):
    """障害の種別（精神、知的、身体など）"""
    __tablename__ = 'disability_type_master'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    # 参照先はUserPII
    users = db.relationship('UserPII', back_populates='disability_type', lazy='dynamic')

class GenderLegalMaster(db.Model):
    """戸籍上の性別（男性/女性）"""
    __tablename__ = 'gender_legal_master'
    id = Column(Integer, primary_key=True)
    name = Column(String(20), unique=True, nullable=False)
    # 参照先はUserPII
    users = db.relationship('UserPII', back_populates='gender_legal', lazy='dynamic')
    
class MunicipalityMaster(db.Model):
    """発行自治体情報（請求先コード、自治体名など）"""
    __tablename__ = 'municipality_master'
    id = Column(Integer, primary_key=True)
    municipality_code = Column(String(10), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    certificates = db.relationship('ServiceCertificate', back_populates='issuance_municipality', lazy='dynamic')
    offices_located_here = db.relationship('OfficeSetting', back_populates='municipality_area', lazy='dynamic')
    
class JobTitleMaster(db.Model):
    """職員の行政上の職務・役職のマスターデータ"""
    __tablename__ = 'job_title_master'
    id = Column(Integer, primary_key=True)
    title_name = Column(String(100), unique=True, nullable=False) # 例: サービス管理責任者
    is_management_role = Column(Boolean, default=False) # 管理職フラグ
    is_qualified_role = Column(Boolean, default=False) # 資格必須職務フラグ
    assignments = db.relationship('SupporterJobAssignment', back_populates='job_title', lazy='dynamic')
    filing_history = db.relationship('JobFilingRecord', back_populates='job_title', lazy='dynamic')

class ServiceTypeMaster(db.Model):
    """サービス種別（就労移行, B型など）と法定見直し頻度"""
    __tablename__ = 'service_type_master'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    service_code = Column(String(20), unique=True, nullable=False)
    required_review_months = Column(Integer)
    granted_services = db.relationship('GrantedService', back_populates='service_type', lazy='dynamic')

class QualificationMaster(db.Model):
    """職員の保有資格（法令・民間）マスター"""
    __tablename__ = 'qualification_master'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    is_legal_mandate = Column(Boolean, default=False) # 法令上の必須資格か
    specialty_domain = Column(String(100)) # 得意分野タグ
    supporter_qualifications = db.relationship('SupporterQualification', back_populates='qualification_master', lazy='dynamic')

class SkillMaster(db.Model):
    """利用者スキル（Excel, コミュニケーションなど）を定義するマスター"""
    __tablename__ = 'skill_master'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    user_skills = db.relationship('UserSkill', back_populates='skill_master', lazy='dynamic')

class TrainingPrerequisiteMaster(db.Model):
    """サビ管研修などの受講要件を法令に基づき定義（法令要件マップ）"""
    __tablename__ = 'training_prerequisite_master'
    id = Column(Integer, primary_key=True)
    job_title_id = Column(Integer, ForeignKey('job_title_master.id'))
    law_name = Column(String(100)) # 法的根拠
    law_article = Column(String(50)) # 該当条項
    effective_date = Column(Date) # 有効日

class DocumentTypeMaster(db.Model):
    """利用者/職員が提出する書類の種別マスター（履歴書、健康診断書など）"""
    __tablename__ = 'document_type_master'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False) # 例: 履歴書, 実務経験証明書, 委任状
    # ★ 機密フラグ (原理6: 受給者証写し等の保護)
    is_confidential = Column(Boolean, default=False)
    user_documents = db.relationship('UserDocument', back_populates='document_type_master', lazy='dynamic')
    
class CommitteeTypeMaster(db.Model):
    """委員会活動の種別マスター（虐待防止、感染予防など）"""
    __tablename__ = 'committee_type_master'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    required_frequency_months = Column(Integer) # 法令上の開催頻度
    logs = db.relationship('CommitteeActivityLog', back_populates='committee_type', lazy='dynamic')

# ★ NEW: 研修・訓練種別マスタ (TrainingTypeMaster)
class TrainingTypeMaster(db.Model):
    """法定研修・訓練の種別マスター（虐待防止研修、避難訓練など）"""
    __tablename__ = 'training_type_master'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    required_frequency_months = Column(Integer) # 法令上の実施頻度
    events = db.relationship('OfficeTrainingEvent', back_populates='training_type', lazy='dynamic')

# ★ NEW: 失敗原因マスタ (FailureFactorMaster) - 失敗の財産化
class FailureFactorMaster(db.Model):
    """生産活動の失敗原因を分類するマスター（個人、環境、指導など）"""
    __tablename__ = 'failure_factor_master'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True) # 例: 個人要因, 環境要因, 指導要因
    description = Column(Text)
    productivity_logs = db.relationship('DailyProductivityLog', back_populates='failure_factor', lazy='dynamic')
    daily_logs = db.relationship('DailyLog', back_populates='failure_factor', lazy='dynamic')
    
# ★ NEW: 問題の所在マスタ (IssueCategoryMaster) - ナレッジ共有用
class IssueCategoryMaster(db.Model):
    """スレッドや日報の問題の所在（タグ）"""
    __tablename__ = 'issue_category_master'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True) # 例: 本人因子, 環境因子
    # SupportThreadやIncidentReportからの逆参照を想定(Many-to-Many)

class ServiceUnitMaster(db.Model):
    """
    サービスの請求単位と単価を定義するマスタ。
    追記型台帳モデルを採用し、遡及変更を禁止する（不変性）。
    """
    __tablename__ = 'service_unit_master'
    id = Column(Integer, primary_key=True)
    
    service_type = Column(String(50), nullable=False) 
    unit_count = Column(Integer, default=0)       
    unit_price = Column(Numeric(10, 4), default=0.0)
    
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    
    # トレーサビリティの強制
    responsible_id = Column(Integer, nullable=False) 
    commit_timestamp = Column(DateTime, default=func.now(), nullable=False)

# ★ NEW: 報酬・加算マスタ (GovernmentFeeMaster) - 3階層フィルター
class GovernmentFeeMaster(db.Model):
    """
    障害福祉サービスの報酬・加算・減算の定義マスタ。
    「3階層フィルター」の制御ルールをここに集約する。
    """
    __tablename__ = 'government_fee_master'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False) # 例: 送迎加算(I), 初期加算
    code = Column(String(20), unique=True, nullable=False) # 請求コード
    category = Column(String(20), nullable=False) # BASE, ADD, SUB
    units = Column(Integer, default=0)
    
    # 3階層フィルター制御フラグ
    needs_office_filing = Column(Boolean, default=False)
    needs_user_eligibility = Column(Boolean, default=False)
    needs_daily_logs = Column(Boolean, default=False)
    
    # 計算タイプ (ADD_TO_BASE, PER_ACTION, SUBTRACTION)
    calculation_type = Column(String(20), nullable=False)
    logic_key = Column(String(50)) 
    
    office_filings = db.relationship('OfficeAdditiveFiling', back_populates='fee_master', lazy='dynamic')


class StaffActivityMaster(db.Model):
    """職員の就業時間内の活動種別マスター（請求業務、事務作業など）"""
    __tablename__ = 'staff_activity_master'
    id = Column(Integer, primary_key=True)
    activity_name = Column(String(100), nullable=False) # 例: 個別支援, 企業開拓, 事務作業, 休憩
    logs = db.relationship('StaffActivityAllocationLog', back_populates='activity_type', lazy='dynamic')
    
class ProductMaster(db.Model):
    """A型・B型で提供する生産活動のアイテムマスター"""
    __tablename__ = 'product_master'
    id = Column(Integer, primary_key=True)
    product_name = Column(String(100), nullable=False)
    unit_of_measure = Column(String(20)) # 単位（例：個、セット、時間）
    standard_wage_rate = Column(Numeric(precision=10, scale=2)) # 標準工賃単価
    logs = db.relationship('DailyProductivityLog', back_populates='product', lazy='dynamic')
    
class VendorMaster(db.Model):
    """A型・B型の取引先企業（仕入先・販売先）"""
    __tablename__ = 'vendor_master'
    id = Column(Integer, primary_key=True)
    company_name = Column(String(255), nullable=False)
    industry_type = Column(String(100))
    contact_person = Column(String(100))
    invoices = db.relationship('SalesInvoice', back_populates='vendor', lazy='dynamic')

# ====================================================================
# 4. RBAC (ロールと権限)
# ====================================================================
class RoleMaster(db.Model):
    """アクセス権限付与の単位となる役割（RBAC）"""
    __tablename__ = 'role_master'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)
    role_scope = Column(String(20), nullable=False) # JOB, CORPORATE, SYSTEM
    sort_order = Column(Integer, default=0)
    supporters = db.relationship('Supporter', secondary=supporter_role_link, back_populates='roles')
    permissions = db.relationship('PermissionMaster', secondary=role_permission_link, back_populates='roles')

class PermissionMaster(db.Model):
    """システムのアクション権限の最小単位（RBAC）"""
    __tablename__ = 'permission_master'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True) # 例: APPROVE_LOG, VIEW_PII
    roles = db.relationship('RoleMaster', secondary=role_permission_link, back_populates='permissions')