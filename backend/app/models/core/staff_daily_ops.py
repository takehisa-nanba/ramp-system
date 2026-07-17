# backend/app/models/core/staff_daily_ops.py

from backend.app.extensions import db
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, Text
from sqlalchemy.sql import func

class StaffDailyShift(db.Model):
    """
    職員の日次シフト予定。
    常勤換算の人員配置基準を満たしているか、事前にチェックするための「予定データ」。
    """
    __tablename__ = 'staff_daily_shifts'
    
    id = Column(Integer, primary_key=True)
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False, index=True)
    office_service_configuration_id = Column(Integer, ForeignKey('office_service_configurations.id'), nullable=False, index=True)
    
    target_date = Column(Date, nullable=False, index=True)
    
    # 予定時刻
    planned_start_time = Column(DateTime, nullable=False)
    planned_end_time = Column(DateTime, nullable=False)
    planned_break_minutes = Column(Integer, default=0, nullable=False)
    
    # このシフトが確定済みかどうか
    is_confirmed = Column(Boolean, default=False, nullable=False)
    
    supporter = db.relationship('Supporter', backref=db.backref('daily_shifts', lazy='dynamic', cascade="all, delete-orphan"))
    service_config = db.relationship('OfficeServiceConfiguration')


class StaffActionLog(db.Model):
    """
    職員の活動ログ（つぶやき形式）。
    「企業同行を行った」「〇〇さんの面談完了」など、日々の業務実績を都度記録する。
    AIがこれを集約し、業務日報（StaffDailyReport）の下書きを生成する。
    """
    __tablename__ = 'staff_action_logs'
    
    id = Column(Integer, primary_key=True)
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False, index=True)
    
    action_timestamp = Column(DateTime, nullable=False, default=func.now())
    action_content = Column(Text, nullable=False)
    
    # AIが日報に組み込み済みかどうかのフラグ
    is_processed_by_ai = Column(Boolean, default=False, nullable=False)
    
    supporter = db.relationship('Supporter', backref=db.backref('action_logs', lazy='dynamic', cascade="all, delete-orphan"))


class StaffDailyReport(db.Model):
    """
    職員の業務日報。
    StaffActionLogからAIによって自動生成（下書き）され、職員が最終確認して提出する。
    """
    __tablename__ = 'staff_daily_reports'
    
    id = Column(Integer, primary_key=True)
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False, index=True)
    target_date = Column(Date, nullable=False, index=True)
    
    # 日報本文（AI生成の下書き後、人間が編集可能）
    report_content = Column(Text, nullable=False)
    
    # AIによって生成された下書きかどうか
    is_ai_draft = Column(Boolean, default=True, nullable=False)
    
    # 本人確認（提出）済みか
    is_submitted = Column(Boolean, default=False, nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    
    supporter = db.relationship('Supporter', backref=db.backref('daily_reports', lazy='dynamic', cascade="all, delete-orphan"))
