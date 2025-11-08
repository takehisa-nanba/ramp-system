# backend/app/models/records.py

from datetime import datetime
from app.extensions import db
from sqlalchemy.orm import relationship
from sqlalchemy import UniqueConstraint

# ----------------------------------------------------
# 1. ServiceRecord (★ 唯一のサービス提供記録モデル ★)
# ----------------------------------------------------
class ServiceRecord(db.Model):
    __tablename__ = 'service_records'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # ★ 「場所」こそがフラグとなる (必須)
    service_location_id = db.Column(db.Integer, db.ForeignKey('service_location_master.id'), nullable=False)
    
    record_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    service_duration_minutes = db.Column(db.Integer, nullable=False) # 総時間

    service_type = db.Column(db.String(50), nullable=False) # 例: '個別訓練', 'SST', '施設外就労'
    service_content = db.Column(db.Text, nullable=False)
    
    # 証憑 (しょうひょう)
    user_confirmed_at = db.Column(db.DateTime, nullable=True) # 日々の確認
    is_approved = db.Column(db.Boolean, default=False, nullable=False) # 職員承認
    is_billable = db.Column(db.Boolean, default=True, nullable=False) # 請求対象
    
    # リレーションシップ
    service_location = db.relationship('ServiceLocationMaster', back_populates='service_records')
    break_records = db.relationship('BreakRecord', back_populates='service_record', lazy=True)
    record_supporters = db.relationship('RecordSupporter', back_populates='service_record', lazy=True)
    additive_records = db.relationship('ServiceRecordAdditive', back_populates='service_record', lazy=True)
    
    # (userへのリレーションは core.py の User.service_records で backref 済み)

# ----------------------------------------------------
# 2. ExternalSupportRecord (★ 削除 ★)
# ----------------------------------------------------
# (モデル定義ごと削除)

# ----------------------------------------------------
# 3. BreakRecord (休憩時間の詳細履歴)
# ----------------------------------------------------
class BreakRecord(db.Model):
    __tablename__ = 'break_records'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # ★ 修正: service_record_id のみを参照 (シンプルに戻す)
    service_record_id = db.Column(db.Integer, db.ForeignKey('service_records.id'), nullable=False)
    
    break_type = db.Column(db.String(50), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    
    supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id')) # 承認職員

    service_record = db.relationship('ServiceRecord', back_populates='break_records')
    supporter = db.relationship('Supporter', foreign_keys=[supporter_id])


# ----------------------------------------------------
# 4. RecordSupporter (共同支援/記録担当職員)
# ----------------------------------------------------
class RecordSupporter(db.Model):
    __tablename__ = 'record_supporters'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # ★ 修正: service_record_id のみを参照
    service_record_id = db.Column(db.Integer, db.ForeignKey('service_records.id'), nullable=False)
    
    supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=False)
    is_primary = db.Column(db.Boolean, default=False, nullable=False) 

    service_record = db.relationship('ServiceRecord', back_populates='record_supporters')
    supporter = db.relationship('Supporter')

# ----------------------------------------------------
# 5. ServiceRecordAdditive (加算実績)
# ----------------------------------------------------
class ServiceRecordAdditive(db.Model):
    __tablename__ = 'service_record_additives'
    
    id = db.Column(db.Integer, primary_key=True)

    # ★ 修正: service_record_id のみを参照
    service_record_id = db.Column(db.Integer, db.ForeignKey('service_records.id'), nullable=False)
    
    fee_master_id = db.Column(db.Integer, db.ForeignKey('government_fee_master.id'), nullable=False)
    
    units_applied = db.Column(db.Numeric, nullable=False)
    fee_rate_at_record = db.Column(db.Numeric, nullable=False)
    
    supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'))

    service_record = db.relationship('ServiceRecord', back_populates='additive_records')
    fee_master = db.relationship('GovernmentFeeMaster')
    supporter = db.relationship('Supporter', foreign_keys=[supporter_id])


# ----------------------------------------------------
# 6. AttendanceRecord (月次集計)
# ----------------------------------------------------
class AttendanceRecord(db.Model):
    __tablename__ = 'attendance_records'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reporting_month = db.Column(db.Date, nullable=False)
    
    total_days_attended = db.Column(db.Integer, default=0, nullable=False)
    total_duration_minutes = db.Column(db.Integer, default=0, nullable=False)

    # ★ 新規追加: 月次の同意（サイン）
    user_consent_date = db.Column(db.DateTime, nullable=True)
    attending_supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=True)
    is_finalized = db.Column(db.Boolean, default=False, nullable=False)
    
    # リレーションシップ
    user = db.relationship('User', back_populates='attendance_records')
    attending_supporter = db.relationship('Supporter', foreign_keys=[attending_supporter_id])

    __table_args__ = (UniqueConstraint('user_id', 'reporting_month', name='uq_user_month'),)
