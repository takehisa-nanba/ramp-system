# backend/app/models/office_admin.py

from datetime import datetime
from app.extensions import db
from sqlalchemy.orm import relationship

# ----------------------------------------------------
# 1. Corporation (法人情報)
# ----------------------------------------------------
class Corporation(db.Model):
    __tablename__ = 'corporations'
    
    id = db.Column(db.Integer, primary_key=True)
    corporation_name = db.Column(db.String(150), nullable=False) # 法人名
    corporation_type = db.Column(db.String(50), nullable=False) # 法人格
    
    representative_name = db.Column(db.String(100), nullable=True) # 代表者名
    corporation_number = db.Column(db.String(20), unique=True, nullable=True) # 法人番号
    
    # 本社所在地
    postal_code = db.Column(db.String(10), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    
    # ★ 新規追加: 法人印（丸印）の画像URL
    corporation_seal_image_url = db.Column(db.String(500), nullable=True)
    
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # リレーションシップ (法人は複数の事業所を持つ)
    offices = db.relationship('OfficeSetting', back_populates='corporation', lazy=True)


# ----------------------------------------------------
# 2. OfficeSetting (事業所基本情報)
# ----------------------------------------------------
class OfficeSetting(db.Model):
    __tablename__ = 'office_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    corporation_id = db.Column(db.Integer, db.ForeignKey('corporations.id'), nullable=False)
    
    office_name = db.Column(db.String(100), nullable=False)
    
    # 所在地情報
    municipality_id = db.Column(db.Integer, db.ForeignKey('municipality_master.id'), nullable=False)
    
    # 管理者情報
    owner_supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=False) # 経営責任者
    
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # ★ 新規追加: 事業所印（角印）の画像URL
    office_seal_image_url = db.Column(db.String(500), nullable=True)
    
    # リレーションシップ
    corporation = db.relationship('Corporation', back_populates='offices')
    municipality = db.relationship('MunicipalityMaster')
    owner_supporter = db.relationship('Supporter')
    
    # 多機能型対応: サービス設定へのリレーション
    service_configs = db.relationship('OfficeServiceConfiguration', back_populates='office', lazy=True)
    additive_filings = db.relationship('OfficeAdditiveFiling', back_populates='office', lazy=True)
    fee_decisions = db.relationship('FeeCalculationDecision', back_populates='office', lazy=True)


# ----------------------------------------------------
# 3. OfficeServiceConfiguration (多機能型サービス設定)
# ----------------------------------------------------
class OfficeServiceConfiguration(db.Model):
    # (変更なし)
    __tablename__ = 'office_service_configurations'
    id = db.Column(db.Integer, primary_key=True)
    office_id = db.Column(db.Integer, db.ForeignKey('office_settings.id'), nullable=False)
    service_type = db.Column(db.String(50), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    service_provider_number = db.Column(db.String(20), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    office = db.relationship('OfficeSetting', back_populates='service_configs')
    
    
# ----------------------------------------------------
# 4. OfficeAdditiveFiling (加算届出状況)
# ----------------------------------------------------
class OfficeAdditiveFiling(db.Model):
    # (変更なし)
    __tablename__ = 'office_additive_filings'
    id = db.Column(db.Integer, primary_key=True)
    office_id = db.Column(db.Integer, db.ForeignKey('office_settings.id'), nullable=False)
    fee_master_id = db.Column(db.Integer, db.ForeignKey('government_fee_master.id'), nullable=False)
    is_filed = db.Column(db.Boolean, default=False, nullable=False)
    filing_date = db.Column(db.Date)
    effective_start_date = db.Column(db.Date)
    office = db.relationship('OfficeSetting', back_populates='additive_filings')
    fee_master = db.relationship('GovernmentFeeMaster')


# ----------------------------------------------------
# 5. FeeCalculationDecision (算定意思決定)
# ----------------------------------------------------
class FeeCalculationDecision(db.Model):
    # (変更なし)
    __tablename__ = 'fee_calculation_decisions'
    id = db.Column(db.Integer, primary_key=True)
    office_id = db.Column(db.Integer, db.ForeignKey('office_settings.id'), nullable=False)
    fee_master_id = db.Column(db.Integer, db.ForeignKey('government_fee_master.id'), nullable=False)
    calculation_month = db.Column(db.Date, nullable=False)
    is_calculated = db.Column(db.Boolean, default=True, nullable=False)
    supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=False)
    decision_timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    office = db.relationship('OfficeSetting', back_populates='fee_decisions')
    fee_master = db.relationship('GovernmentFeeMaster')
    supporter = db.relationship('Supporter')
    