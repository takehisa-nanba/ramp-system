# backend/app/models/records.py

from datetime import datetime
from app.extensions import db
from sqlalchemy.orm import relationship
from sqlalchemy import UniqueConstraint

# ----------------------------------------------------
# 1. ServiceRecord (サービス提供記録 - 施設内)
# ----------------------------------------------------
class ServiceRecord(db.Model):
    __tablename__ = 'service_records'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    record_date = db.Column(db.Date, nullable=False)
    
    # 時間管理
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    service_duration_minutes = db.Column(db.Integer, nullable=False) # 在所時間 (計算値)

    service_type = db.Column(db.String(50), nullable=False)
    service_content = db.Column(db.Text, nullable=False)
    
    # ステータス
    is_billable = db.Column(db.Boolean, default=True, nullable=False)
    is_approved = db.Column(db.Boolean, default=False, nullable=False)
    
    # リレーションシップ
    break_records = db.relationship('BreakRecord', back_populates='service_record', lazy=True)
    record_supporters = db.relationship('RecordSupporter', back_populates='service_record', lazy=True, foreign_keys='RecordSupporter.service_record_id')
    additive_records = db.relationship('ServiceRecordAdditive', back_populates='service_record', lazy=True)


# ----------------------------------------------------
# 2. ExternalSupportRecord (施設外支援記録)
# ----------------------------------------------------
class ExternalSupportRecord(db.Model):
    __tablename__ = 'external_support_records'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    record_date = db.Column(db.Date, nullable=False)
    
    # 時間管理
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    actual_work_minutes = db.Column(db.Integer, nullable=False) # 実働時間 (計算値)

    support_location = db.Column(db.String(100), nullable=False)
    support_content = db.Column(db.Text, nullable=False)
    
    is_billable = db.Column(db.Boolean, default=True, nullable=False)

    # リレーションシップ
    record_supporters = db.relationship('RecordSupporter', back_populates='external_record', lazy=True, foreign_keys='RecordSupporter.external_record_id')
    additive_records = db.relationship('ServiceRecordAdditive', back_populates='external_record', lazy=True)


# ----------------------------------------------------
# 3. BreakRecord (休憩時間の詳細履歴 - ServiceRecordの子)
# ----------------------------------------------------
class BreakRecord(db.Model):
    __tablename__ = 'break_records'
    
    id = db.Column(db.Integer, primary_key=True)
    service_record_id = db.Column(db.Integer, db.ForeignKey('service_records.id'), nullable=False)
    
    break_type = db.Column(db.String(50), nullable=False) # '昼休憩', '小休憩'
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    
    supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id')) # 承認職員

    service_record = db.relationship('ServiceRecord', back_populates='break_records')


# ----------------------------------------------------
# 4. RecordSupporter (共同支援/記録担当職員の中間テーブル)
# ----------------------------------------------------
class RecordSupporter(db.Model):
    __tablename__ = 'record_supporters'
    
    id = db.Column(db.Integer, primary_key=True)
    # ServiceRecord または ExternalSupportRecord のいずれか一方に紐づく
    service_record_id = db.Column(db.Integer, db.ForeignKey('service_records.id'))
    external_record_id = db.Column(db.Integer, db.ForeignKey('external_support_records.id'))
    supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=False)
    
    is_primary = db.Column(db.Boolean, default=False, nullable=False) # 主担当者か

    service_record = db.relationship('ServiceRecord', foreign_keys=[service_record_id], back_populates='record_supporters')
    external_record = db.relationship('ExternalSupportRecord', foreign_keys=[external_record_id], back_populates='record_supporters')
    supporter = db.relationship('Supporter')


# ----------------------------------------------------
# 5. ServiceRecordAdditive (加算実績)
# ----------------------------------------------------
class ServiceRecordAdditive(db.Model):
    __tablename__ = 'service_record_additives'
    
    id = db.Column(db.Integer, primary_key=True)
    # ServiceRecord または ExternalSupportRecord のいずれか一方に紐づく
    service_record_id = db.Column(db.Integer, db.ForeignKey('service_records.id'))
    external_record_id = db.Column(db.Integer, db.ForeignKey('external_support_records.id'))
    
    fee_master_id = db.Column(db.Integer, db.ForeignKey('government_fee_master.id'), nullable=False)
    
    units_applied = db.Column(db.Numeric, nullable=False)
    fee_rate_at_record = db.Column(db.Numeric, nullable=False) # 記録時点の単価（検証用）
    
    supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id')) # 加算の発生に関わった職員

    service_record = db.relationship('ServiceRecord', foreign_keys=[service_record_id], back_populates='additive_records')
    external_record = db.relationship('ExternalSupportRecord', foreign_keys=[external_record_id], back_populates='additive_records')
    fee_master = db.relationship('GovernmentFeeMaster')


# ----------------------------------------------------
# 6. AttendanceRecord (実績記録表 - 月次集計)
# ----------------------------------------------------
class AttendanceRecord(db.Model):
    __tablename__ = 'attendance_records'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    reporting_month = db.Column(db.Date, nullable=False)
    
    total_days_attended = db.Column(db.Integer, default=0, nullable=False)
    total_duration_minutes = db.Column(db.Integer, default=0, nullable=False)
    
    __table_args__ = (UniqueConstraint('user_id', 'reporting_month', name='uq_user_month'),)
