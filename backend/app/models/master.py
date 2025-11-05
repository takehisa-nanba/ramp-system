# backend/app/models/master.py

from app.extensions import db
from sqlalchemy.orm import relationship

# --- マスターテーブル群 ---

class RoleMaster(db.Model):
    # (変更なし)
    __tablename__ = 'role_master'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    supporters = db.relationship('Supporter', back_populates='role')

class StatusMaster(db.Model):
    # (変更なし)
    __tablename__ = 'status_master'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    
class AttendanceStatusMaster(db.Model):
    # (変更なし)
    __tablename__ = 'attendance_status_master'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    daily_logs = db.relationship('DailyLog', back_populates='attendance_status')

class ReferralSourceMaster(db.Model):
    # (変更なし)
    __tablename__ = 'referral_source_master'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

class EmploymentTypeMaster(db.Model):
    # (変更なし)
    __tablename__ = 'employment_type_master'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

class WorkStyleMaster(db.Model):
    # (変更なし)
    __tablename__ = 'work_style_master'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

class DisclosureTypeMaster(db.Model):
    # (変更なし)
    __tablename__ = 'disclosure_type_master'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

class ContactCategoryMaster(db.Model):
    # (変更なし)
    __tablename__ = 'contact_category_master'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    contacts = relationship('Contact', back_populates='category') 

class MeetingTypeMaster(db.Model):
    # (変更なし)
    __tablename__ = 'meeting_type_master'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

class ServiceLocationMaster(db.Model):
    # (変更なし)
    __tablename__ = 'service_location_master'
    id = db.Column(db.Integer, primary_key=True)
    location_name = db.Column(db.String(100), nullable=False, unique=True)
    is_offsite = db.Column(db.Boolean, default=False) 
    daily_logs = db.relationship('DailyLog', back_populates='service_location')

class AssessmentItemMaster(db.Model):
    __tablename__ = 'assessment_item_master'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    sub_category = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)

    ### ----------------------------------------------------
    ### 1. back_populates の名前を修正
    ### ----------------------------------------------------
    assessment_results = db.relationship('ReadinessAssessmentResult', back_populates='assessment_item')

class AssessmentScoreMaster(db.Model):
    # (変更なし)
    __tablename__ = 'assessment_score_master'
    id = db.Column(db.Integer, primary_key=True)
    score_value = db.Column(db.Integer, nullable=False, unique=True)
    score_text = db.Column(db.String(50), nullable=False, unique=True)
    is_active = db.Column(db.Boolean, default=True)
    ### plan.py の ReadinessAssessmentResult からのリレーションを受け取る (逆参照は任意)
    # assessment_results = db.relationship('ReadinessAssessmentResult', back_populates='assessment_score')

class CertificateTypeMaster(db.Model):
    # (変更なし)
    __tablename__ = 'certificate_type_master'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True) 
    is_active = db.Column(db.Boolean, default=True)

class AssessmentTypeMaster(db.Model):
    # (変更なし)
    __tablename__ = 'assessment_type_master'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    is_active = db.Column(db.Boolean, default=True)

class GenderLegalMaster(db.Model):
    # (変更なし)
    __tablename__ = 'gender_legal_master'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    is_active = db.Column(db.Boolean, default=True)

class DisabilityTypeMaster(db.Model):
    # (変更なし)
    __tablename__ = 'disability_type_master'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True) 
    is_active = db.Column(db.Boolean, default=True)

class MunicipalityMaster(db.Model):
    # (変更なし)
    __tablename__ = 'municipality_master'
    id = db.Column(db.Integer, primary_key=True)
    municipality_code = db.Column(db.String(20), nullable=False, unique=True, index=True) 
    name = db.Column(db.String(100), nullable=False) 
    is_active = db.Column(db.Boolean, default=True)
    certificates_issued_here = db.relationship('BeneficiaryCertificate', back_populates='billing_municipality')

class HistoryCategoryMaster(db.Model):
    # (変更なし)
    __tablename__ = 'history_category_master'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    is_active = db.Column(db.Boolean, default=True)
    history_items = db.relationship(
        'DevelopmentalHistoryItem',
        secondary='developmental_history_categories_association',
        back_populates='categories'
    )
    
class GovernmentOffice(db.Model):
    # (変更なし)
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
    # (変更なし)
    __tablename__ = 'service_templates'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    
    specific_goals = db.relationship('SpecificGoal', back_populates='template')

### ----------------------------------------------------
### 2. PreparationActivityMaster を追加 (audit_log.py から移動)
### ----------------------------------------------------
class PreparationActivityMaster(db.Model):
    __tablename__ = 'preparation_activity_master'
    id = db.Column(db.Integer, primary_key=True)
    activity_name = db.Column(db.String(150), nullable=False, unique=True)
    is_billable = db.Column(db.Boolean, nullable=False, default=False)
    
    daily_logs = db.relationship('DailyLog', back_populates='preparation_activity')

class FeePayerMaster(db.Model):
    __tablename__ = 'fee_payer_master'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True) # 例: '本人', '保護者', '自治体'
    is_active = db.Column(db.Boolean, default=True)

    # 逆参照: この費用負担者が関連する定着支援契約
    retention_contracts = db.relationship('JobRetentionContract', back_populates='fee_payer')

