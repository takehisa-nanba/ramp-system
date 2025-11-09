# backend/app/models/client_relations.py

from datetime import datetime
from app.extensions import db
from sqlalchemy.orm import relationship
from sqlalchemy import UniqueConstraint

# ----------------------------------------------------
# 1. EmergencyContact Model (緊急連絡先)
# ----------------------------------------------------
class EmergencyContact(db.Model):
    __tablename__ = 'emergency_contacts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    full_name = db.Column(db.String(100), nullable=False)
    relationship = db.Column(db.String(50), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    note = db.Column(db.Text)
    
    
# ----------------------------------------------------
# 2. MedicalInstitution Model (医療機関・連携先)
# ----------------------------------------------------
class MedicalInstitution(db.Model):
    __tablename__ = 'medical_institutions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    institution_type = db.Column(db.String(50), nullable=False) # 医療機関, 相談事業所など
    institution_name = db.Column(db.String(100), nullable=False)
    doctor_name = db.Column(db.String(100)) # 主治医/担当者名
    phone_number = db.Column(db.String(20))
    visit_frequency = db.Column(db.String(50)) # 通院頻度
    medication_details = db.Column(db.Text)
    note = db.Column(db.Text)


# ----------------------------------------------------
# 3. BeneficiaryCertificate Model (受給者証情報 - 親テーブル)
# ----------------------------------------------------
class BeneficiaryCertificate(db.Model):
    __tablename__ = 'beneficiary_certificates'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    certificate_number = db.Column(db.String(30), nullable=False)
    is_current = db.Column(db.Boolean, default=True, nullable=False)
    issue_date = db.Column(db.Date, nullable=False)
    
    # 請求関連情報（全て必須）
    billing_municipality_id = db.Column(db.Integer, db.ForeignKey('municipality_master.id'), nullable=False)
    contract_office_number = db.Column(db.String(20), nullable=False) # 事業所記載番号
    disability_classification = db.Column(db.String(10), nullable=False) # 障害支援区分 (例: 区分3)

    # リレーションシップ (期間と数量はすべて子テーブルに分離)
    provision_periods = db.relationship('ServiceProvisionPeriod', back_populates='certificate', lazy=True)
    unit_periods = db.relationship('ServiceUnitPeriod', back_populates='certificate', lazy=True)
    limit_periods = db.relationship('CopaymentLimitPeriod', back_populates='certificate', lazy=True)
    provisional_periods = db.relationship('ProvisionalServicePeriod', back_populates='certificate', lazy=True)
    # --- ★ ここに以下の1行を追加 ★ ---
    billing_municipality = db.relationship('MunicipalityMaster', back_populates='certificates_issued_here')
    # --- ★ 追加ここまで ★ ---


# ----------------------------------------------------
# 4. ServiceProvisionPeriod (サービス支給決定期間)
# ----------------------------------------------------
class ServiceProvisionPeriod(db.Model):
    __tablename__ = 'service_provision_periods'
    id = db.Column(db.Integer, primary_key=True)
    certificate_id = db.Column(db.Integer, db.ForeignKey('beneficiary_certificates.id'), nullable=False)

    service_type = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False) # 原則期間の定めは必須
    
    certificate = db.relationship('BeneficiaryCertificate', back_populates='provision_periods')


# ----------------------------------------------------
# 5. ServiceUnitPeriod (支給決定量・日数)
# ----------------------------------------------------
class ServiceUnitPeriod(db.Model):
    __tablename__ = 'service_unit_periods'
    id = db.Column(db.Integer, primary_key=True)
    certificate_id = db.Column(db.Integer, db.ForeignKey('beneficiary_certificates.id'), nullable=False)

    daily_units_per_month = db.Column(db.Integer, nullable=False) # 月間の支給決定日数
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    certificate = db.relationship('BeneficiaryCertificate', back_populates='unit_periods')


# ----------------------------------------------------
# 6. CopaymentLimitPeriod (自己負担上限額適用期間)
# ----------------------------------------------------
class CopaymentLimitPeriod(db.Model):
    __tablename__ = 'copayment_limit_periods'
    id = db.Column(db.Integer, primary_key=True)
    certificate_id = db.Column(db.Integer, db.ForeignKey('beneficiary_certificates.id'), nullable=False)

    copayment_limit = db.Column(db.Integer, nullable=False) # 月額自己負担上限額
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False) # 適用終了日

    certificate = db.relationship('BeneficiaryCertificate', back_populates='limit_periods')


# ----------------------------------------------------
# 7. ProvisionalServicePeriod (暫定支給期間)
# ----------------------------------------------------
class ProvisionalServicePeriod(db.Model):
    __tablename__ = 'provisional_service_periods'
    id = db.Column(db.Integer, primary_key=True)
    certificate_id = db.Column(db.Integer, db.ForeignKey('beneficiary_certificates.id'), nullable=False)

    service_type = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    assessment_date = db.Column(db.Date) # 本アセスメント予定日

    certificate = db.relationship('BeneficiaryCertificate', back_populates='provisional_periods')
