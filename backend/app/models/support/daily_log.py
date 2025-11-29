# backend/app/models/support_process/daily_log.py

from backend.app.extensions import db
from sqlalchemy import Column, Integer, String, Date, ForeignKey, DateTime, Text, Boolean, func

# ====================================================================
# 1. DailyLog (サービス提供記録 - 親)
# ====================================================================
class DailyLog(db.Model):
    """
    日報（サービス提供記録）。請求の基点となる最小単位。
    利用者の実態と、職員の記録の「親」となる。
    """
    __tablename__ = 'daily_logs'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    log_date = Column(Date, nullable=False, index=True)
    
    # --- 請求/監査ファクト ---
    location_type = Column(String(50), nullable=False) # 'ON_SITE', 'OFF_SITE_USER_HOME', etc.
    external_location_detail = Column(Text) # 事業所外活動の具体的な場所
    log_status = Column(String(30), nullable=False, default='DRAFT') # 承認ワークフロー
    
    # --- 利用者実態と評価（支援の質の担保）---
    sleep_quality_score = Column(Integer) 
    physical_condition_score = Column(Integer) 
    grooming_check = Column(Boolean) 
    user_self_evaluation = Column(Text) 
    staff_effectiveness_flag = Column(Boolean) 
    user_effectiveness_flag = Column(Boolean) 
    support_content_notes = Column(Text, nullable=False) # 職員による記録の要約
    
    # --- 財産化（原理5：失敗の構造化）---
    failure_factor_id = Column(Integer, ForeignKey('failure_factor_master.id'))
    challenge_analysis_notes = Column(Text) 
    heartwarming_episode = Column(Text)
    
    # --- リレーションシップ ---
    activities = db.relationship('DailyLogActivity', back_populates='daily_log', cascade="all, delete-orphan")
    break_records = db.relationship('BreakRecord', back_populates='daily_log', lazy='dynamic', cascade="all, delete-orphan")
    productivity_logs = db.relationship('DailyProductivityLog', back_populates='daily_log', lazy='dynamic', cascade="all, delete-orphan")
    user = db.relationship('User', back_populates='daily_logs')
    billing_data = db.relationship('BillingData', back_populates='daily_log', uselist=False) # 1:1
    failure_factor = db.relationship('FailureFactorMaster', back_populates='daily_logs')

# ====================================================================
# 2. DailyLogActivity (活動実績 - 変動費請求の根拠)
# ====================================================================
class DailyLogActivity(db.Model):
    """
    日報に紐づく具体的な活動実績。変動費請求の根拠となる最小単位。
    """
    __tablename__ = 'daily_log_activities'
    id = Column(Integer, primary_key=True)
    daily_log_id = Column(Integer, ForeignKey('daily_logs.id'), nullable=False)
    
    # --- 請求ファクト ---
    support_goal_id = Column(Integer, ForeignKey('individual_support_goals.id'), nullable=False) 
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False)
    
    # 時間実績
    support_start_time = Column(DateTime, nullable=False)
    support_end_time = Column(DateTime, nullable=False)
    
    # 加算対象の時間 (個別の活動で時間計測)
    work_preparation_minutes = Column(Integer, default=0) 
    
    support_content = Column(Text, nullable=False) # 個別の活動内容
    
    # --- リレーションシップ ---
    daily_log = db.relationship('DailyLog', back_populates='activities')
    supporter = db.relationship('Supporter', foreign_keys=[supporter_id])
    individual_support_goal = db.relationship('IndividualSupportGoal', back_populates='daily_activities')

# ====================================================================
# 3. BreakRecord (休憩記録)
# ====================================================================
class BreakRecord(db.Model):
    """個別の休憩記録"""
    __tablename__ = 'break_records'
    id = Column(Integer, primary_key=True)
    daily_log_id = Column(Integer, ForeignKey('daily_logs.id'), nullable=False, index=True)
    
    break_start_time = Column(DateTime, nullable=False)
    break_end_time = Column(DateTime)
    
    daily_log = db.relationship('DailyLog', back_populates='break_records')


# ====================================================================
# 4. DailyProductivityLog (A/B型 生産活動実績)
# ====================================================================
class DailyProductivityLog(db.Model):
    """
    A型・B型の生産活動実績。
    DailyLog（親）にも失敗分析機能がついたが、
    製品ごとの厳密な不良数管理のためにこのモデルは維持する。
    """
    __tablename__ = 'daily_productivity_logs'
    
    id = Column(Integer, primary_key=True)
    daily_log_id = Column(Integer, ForeignKey('daily_logs.id'), nullable=False, index=True)
    
    product_id = Column(Integer, ForeignKey('product_master.id'), nullable=False)
    
    # --- 会計 ---
    units_passed_inspection = Column(Integer, default=0) 
    units_rejected = Column(Integer, default=0) 
    
    # --- 支援（生産特有の失敗分析） ---
    failure_factor_id = Column(Integer, ForeignKey('failure_factor_master.id'))
    rejection_analysis_notes = Column(Text) 
    is_repaired = Column(Boolean, default=False) 
    
    daily_log = db.relationship('DailyLog', back_populates='productivity_logs')
    product = db.relationship('ProductMaster')
    failure_factor = db.relationship('FailureFactorMaster')