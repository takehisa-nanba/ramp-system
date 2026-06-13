# backend/app/models/support/schedule.py

# 修正点: 'from backend.app.extensions' (絶対参照)
from backend.app.extensions import db
from sqlalchemy import Table, Column, Integer, ForeignKey, String, DateTime, Boolean, Date, Text

# ====================================================================
# 1. schedule_participants (中間テーブル)
# ====================================================================
# 責務: スケジュール(N)と参加者(M)を紐づける
# 利用者(User)と職員(Supporter)の両方を参加者として扱えるよう、
# user_id と supporter_id の両方をFKとして持つ（原理5）。
# 修正: 1つのスケジュールに複数の参加者を登録できるよう、代理キー(id)を設定。
schedule_participants = db.Table(
    'schedule_participants', 
    db.metadata,
    db.Column('id', db.Integer, nullable=False, primary_key=True),
    db.Column('schedule_id', db.Integer, db.ForeignKey('schedules.id'), index=True),
    
    # 利用者の参加 (NULL許容)
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), index=True), 
    
    # 職員の参加 (NULL許容)
    db.Column('supporter_id', db.Integer, db.ForeignKey('supporters.id'), index=True) 
)

# ====================================================================
# 2. Schedule (スケジュール本体)
# ====================================================================
class Schedule(db.Model):
    """
    イベント・予定管理（ミーティング、シフト、個別支援活動など）。
    利用者と職員の両方の参加に対応する。
    """
    __tablename__ = 'schedules'
    
    id = Column(Integer, nullable=False, primary_key=True)
    title = Column(String(255), nullable=False)
    location = Column(String(255))
    
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime)
    
    # スケジュール種別（例: 'INDIVIDUAL_SUPPORT', 'STAFF_MEETING', 'SHIFT', 'OUTSIDE_WORK'）
    # 'OUTSIDE_WORK'の場合、オフライン準備のアラートトリガーとなる。
    schedule_type = Column(String(50))
    
    # 備考（詳細な指示など）
    description = Column(String(500))

    # --- リレーションシップ (多対多) ---
    
    # このスケジュールに参加する「利用者」
    # ★ 修正: backref を廃止し、back_populates と overlaps を使用
    participants_user = db.relationship(
        'User', 
        secondary=schedule_participants, 
        back_populates='user_schedules',
        overlaps="participants_supporter, supporter_schedules" # 競合を許容
    )
    
    participants_supporter = db.relationship(
        'Supporter', 
        secondary=schedule_participants, 
        back_populates='supporter_schedules',
        overlaps="participants_user, user_schedules" # 競合を許容
    )


class UserScheduleTemplate(db.Model):
    """
    利用者の契約曜日ごとの基本通所予定（予定テンプレート）。
    毎週の予定作成の自動化に使用される。
    """
    __tablename__ = 'user_schedule_templates'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # 曜日 ('Monday', 'Tuesday', ..., 'Sunday')
    day_of_week = Column(String(20), nullable=False)
    
    # その曜日に通所する予定があるか
    is_scheduled = Column(Boolean, default=True, nullable=False)
    
    # 予定される基本時間帯 (HH:MM形式)
    start_time = Column(String(5), nullable=True) # 例: '10:00'
    end_time = Column(String(5), nullable=True)   # 例: '16:00'
    
    # 支援区分 (ON_SITE, OFF_SITE_SUPPORT, TRANSITION_PREP, OFF_SITE_WORK, AT_HOME)
    location_type = Column(String(50), nullable=True, default='ON_SITE')
    
    user = db.relationship('User', back_populates='schedule_templates', foreign_keys=[user_id])
    
    # 複合ユニーク制約（1人の利用者に対して曜日ごとに1件）
    __table_args__ = (
        db.UniqueConstraint('user_id', 'day_of_week', name='_user_day_template_uc'),
    )


class UserScheduleRequest(db.Model):
    """
    予定の追加、欠席（キャンセル）、変更申請の履歴。
    """
    __tablename__ = 'user_schedule_requests'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    target_date = Column(Date, nullable=False, index=True)
    
    request_type = Column(String(30), nullable=False) # 'ABSENCE' (欠席), 'EXTRA_DAY' (臨時追加), 'SHIFT_TIME' (時間変更)
    requested_start_time = Column(String(5), nullable=True)
    requested_end_time = Column(String(5), nullable=True)
    
    # 理由（本人・代理）
    request_reason = Column(Text, nullable=False)
    
    # 申請状態
    request_status = Column(String(30), default='PENDING', nullable=False) # 'PENDING', 'APPROVED', 'REJECTED', 'CANCELLED'
    
    requested_by_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    requested_by_supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=True)
    
    # 意思決定
    decided_by_supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=True)
    decided_at = Column(DateTime, nullable=True)
    decision_reason = Column(Text, nullable=True) # 却下や承認時の理由
    
    user = db.relationship('User', foreign_keys=[user_id], back_populates='schedule_requests')
    requested_by_user = db.relationship('User', foreign_keys=[requested_by_user_id])
    requested_by_supporter = db.relationship('Supporter', foreign_keys=[requested_by_supporter_id])
    decided_by_supporter = db.relationship('Supporter', foreign_keys=[decided_by_supporter_id])


class UserDailySchedule(db.Model):
    """
    確定した日付ごとの通所予定の実績・事実。
    """
    __tablename__ = 'user_daily_schedules'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    date = Column(Date, nullable=False, index=True)
    start_time = Column(String(5), nullable=True)
    end_time = Column(String(5), nullable=True)
    
    schedule_kind = Column(String(30), default='NORMAL', nullable=False) # 予定の種別: 'NORMAL', 'EXTRA', 'SUBSTITUTED'
    
    # 承認状態: 'APPROVED' (承認済/確定/有効), 'CANCELLED' (キャンセル/欠席), 'REQUESTED' (申請中), 'REJECTED' (却下)
    approval_status = Column(String(30), default='APPROVED', nullable=False)

    @property
    def is_scheduled(self) -> bool:
        return self.approval_status == 'APPROVED' and self.start_time is not None and self.end_time is not None
    
    # 支援区分 (ON_SITE, OFF_SITE_SUPPORT, TRANSITION_PREP, OFF_SITE_WORK, AT_HOME)
    location_type = Column(String(50), nullable=True, default='ON_SITE')
    
    # 直接変更などの理由（欠席、臨時追加、変更などの場合）
    decision_reason = Column(Text, nullable=True)
    
    schedule_request_id = Column(Integer, ForeignKey('user_schedule_requests.id'), nullable=True)
    
    user = db.relationship('User', back_populates='daily_schedules', foreign_keys=[user_id])
    schedule_request = db.relationship('UserScheduleRequest', foreign_keys=[schedule_request_id])
    
    # 複合ユニーク制約（1人の利用者に対して1日1件の予定）
    __table_args__ = (
        db.UniqueConstraint('user_id', 'date', name='_user_daily_schedule_uc'),
    )