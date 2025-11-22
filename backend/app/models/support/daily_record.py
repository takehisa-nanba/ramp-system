# backend/app/models/support/support_plan.py
from backend.app.extensions import db
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, Text, Numeric, func

# ====================================================================
# 1. DailyLog (日々の活動記録 / 日報)
# ====================================================================
class DailyLog(db.Model):
    """
    日々の活動記録（日誌）。
    支援の「事実」の最小単位。
    就労移行における「些細な失敗」も、構造化して財産化する（原理2）。
    """
    __tablename__ = 'daily_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    log_date = Column(Date, nullable=False, index=True)
    
    # ★ Plan-Activity ガードレールの核
    goal_id = Column(Integer, ForeignKey('individual_support_goals.id'), nullable=False, index=True) 
    
    # サービス提供を行った職員
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False, index=True)
    
    # --- 勤怠実績 ---
    actual_start_time = Column(DateTime) 
    actual_end_time = Column(DateTime) 
    tardiness_minutes = Column(Integer, default=0) 
    early_leave_minutes = Column(Integer, default=0) 
    
    # --- 加算対象の活動時間 ---
    work_preparation_minutes = Column(Integer, default=0) 
    
    # --- 利用者日報（自己覚知） ---
    sleep_quality_score = Column(Integer) 
    physical_condition_score = Column(Integer) 
    grooming_check = Column(Boolean) 
    daily_goal_commitment = Column(Text) 
    user_self_evaluation = Column(Text) 
    user_lifestyle_notes = Column(Text) 
    
    # --- 評価の転換（相互覚知） ---
    staff_effectiveness_flag = Column(Boolean) 
    user_effectiveness_flag = Column(Boolean) 
    
    # --- 職員による記録（監査証跡） ---
    support_method = Column(String(50))
    support_content_notes = Column(Text, nullable=False) 
    
    # --- 意味のポケット（原理5） ---
    heartwarming_episode = Column(Text)

    # ★ NEW: 失敗・課題の財産化（就労移行対応）
    # 「面接失敗」「体調不良」などの要因を構造化して記録する
    failure_factor_id = Column(Integer, ForeignKey('failure_factor_master.id'))
    challenge_analysis_notes = Column(Text) # 分析と次への対策

    # --- 承認ワークフロー ---
    log_status = Column(String(30), nullable=False, default='DRAFT')
    approver_id = Column(Integer, ForeignKey('supporters.id')) 
    approved_at = Column(DateTime) 
    rejection_reason = Column(Text) 
    
    # --- リレーションシップ ---
    user = db.relationship('User', back_populates='daily_logs')
    supporter = db.relationship('Supporter', foreign_keys=[supporter_id])
    approver = db.relationship('Supporter', foreign_keys=[approver_id])
    goal = db.relationship('IndividualSupportGoal')
    
    # 失敗要因マスタへのリレーション
    failure_factor = db.relationship('FailureFactorMaster')
    
    # 子テーブル
    break_records = db.relationship('BreakRecord', back_populates='daily_log', cascade="all, delete-orphan")
    productivity_logs = db.relationship('DailyProductivityLog', back_populates='daily_log', cascade="all, delete-orphan")
    absence_response = db.relationship('AbsenceResponseLog', back_populates='daily_log', uselist=False)


# ====================================================================
# 2. BreakRecord (休憩記録)
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
# 3. DailyProductivityLog (A/B型 生産活動実績)
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