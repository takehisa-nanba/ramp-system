# app/models/master.py

from app.extensions import db
from sqlalchemy.orm import relationship

# --- マスターテーブル群 ---

class RoleMaster(db.Model):
    __tablename__ = 'role_master'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    
    # リレーションシップ（逆参照）
    supporters = db.relationship('Supporter', back_populates='role') # Supporter.role_id から参照

class StatusMaster(db.Model):
    __tablename__ = 'status_master'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    # prospect, user, plan などの分類
    category = db.Column(db.String(50), nullable=False) 
    name = db.Column(db.String(50), nullable=False)
    
    # リレーションシップ（逆参照）
    # User.status_id, Prospect.status_id, SupportPlan.status_id から参照される

class AttendanceStatusMaster(db.Model):
    __tablename__ = 'attendance_status_master'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False) # 通所, 欠席, 午前休, など
    
    # リレーションシップ（逆参照）
    daily_logs = db.relationship('DailyLog', back_populates='attendance_status') # DailyLog.attendance_status_id から参照

class ReferralSourceMaster(db.Model):
    __tablename__ = 'referral_source_master'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    
    # リレーションシップ（逆参照）
    # Prospect.referral_source_id から参照される

class EmploymentTypeMaster(db.Model):
    __tablename__ = 'employment_type_master'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

class WorkStyleMaster(db.Model):
    __tablename__ = 'work_style_master'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

class DisclosureTypeMaster(db.Model):
    __tablename__ = 'disclosure_type_master'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

class ContactCategoryMaster(db.Model):
    __tablename__ = 'contact_category_master'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

    # リレーションシップ (Contact からの逆参照)
    contacts = relationship('Contact', back_populates='category') 

class MeetingTypeMaster(db.Model):
    __tablename__ = 'meeting_type_master'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

class ServiceLocationMaster(db.Model):
    __tablename__ = 'service_location_master'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    location_name = db.Column(db.String(100), nullable=False, unique=True)
    is_offsite = db.Column(db.Boolean, default=False) # 施設外支援フラグ
    
    # リレーションシップ（逆参照）
    daily_logs = db.relationship('DailyLog', back_populates='service_location') # DailyLog.location_id から参照

class AssessmentItemMaster(db.Model):
    """
    就労準備性アセスメントの「項目」マスタ
    (例: '1. 健康管理', '(1)体調管理', '体調を...')
    """
    __tablename__ = 'assessment_item_master'
    __table_args__ = ({"extend_existing": True},)
    
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    sub_category = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)

    # 逆参照
    assessment_results = db.relationship('ReadinessAssessmentResult', back_populates='item')

class AssessmentScoreMaster(db.Model):
    """
    アセスメントの「4段階評価」マスタ
    (例: 4, 'できる')
    """
    __tablename__ = 'assessment_score_master'
    __table_args__ = ({"extend_existing": True},)
    
    id = db.Column(db.Integer, primary_key=True)
    score_value = db.Column(db.Integer, nullable=False, unique=True)
    score_text = db.Column(db.String(50), nullable=False, unique=True)
    is_active = db.Column(db.Boolean, default=True)

class CertificateTypeMaster(db.Model):
    """ 受給者証種別マスタ """
    __tablename__ = 'certificate_type_master'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True) # 例: '障害福祉サービス受給者証'
    is_active = db.Column(db.Boolean, default=True)

class AssessmentTypeMaster(db.Model):
    """ 汎用アセスメント種別マスタ """
    __tablename__ = 'assessment_type_master'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True) # 例: '初期アセスメント'
    is_active = db.Column(db.Boolean, default=True)

class GenderLegalMaster(db.Model):
    """
    公的書類上の性別マスタ (user.py から参照)
    """
    __tablename__ = 'gender_legal_master'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True) # 例: '男性', '女性', 'その他'
    is_active = db.Column(db.Boolean, default=True)

class DisabilityTypeMaster(db.Model):
    """
    障害種別マスタ (user.py から参照)
    """
    __tablename__ = 'disability_type_master'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True) # 例: '身体障害', '知的障害', '精神障害'
    is_active = db.Column(db.Boolean, default=True)

class CertificateTypeMaster(db.Model):
    """
    受給者証種別マスタ (compliance.py から参照)
    """
    __tablename__ = 'certificate_type_master'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True) # 例: '障害福祉サービス受給者証'
    is_active = db.Column(db.Boolean, default=True)

class MunicipalityMaster(db.Model):
    """
    市区町村コードマスタ (compliance.py から参照)
    """
    __tablename__ = 'municipality_master'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    municipality_code = db.Column(db.String(20), nullable=False, unique=True, index=True) # 例: '221309'
    name = db.Column(db.String(100), nullable=False) # 例: '浜松市'
    is_active = db.Column(db.Boolean, default=True)
    # 逆参照
    certificates_issued_here = db.relationship('Certificate', back_populates='billing_municipality')

class HistoryCategoryMaster(db.Model):
    """
    成育歴の「カテゴリ」マスタ (profile.py から参照)
    """
    __tablename__ = 'history_category_master'
    __table_args__ = ({"extend_existing": True},)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True) # 例: '学歴', '職歴', '病歴'
    is_active = db.Column(db.Boolean, default=True)
    # 逆参照
    history_items = db.relationship(
        'DevelopmentalHistoryItem',
        secondary='developmental_history_categories_association',
        back_populates='categories'
    )