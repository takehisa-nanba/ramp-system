from ...extensions import db
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, Text, Numeric, func

# ====================================================================
# 1. DailyLog (日々の記録 / 承認ワークフロー)
# ====================================================================
class DailyLog(db.Model):
    """
    日々の活動記録（日誌）。
    支援の「事実」の最小単位であり、請求(原理3)と監査(原理1)の最終証跡。
    """
    __tablename__ = 'daily_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    log_date = Column(Date, nullable=False)
    
    # ★ Plan-Activity ガードレールの核（原理1）
    # 必ず「どの目標に基づく活動か」を紐づける
    goal_id = Column(Integer, ForeignKey('individual_support_goals.id'), nullable=False, index=True) 
    
    # サービス提供を行った職員
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False, index=True)
    
    # --- 勤怠実績（セルフ打刻または職員入力） ---
    actual_start_time = Column(DateTime) # 実際の来所時刻
    actual_end_time = Column(DateTime) # 実際の退出時刻
    
    # --- 勤怠の構造化（原理2：訓練） ---
    tardiness_minutes = Column(Integer, default=0) # 遅刻時間（分）
    early_leave_minutes = Column(Integer, default=0) # 早退時間（分）
    
    # --- 加算対象の活動時間（原理3） ---
    work_preparation_minutes = Column(Integer, default=0) # 移行準備支援体制加算の対象時間（分）
    
    # --- 利用者日報（原理2：訓練） ---
    sleep_quality_score = Column(Integer) # 睡眠の質 (1-5)
    physical_condition_score = Column(Integer) # 体調 (1-5)
    grooming_check = Column(Boolean) # 身だしなみ (職員チェック)
    daily_goal_commitment = Column(Text) # 利用者自身が立てた当日の目標
    user_self_evaluation = Column(Text) # 一日の振り返り（得た気付き）
    user_lifestyle_notes = Column(Text) # 生活に関するコメント
    
    # --- 職員による記録（原理1：監査証跡） ---
    support_content_notes = Column(Text, nullable=False) # 実施内容の詳細（NULL禁止）
    
    # --- 承認ワークフロー（原理1） ---
    # (DRAFT, PENDING_APPROVAL, FINALIZED, REJECTED)
    log_status = Column(String(30), nullable=False, default='DRAFT')
    approver_id = Column(Integer, ForeignKey('supporters.id')) # 最終承認した職員
    approved_at = Column(DateTime) # ロック（変更不可）された日時
    rejection_reason = Column(Text) # 差し戻し理由（NULL禁止）
    
    # --- リレーションシップ ---
    user = relationship('User', back_populates='daily_logs')
    supporter = relationship('Supporter', foreign_keys=[supporter_id])
    approver = relationship('Supporter', foreign_keys=[approver_id])
    goal = relationship('IndividualSupportGoal')
    
    # 子テーブル
    break_records = relationship('BreakRecord', back_populates='daily_log', cascade="all, delete-orphan")
    productivity_logs = relationship('DailyProductivityLog', back_populates='daily_log', cascade="all, delete-orphan")

# ====================================================================
# 2. BreakRecord (休憩記録)
# ====================================================================
class BreakRecord(db.Model):
    """個別の休憩記録（DailyLogと1対多）"""
    __tablename__ = 'break_records'
    id = Column(Integer, primary_key=True)
    daily_log_id = Column(Integer, ForeignKey('daily_logs.id'), nullable=False, index=True)
    
    break_start_time = Column(DateTime, nullable=False)
    break_end_time = Column(DateTime)
    
    daily_log = relationship('DailyLog', back_populates='break_records')

# ====================================================================
# 3. DailyProductivityLog (A/B型 生産活動実績 / 失敗の財産化)
# ====================================================================
class DailyProductivityLog(db.Model):
    """
    A型・B型の生産活動実績（工賃計算と原価計算の土台）。
    DailyLogに紐づく。
    """
    __tablename__ = 'daily_productivity_logs'
    
    id = Column(Integer, primary_key=True)
    daily_log_id = Column(Integer, ForeignKey('daily_logs.id'), nullable=False, index=True)
    
    # どの生産活動か (masters/master_definitions.py を参照)
    product_id = Column(Integer, ForeignKey('product_master.id'), nullable=False)
    
    # --- 会計（原理3） ---
    units_passed_inspection = Column(Integer, default=0) # 良品数（工賃計算の分子）
    units_rejected = Column(Integer, default=0) # 不良品数（原価計算の損失）
    
    # --- 支援（原理2：失敗の財産化） ---
    rejection_analysis_notes = Column(Text) # 不良発生の原因分析と指導内容
    is_repaired = Column(Boolean, default=False) # 不良品を修正完了したか
    
    # --- リレーションシップ ---
    daily_log = relationship('DailyLog', back_populates='productivity_logs')
    product = relationship('ProductMaster')