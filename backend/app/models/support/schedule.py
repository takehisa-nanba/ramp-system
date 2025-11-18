from backend.app.extensions import db
from sqlalchemy.orm import relationship
from sqlalchemy import Table, Column, Integer, ForeignKey, String, DateTime

# ====================================================================
# 1. schedule_participants (中間テーブル)
# ====================================================================
# 責務: スケジュール(N)と参加者(M)を紐づける
# 利用者(User)と職員(Supporter)の両方を参加者として扱えるよう、
# user_id と supporter_id の両方をFKとして持つ。
schedule_participants = db.Table(
    'schedule_participants', 
    db.Column('schedule_id', db.Integer, db.ForeignKey('schedules.id'), primary_key=True),
    
    # 利用者の参加
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True, index=True), 
    
    # 職員の参加
    db.Column('supporter_id', db.Integer, db.ForeignKey('supporters.id'), primary_key=True, index=True) 
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
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    location = Column(String(255))
    
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime)
    
    # スケジュール種別（例: 'INDIVIDUAL_SUPPORT', 'STAFF_MEETING', 'SHIFT')
    schedule_type = Column(String(50))

    # --- リレーションシップ (多対多) ---
    
    # このスケジュールに参加する「利用者」 (core/user.py を参照)
    participants_user = db.relationship('User', secondary=schedule_participants, backref='user_schedules')
    
    # このスケジュールに参加する「職員」 (core/supporter.py を参照)
    participants_supporter = db.relationship('Supporter', secondary=schedule_participants, backref='supporter_schedules')