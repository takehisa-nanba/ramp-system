# backend/app/models/master.py

from app.extensions import db
from sqlalchemy.orm import relationship

# --- 1. システム運用ロール ---
class RoleMaster(db.Model):
    __tablename__ = 'role_master'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True) #例: 'SystemAdmin', 'OfficeAdmin', 'Staff'
    
    supporters = db.relationship('Supporter', back_populates='role')

# --- 2. 法令上/組織上の職務マスタ (★ 新規追加 ★) ---
class JobTitleMaster(db.Model):
    __tablename__ = 'job_title_master'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True) #例: '生活支援員', '就労支援員', '経営者', '課長'
    
    # 'LEGAL' (法令上の職務) or 'ORG' (組織上の役職)
    job_type = db.Column(db.String(50), nullable=False, default='LEGAL')
    
    # Trueなら加配要件などに関わる、簡単に変更できない職務
    is_compliance_role = db.Column(db.Boolean, default=False, nullable=False)
    
    # この職務を割り当てられている全履歴
    assignments = db.relationship('SupporterJobAssignment', back_populates='job_title')

# --- 3. その他、既存のマスター ---
class StatusMaster(db.Model):
    __tablename__ = 'status_master'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False) #例: 'user', 'plan'
    name = db.Column(db.String(50), nullable=False) #例: '新規問合せ', '利用中', 'Draft'
    
class AttendanceStatusMaster(db.Model):
    __tablename__ = 'attendance_status_master'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False) #例: '通所', '欠席'
    
    daily_logs = db.relationship('DailyLog', back_populates='attendance_status')

class ReferralSourceMaster(db.Model):
    __tablename__ = 'referral_source_master'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

class EmploymentTypeMaster(db.Model):
    __tablename__ = 'employment_type_master'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

class WorkStyleMaster(db.Model):
    __tablename__ = 'work_style_master'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

class DisclosureTypeMaster(db.Model):
    __tablename__ = 'disclosure_type_master'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

class ContactCategoryMaster(db.Model):
    __tablename__ = 'contact_category_master'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

    contacts = relationship('Contact', back_populates='category') 

class MeetingTypeMaster(db.Model):
    __tablename__ = 'meeting_type_master'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

# --- ★ 修正: 支援場所マスタ (フラグ・契約書URL追加) ---
class ServiceLocationMaster(db.Model):
    __tablename__ = 'service_location_master'
    
    id = db.Column(db.Integer, primary_key=True)
    location_name = db.Column(db.String(100), nullable=False, unique=True)
    
    # フラグ（分類）
    is_offsite = db.Column(db.Boolean, default=False, nullable=False) # True=施設外
    is_offsite_work_location = db.Column(db.Boolean, default=False, nullable=False) # True=施設外就労
    
    # 証憑（契約書）
    contract_document_url = db.Column(db.String(500), nullable=True) # S3などへのリンク
    contract_start_date = db.Column(db.Date, nullable=True)
    contract_end_date = db.Column(db.Date, nullable=True)
    
    # 逆参照リレーション
    daily_logs = db.relationship('DailyLog', back_populates='service_location')
    service_records = db.relationship('ServiceRecord', back_populates='service_location')
    schedules = db.relationship('Schedule', back_populates='service_location')

class AssessmentItemMaster(db.Model):
    __tablename__ = 'assessment_item_master'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    sub_category = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)

    assessment_results = db.relationship('ReadinessAssessmentResult', back_populates='assessment_item')
    pre_enrollment_assessment_scores = db.relationship('PreEnrollmentAssessmentScore', back_populates='assessment_item')

class AssessmentScoreMaster(db.Model):
    __tablename__ = 'assessment_score_master'
    id = db.Column(db.Integer, primary_key=True)
    score_value = db.Column(db.Integer, nullable=False, unique=True)
    score_text = db.Column(db.String(50), nullable=False, unique=True)
    is_active = db.Column(db.Boolean, default=True)
    
    readiness_assessment_results = db.relationship('ReadinessAssessmentResult', back_populates='assessment_score')

class CertificateTypeMaster(db.Model):
    __tablename__ = 'certificate_type_master'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True) 
    is_active = db.Column(db.Boolean, default=True)

class AssessmentTypeMaster(db.Model):
    __tablename__ = 'assessment_type_master'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    is_active = db.Column(db.Boolean, default=True)

class GenderLegalMaster(db.Model):
    __tablename__ = 'gender_legal_master'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    is_active = db.Column(db.Boolean, default=True)

class DisabilityTypeMaster(db.Model):
    __tablename__ = 'disability_type_master'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True) 
    is_active = db.Column(db.Boolean, default=True)
    
    users = db.relationship('User', back_populates='disability_type')

class MunicipalityMaster(db.Model):
    __tablename__ = 'municipality_master'
    id = db.Column(db.Integer, primary_key=True)
    municipality_code = db.Column(db.String(20), nullable=False, unique=True, index=True) 
    name = db.Column(db.String(100), nullable=False) 
    is_active = db.Column(db.Boolean, default=True)
    
    certificates_issued_here = db.relationship('BeneficiaryCertificate', back_populates='billing_municipality')
    offices_located_here = db.relationship('OfficeSetting', back_populates='municipality')

class HistoryCategoryMaster(db.Model):
    __tablename__ = 'history_category_master'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    is_active = db.Column(db.Boolean, default=True)
    
    # history_items = db.relationship(
    #     'DevelopmentalHistoryItem',
    #     secondary='developmental_history_categories_association',
    #     back_populates='categories'
    # )

# --- (audit_log.py から移動してきたマスター) ---

class GovernmentOffice(db.Model):
    __tablename__ = 'government_offices'
    id = db.Column(db.Integer, primary_key=True)
    office_name = db.Column(db.String(100), nullable=False, unique=True)
    office_type = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(255))
    phone_number = db.Column(db.String(20))
    email = db.Column(db.String(120))
    remarks = db.Column(db.Text)
    
    contacts = relationship('Contact', back_populates='government_office')

class ServiceTemplate(db.Model):
    __tablename__ = 'service_templates'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    
    specific_goals = db.relationship('SpecificGoal', back_populates='template')

class PreparationActivityMaster(db.Model):
    __tablename__ = 'preparation_activity_master'
    id = db.Column(db.Integer, primary_key=True)
    activity_name = db.Column(db.String(150), nullable=False, unique=True)
    is_billable = db.Column(db.Boolean, nullable=False, default=False)
    
    daily_logs = db.relationship('DailyLog', back_populates='preparation_activity')

# --- (retention.py からの要求で追加したマスター) ---

class FeePayerMaster(db.Model):
    __tablename__ = 'fee_payer_master'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    is_active = db.Column(db.Boolean, default=True)
    
    retention_contracts = db.relationship('JobRetentionContract', back_populates='fee_payer')
