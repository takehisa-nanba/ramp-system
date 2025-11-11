# backend/app/models/retention.py

from datetime import datetime
from app.extensions import db
from sqlalchemy.orm import relationship
from sqlalchemy import UniqueConstraint

# ----------------------------------------------------
# 1. JobRetentionContract (定着支援契約)
# ----------------------------------------------------
class JobRetentionContract(db.Model):
    __tablename__ = 'job_retention_contracts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # 契約情報
    contract_office_number = db.Column(db.String(20), nullable=False) # 定着支援事業所番号
    
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date) # 最長3年/5年など
    
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # 費用負担者情報（受給者証とは異なる場合があるため）
    fee_payer_id = db.Column(db.Integer, db.ForeignKey('fee_payer_master.id'))

    # リレーションシップ
    user = db.relationship('User')
    records = db.relationship('JobRetentionRecord', back_populates='contract', lazy=True)
    fee_payer = db.relationship('FeePayerMaster', back_populates='retention_contracts')

# ----------------------------------------------------
# 2. JobRetentionRecord (定着支援の活動記録)
# ----------------------------------------------------
class JobRetentionRecord(db.Model):
    __tablename__ = 'job_retention_records'
    
    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('job_retention_contracts.id'), nullable=False)
    supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=False)
    
    record_date = db.Column(db.Date, nullable=False)
    
    # 支援方法・時間
    support_method = db.Column(db.String(50), nullable=False) # '訪問', '電話', 'メール'
    duration_minutes = db.Column(db.Integer, nullable=False) # 支援時間（分）
    
    # 記録内容
    support_content = db.Column(db.Text, nullable=False)
    
    # 請求・承認
    is_billable = db.Column(db.Boolean, default=True, nullable=False)
    is_approved = db.Column(db.Boolean, default=False, nullable=False)
    
    # リレーションシップ
    contract = db.relationship('JobRetentionContract', back_populates='records')
    supporter = db.relationship('Supporter')
