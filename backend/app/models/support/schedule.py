# backend/app/models/support/schedule.py
from backend.app.extensions import db
from sqlalchemy import Table, Column, Integer, ForeignKey, String, DateTime

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