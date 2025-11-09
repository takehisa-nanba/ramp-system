# backend/app/models/office_admin.py

from datetime import datetime
from app.extensions import db
from sqlalchemy.orm import relationship
from sqlalchemy import JSON

# ----------------------------------------------------
# 1. Corporation (法人情報)
# ----------------------------------------------------
class Corporation(db.Model):
    __tablename__ = 'corporations'
    
    id = db.Column(db.Integer, primary_key=True)
    corporation_name = db.Column(db.String(150), nullable=False)
    corporation_type = db.Column(db.String(50), nullable=False)
    representative_name = db.Column(db.String(100), nullable=True)
    corporation_number = db.Column(db.String(20), unique=True, nullable=True)
    postal_code = db.Column(db.String(10), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    corporation_seal_image_url = db.Column(db.String(500), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    offices = db.relationship('OfficeSetting', back_populates='corporation', lazy=True)

# ----------------------------------------------------
# 2. OfficeSetting (事業所基本情報)
# ----------------------------------------------------
class OfficeSetting(db.Model):
    __tablename__ = 'office_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    corporation_id = db.Column(db.Integer, db.ForeignKey('corporations.id'), nullable=False)
    office_name = db.Column(db.String(100), nullable=False)
    municipality_id = db.Column(db.Integer, db.ForeignKey('municipality_master.id'), nullable=False)
    owner_supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    office_seal_image_url = db.Column(db.String(500), nullable=True)
    
    # --- ★ ここに「ローカルルール」設定を追加 ★ ---
    local_rules_config = db.Column(db.JSON, nullable=True) 
    
    # --- リレーションシップ ---
    corporation = db.relationship('Corporation', back_populates='offices')
    municipality = db.relationship('MunicipalityMaster', back_populates='offices_located_here')
    owner_supporter = db.relationship('Supporter', foreign_keys=[owner_supporter_id], back_populates='owned_offices')
    staff_members = db.relationship('Supporter', foreign_keys='[Supporter.office_id]', back_populates='office')

    service_configs = db.relationship('OfficeServiceConfiguration', back_populates='office', lazy=True)
    additive_filings = db.relationship('OfficeAdditiveFiling', back_populates='office', lazy=True)
    fee_decisions = db.relationship('FeeCalculationDecision', back_populates='office', lazy=True)

# ----------------------------------------------------
# 3. OfficeServiceConfiguration (多機能型サービス設定)
# ----------------------------------------------------
class OfficeServiceConfiguration(db.Model):
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
