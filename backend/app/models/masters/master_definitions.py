# 🚨 修正点: 'from app.extensions import db' を
# 3階層上の 'extensions.py' を指すように変更
from backend.app.extensions import db
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, Text, Numeric

# 🚨 修正点: rbac_links のインポートパスを相対パスに変更
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
    
    # Userモデルからの逆参照
    users = relationship('User', back_populates='status', lazy='dynamic') 

class DisabilityTypeMaster(db.Model):
    """障害の種別（精神、知的、身体など）"""
    __tablename__ = 'disability_type_master'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    
    # Userモデルからの逆参照
    users = relationship('UserPII', back_populates='disability_type', lazy='dynamic')

class GenderLegalMaster(db.Model):
    """戸籍上の性別（男性/女性）"""
    __tablename__ = 'gender_legal_master'
    id = Column(Integer, primary_key=True)
    name = Column(String(20), unique=True, nullable=False)

    # Userモデルからの逆参照
    users = relationship('UserPII', back_populates='gender_legal', lazy='dynamic')
    
class MunicipalityMaster(db.Model):
    """発行自治体情報（請求先コード、自治体名など）"""
    __tablename__ = 'municipality_master'
    id = Column(Integer, primary_key=True)
    municipality_code = Column(String(10), unique=True, nullable=False) # 行政が発行するコード
    name = Column(String(100), nullable=False)
    
    # ServiceCertificate, OfficeSettingからの逆参照
    certificates = relationship('ServiceCertificate', back_populates='issuance_municipality', lazy='dynamic')
    offices_located_here = relationship('OfficeSetting', back_populates='municipality_area', lazy='dynamic')
    
class JobTitleMaster(db.Model):
    """職員の行政上の職務・役職のマスターデータ"""
    __tablename__ = 'job_title_master'
    id = Column(Integer, primary_key=True)
    title_name = Column(String(100), unique=True, nullable=False) # 職務名（例: サービス管理責任者, 職業指導員）
    is_management_role = Column(Boolean, default=False) # 管理職フラグ (常勤換算の判断に影響)
    is_qualified_role = Column(Boolean, default=False) # 資格必須職務フラグ
    
    # SupporterJobAssignment, JobFilingRecordからの逆参照
    assignments = relationship('SupporterJobAssignment', back_populates='job_title', lazy='dynamic')
    filing_history = relationship('JobFilingRecord', back_populates='job_title', lazy='dynamic')

class ServiceTypeMaster(db.Model):
    """サービス種別（就労移行, B型など）と法定見直し頻度"""
    __tablename__ = 'service_type_master'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    service_code = Column(String(20), unique=True, nullable=False)
    required_review_months = Column(Integer) # 法令上の見直し頻度（3ヶ月, 6ヶ月など）
    
    # GrantedServiceからの逆参照
    granted_services = relationship('GrantedService', back_populates='service_type', lazy='dynamic')

class QualificationMaster(db.Model):
    """職員の保有資格（法令・民間）マスター"""
    __tablename__ = 'qualification_master'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    is_legal_mandate = Column(Boolean, default=False) # 法令上の必須資格か (例: サビ管研修修了)
    specialty_domain = Column(String(100)) # 得意分野タグ (例: 'デザイン', '相談支援')
    
    # SupporterQualificationからの逆参照
    supporter_qualifications = relationship('SupporterQualification', back_populates='qualification_master', lazy='dynamic')

class SkillMaster(db.Model):
    """利用者スキル（Excel, コミュニケーションなど）を定義するマスター"""
    __tablename__ = 'skill_master'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    
    # UserSkillからの逆参照
    user_skills = relationship('UserSkill', back_populates='skill_master', lazy='dynamic')

class TrainingPrerequisiteMaster(db.Model):
    """サビ管研修などの受講要件を法令に基づき定義（法令要件マップ）"""
    __tablename__ = 'training_prerequisite_master'
    id = Column(Integer, primary_key=True)
    job_title_id = Column(Integer, ForeignKey('job_title_master.id'))
    law_name = Column(String(100)) # 法的根拠
    law_article = Column(String(50)) # 該当条項
    effective_date = Column(Date) # このルールが有効になる日付

class DocumentTypeMaster(db.Model):
    """利用者/職員が提出する書類の種別マスター（履歴書、健康診断書など）"""
    __tablename__ = 'document_type_master'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False) # 例: 履歴書, 実務経験証明書, 委任状
    # ★ 機密フラグ (user_333での合意)
    is_confidential = Column(Boolean, default=False)
    
    # UserDocumentからの逆参照
    user_documents = relationship('UserDocument', back_populates='document_type_master', lazy='dynamic')
    
class CommitteeTypeMaster(db.Model):
    """委員会活動の種別マスター（虐待防止、感染予防など）"""
    __tablename__ = 'committee_type_master'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    required_frequency_months = Column(Integer) # 法令上の開催頻度（例: 12ヶ月に1回）
    
    # CommitteeActivityLogからの逆参照
    logs = relationship('CommitteeActivityLog', back_populates='committee_type', lazy='dynamic')

# ★ NEW: 研修種別マスタ (TrainingTypeMaster)
class TrainingTypeMaster(db.Model):
    """法定研修の種別マスター（虐待防止研修、感染症対策研修など）"""
    __tablename__ = 'training_type_master'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    required_frequency_months = Column(Integer) # 法令上の実施頻度
    
    # OfficeTrainingEventからの逆参照
    events = relationship('OfficeTrainingEvent', back_populates='training_type', lazy='dynamic')
    
class StaffActivityMaster(db.Model):
    """職員の就業時間内の活動種別マスター（請求業務、事務作業など）"""
    __tablename__ = 'staff_activity_master'
    id = Column(Integer, primary_key=True)
    activity_name = Column(String(100), nullable=False) # 例: 個別支援, 企業開拓, 事務作業, 休憩
    
    # StaffActivityAllocationLogからの逆参照
    logs = relationship('StaffActivityAllocationLog', back_populates='activity_type', lazy='dynamic')
    
class ProductMaster(db.Model):
    """A型・B型で提供する生産活動のアイテムマスター"""
    __tablename__ = 'product_master'
    id = Column(Integer, primary_key=True)
    product_name = Column(String(100), nullable=False)
    unit_of_measure = Column(String(20)) # 単位（例：個、セット、時間）
    standard_wage_rate = Column(Numeric(precision=10, scale=2)) # 標準工賃単価
    
    # DailyProductivityLogからの逆参照
    logs = relationship('DailyProductivityLog', back_populates='product', lazy='dynamic')
    
class VendorMaster(db.Model):
    """A型・B型の取引先企業（仕入先・販売先）"""
    __tablename__ = 'vendor_master'
    id = Column(Integer, primary_key=True)
    company_name = Column(String(255), nullable=False)
    industry_type = Column(String(100))
    contact_person = Column(String(100))
    
    # SalesInvoiceからの逆参照
    invoices = relationship('SalesInvoice', back_populates='vendor', lazy='dynamic')

# ====================================================================
# 4. RBAC (ロールと権限)
# ====================================================================
class RoleMaster(db.Model):
    """アクセス権限付与の単位となる役割（RBAC）"""
    __tablename__ = 'role_master'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)
    role_scope = Column(String(20), nullable=False) # JOB, CORPORATE, SYSTEM
    
    # --- 逆参照（M:N） ---
    # この役割を持つ職員
    supporters = relationship('Supporter', secondary=supporter_role_link, back_populates='roles')
    # この役割が持つ権限
    permissions = relationship('PermissionMaster', secondary=role_permission_link, back_populates='roles')

class PermissionMaster(db.Model):
    """システムのアクション権限の最小単位（RBAC）"""
    __tablename__ = 'permission_master'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True) # 例: APPROVE_LOG, VIEW_PII
    
    # --- 逆参照（M:N） ---
    # この権限を持つ役割
    roles = relationship('RoleMaster', secondary=role_permission_link, back_populates='permissions')