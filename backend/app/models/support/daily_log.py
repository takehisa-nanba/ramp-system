# backend/app/models/support/daily_log.py

from backend.app.extensions import db
from sqlalchemy import Column, Integer, String, Date, ForeignKey, DateTime, Text, Boolean, func

# ====================================================================
# 1. UserDailyLog (利用者の作業日報)
# ====================================================================
class UserDailyLog(db.Model):
    """
    利用者の作業日報。1日1件。
    体調、自己評価、生産活動実績などを保持する。
    """
    __tablename__ = 'user_daily_logs'
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
    
    # --- カスタム項目回答 ---
    custom_data = Column(db.JSON) 
    
    # --- 入力完了フラグ ---
    morning_completed = Column(Boolean, default=False)
    evening_completed = Column(Boolean, default=False)
    
    # --- 財産化（原理5：失敗の構造化）---
    failure_factor_id = Column(Integer, ForeignKey('failure_factor_master.id'))
    challenge_analysis_notes = Column(Text) 
    heartwarming_episode = Column(Text)

    # --- ⚠️ 自動生成メタデータ ---
    auto_created = Column(Boolean, default=False)
    created_reason = Column(String(100))
    
    # --- リレーションシップ ---
    break_records = db.relationship('BreakRecord', back_populates='user_daily_log', lazy='dynamic', cascade="all, delete-orphan")
    productivity_logs = db.relationship('DailyProductivityLog', back_populates='user_daily_log', lazy='dynamic', cascade="all, delete-orphan")
    user = db.relationship('User', back_populates='user_daily_logs')
    billing_data = db.relationship('BillingData', back_populates='user_daily_log', uselist=False) # 1:1
    failure_factor = db.relationship('FailureFactorMaster', back_populates='user_daily_logs')

# ====================================================================
# 2. SupportRecord (支援記録)
# ====================================================================
class SupportRecord(db.Model):
    """
    利用者に対する具体的な支援記録。
    同じ日付に複数登録可能で、目標紐付けは任意。
    """
    __tablename__ = 'support_records'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    log_date = Column(Date, nullable=False, index=True)
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False)
    
    # 時間実績 (直接支援などの場合は時間が入るが、欠席連絡などは空もあり得るため nullable=True)
    support_start_time = Column(DateTime, nullable=True)
    support_end_time = Column(DateTime, nullable=True)
    # 支援所要時間（秒）
    # NULL: 時間を記録しない種別の記録（欠席連絡、家族連絡、企業連絡など）
    # 0: 時間を記録する種別だが、実績として0秒
    # ※ DIRECT_SUPPORT (直接支援) の場合は 0以上の値が必須。
    support_duration_seconds = Column(Integer, nullable=True)
    
    # 支援の種別
    support_record_type = Column(String(30), nullable=False, default='DIRECT_SUPPORT')
    
    # 紐づく計画・目標 (任意)
    support_plan_id = Column(Integer, ForeignKey('support_plans.id'), nullable=True)
    support_goal_id = Column(Integer, ForeignKey('individual_support_goals.id'), nullable=True)
    
    support_content = Column(Text, nullable=False) # 支援内容・詳細
    decision_reason = Column(Text)                 # 判断理由等 (オプション)
    observation_note = Column(Text)                # 観察事項等 (オプション)
    
    # --- リレーションシップ ---
    user = db.relationship('User', back_populates='support_records')
    supporter = db.relationship('Supporter', foreign_keys=[supporter_id])
    support_plan = db.relationship('SupportPlan', back_populates='support_records')
    individual_support_goal = db.relationship('IndividualSupportGoal', back_populates='support_records')

# ====================================================================
# 3. BreakRecord (休憩記録)
# ====================================================================
class BreakRecord(db.Model):
    """個別の休憩記録"""
    __tablename__ = 'break_records'
    id = Column(Integer, primary_key=True)
    user_daily_log_id = Column(Integer, ForeignKey('user_daily_logs.id'), nullable=False, index=True)
    
    break_start_time = Column(DateTime, nullable=False)
    break_end_time = Column(DateTime)
    # 休憩所要時間（秒）
    # NULL: 休憩中（終了打刻未済）
    # 0: 実績0秒の休憩
    break_duration_seconds = Column(Integer, nullable=True)
    
    user_daily_log = db.relationship('UserDailyLog', back_populates='break_records')


# ====================================================================
# 4. DailyProductivityLog (A/B型 生産活動実績)
# ====================================================================
class DailyProductivityLog(db.Model):
    """
    A型・B型の生産活動実績。
    """
    __tablename__ = 'daily_productivity_logs'
    
    id = Column(Integer, primary_key=True)
    user_daily_log_id = Column(Integer, ForeignKey('user_daily_logs.id'), nullable=False, index=True)
    
    product_id = Column(Integer, ForeignKey('product_master.id'), nullable=False)
    
    # --- 会計 ---
    units_passed_inspection = Column(Integer, default=0) 
    units_rejected = Column(Integer, default=0) 
    
    # --- 支援（生産特有の失敗分析） ---
    failure_factor_id = Column(Integer, ForeignKey('failure_factor_master.id'))
    rejection_analysis_notes = Column(Text) 
    is_repaired = Column(Boolean, default=False) 
    
    user_daily_log = db.relationship('UserDailyLog', back_populates='productivity_logs')
    product = db.relationship('ProductMaster')
    failure_factor = db.relationship('FailureFactorMaster')