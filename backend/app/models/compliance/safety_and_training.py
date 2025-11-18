from backend.app.extensions import db
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, Text, func

# ====================================================================
# 1. CommitteeActivityLog (委員会活動記録)
# ====================================================================
class CommitteeActivityLog(db.Model):
    """
    法令で義務付けられた委員会活動（虐待防止、感染予防など）の実施ログ。
    実施漏れのムダ（原理1）を排除する。
    """
    __tablename__ = 'committee_activity_logs'
    
    id = Column(Integer, primary_key=True)
    
    # どの事業所の活動か
    office_id = Column(Integer, ForeignKey('office_settings.id'), nullable=False, index=True)
    
    # どの委員会か (masters/master_definitions.py を参照)
    committee_type_id = Column(Integer, ForeignKey('committee_type_master.id'), nullable=False, index=True)
    
    meeting_timestamp = Column(DateTime, nullable=False, default=func.now())
    
    # attendee_ids (JSON or Link Table)
    
    # --- 証憑（原理1） ---
    discussion_summary = Column(Text, nullable=False) # 議論概要 (NULL禁止)
    decided_action_plan = Column(Text) # 決定した行動計画
    
    manager_id = Column(Integer, ForeignKey('supporters.id')) # 承認した管理者
    
    office = relationship('OfficeSetting')
    committee_type = relationship('CommitteeTypeMaster')
    manager = relationship('Supporter', foreign_keys=[manager_id])

# ====================================================================
# 2. OfficeTrainingEvent (事業所研修イベント)
# ====================================================================
class OfficeTrainingEvent(db.Model):
    """
    事業所が実施した研修イベント（避難訓練など）の「実施事実」。
    TrainingTypeMasterと紐づけることで、法定頻度を監視可能にする（原理1）。
    """
    __tablename__ = 'office_training_events'
    
    id = Column(Integer, primary_key=True)
    office_id = Column(Integer, ForeignKey('office_settings.id'), nullable=False, index=True)
    
    # ★ 修正: 文字列ではなくマスタIDを参照
    training_type_id = Column(Integer, ForeignKey('training_type_master.id'), nullable=False, index=True)
    
    training_name = Column(String(255), nullable=False) # 具体的な研修名
    
    event_timestamp = Column(DateTime, nullable=False, default=func.now())
    duration_minutes = Column(Integer) # 研修時間（分）
    instructor = Column(String(100)) # 講師名
    
    office = relationship('OfficeSetting')
    # ★ NEW: 研修種別へのリレーション
    training_type = relationship('TrainingTypeMaster', back_populates='events')
    
    # 参加した職員のTrainingLogからの逆参照
    attendee_logs = relationship('TrainingLog', back_populates='office_event', lazy='dynamic')

# ====================================================================
# 3. TrainingLog (職員研修記録)
# ====================================================================
class TrainingLog(db.Model):
    """
    職員個人の研修受講記録（内部・外部）。
    「みなし時間」の根拠、および職員の成長アセット（原理2）。
    """
    __tablename__ = 'training_logs'
    
    id = Column(Integer, primary_key=True)
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False, index=True)
    
    # どの事業所研修（内部）に参加したか (NULL許容)
    office_training_event_id = Column(Integer, ForeignKey('office_training_events.id'), nullable=True)
    
    # --- 外部研修の場合 ---
    training_name = Column(String(255), nullable=False)
    training_type = Column(String(50), nullable=False) # (例: 'EXTERNAL', 'INTERNAL', 'LEGAL_MANDATE')
    completion_date = Column(Date, nullable=False)
    duration_minutes = Column(Integer) # 研修時間（分）
    
    # --- 証憑（原理1） ---
    document_url = Column(String(500)) # 修了証のURL
    summary_of_learning = Column(Text, nullable=False) # 学習内容の要約 (NULL禁止)
    
    supporter = relationship('Supporter')
    office_event = relationship('OfficeTrainingEvent', back_populates='attendee_logs')

# ====================================================================
# 4. SupporterFeedbackLog (利用者からの職員評価 / 相互成長)
# ====================================================================
class SupporterFeedbackLog(db.Model):
    """
    利用者から職員へのフィードバック。
    「支援者への支援」をデータ化し、相互成長（哲学）を促す。
    """
    __tablename__ = 'supporter_feedback_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False, index=True)
    
    feedback_timestamp = Column(DateTime, nullable=False, default=func.now())
    rating_score = Column(Integer) # 評価スコア (1-5)
    narrative_feedback = Column(Text, nullable=False) # 自由記述 (NULL禁止)
    is_anonymous = Column(Boolean, default=True) # 匿名フラグ
    
    user = relationship('User')
    supporter = relationship('Supporter')

# ====================================================================
# 5. StaffReflectionLog (職員の内省ログ / 失敗の財産化)
# ====================================================================
class StaffReflectionLog(db.Model):
    """
    職員の内省ログ（失敗の財産化）。
    日々の記録やFBを基に、職員が「学び」を記録する（哲学）。
    """
    __tablename__ = 'staff_reflection_logs'
    
    id = Column(Integer, primary_key=True)
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False, index=True)
    reflection_timestamp = Column(DateTime, nullable=False, default=func.now())
    
    # どの記録（事実）に対する内省か (汎用)
    context_log_type = Column(String(50)) # (例: 'DailyLog', 'IncidentReport', 'FeedbackLog')
    context_log_id = Column(Integer)
    
    # --- 内省（原理2） ---
    reflection_summary = Column(Text, nullable=False) # 内省内容 (NULL禁止)
    personal_growth_plan = Column(Text) # 今後の行動計画
    
    supporter = relationship('Supporter')