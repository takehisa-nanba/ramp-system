from backend.app.extensions import db
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, Text, func

# ====================================================================
# 1. AttendanceRecord (利用者によるセルフ打刻)
# ====================================================================
class AttendanceRecord(db.Model):
    """
    利用者によるセルフ打刻（来所・退所）の実績。
    DailyLogの「実績時間」の元データとなる客観的証跡（原理1）。
    """
    __tablename__ = 'attendance_records'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # 'CHECK_IN' or 'CHECK_OUT'
    record_type = Column(String(20), nullable=False) 
    
    timestamp = Column(DateTime, nullable=False, default=func.now()) # 打刻日時
    
    # 打刻時の場所情報（証跡）
    location_data = Column(String(255)) # GPS座標またはIPアドレス
    
    # 承認ワークフロー
    is_confirmed = Column(Boolean, default=False) # 職員による確認・承認
    
    user = relationship('User')

# ====================================================================
# 2. UserAttendanceCorrectionRequest (利用者による勤怠修正申請)
# ====================================================================
class UserAttendanceCorrectionRequest(db.Model):
    """
    利用者が打刻忘れや間違いを修正するための申請ログ（訓練と監査証跡）。
    DailyLogの時刻修正の根拠となる。
    """
    __tablename__ = 'user_attendance_correction_requests'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    target_date = Column(Date, nullable=False) # 修正対象日
    record_type = Column(String(20), nullable=False) # 'CHECK_IN' or 'CHECK_OUT'
    requested_timestamp = Column(DateTime, nullable=False) # 修正希望時刻
    
    request_reason = Column(Text, nullable=False) # 申請理由 (NULL禁止)
    
    # PENDING, APPROVED, REJECTED
    request_status = Column(String(20), default='PENDING', nullable=False) 
    
    approver_id = Column(Integer, ForeignKey('supporters.id')) # 承認した職員
    processed_at = Column(DateTime)
    
    user = relationship('User', foreign_keys=[user_id])
    approver = relationship('Supporter', foreign_keys=[approver_id])

# ====================================================================
# 3. MonthlyAttendancePlan (月次出席予定)
# ====================================================================
class MonthlyAttendancePlan(db.Model):
    """
    利用者の月次出席予定（売上予測の土台）。
    利用者との合意に基づき、次月の予定コマ数・分数を記録する。
    """
    __tablename__ = 'monthly_attendance_plans'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    target_month = Column(Date, nullable=False, index=True) # 対象月 (例: 2025-11-01)
    
    # --- 予測の母数（原理3） ---
    planned_sessions = Column(Integer, nullable=False) # 予定コマ数（日数）
    planned_minutes = Column(Integer, nullable=False) # 予定合計分数
    
    # --- 承認とロック（原理1） ---
    # (DRAFT, CONFIRMED)
    plan_status = Column(String(20), default='DRAFT', nullable=False)
    confirmed_at = Column(DateTime) # 職員による予定確定日時（ロック）
    confirmed_by_id = Column(Integer, ForeignKey('supporters.id'))
    
    user = relationship('User')
    confirmer = relationship('Supporter', foreign_keys=[confirmed_by_id])

# ====================================================================
# 4. AbsenceResponseLog (欠席時対応ログ)
# ====================================================================
class AbsenceResponseLog(db.Model):
    """
    利用者の欠席時に、職員が対応（安否確認、連絡）を行った証跡。
    減算リスク回避（原理1）のための必須ログ。
    """
    __tablename__ = 'absence_response_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    absence_date = Column(Date, nullable=False, index=True) # 欠席日
    
    # 関連するDailyLog（あれば）
    daily_log_id = Column(Integer, ForeignKey('daily_logs.id'), nullable=True, unique=True)
    
    # --- 対応の証跡（原理1） ---
    response_timestamp = Column(DateTime, default=func.now())
    response_supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False)
    
    # (例: 'PHONE_CALL', 'FAMILY_CONTACT', 'HOME_VISIT')
    response_method = Column(String(50), nullable=False)
    response_summary = Column(Text, nullable=False) # 対応内容 (NULL禁止)
    
    user = relationship('User')
    daily_log = relationship('DailyLog')
    supporter = relationship('Supporter', foreign_keys=[response_supporter_id])