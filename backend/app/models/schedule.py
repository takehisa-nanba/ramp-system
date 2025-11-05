# backend/app/models/schedule.py

from datetime import datetime
from app.extensions import db
from sqlalchemy.orm import relationship

# ----------------------------------------------------
# 1. Schedule (予定の基本情報)
# ----------------------------------------------------
class Schedule(db.Model):
    __tablename__ = 'schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    schedule_type = db.Column(db.String(50), nullable=False) # '個人面談', '会議', '訓練活動', '定着訪問'
    
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    is_all_day = db.Column(db.Boolean, default=False, nullable=False)
    
    creator_supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=False)
    is_canceled = db.Column(db.Boolean, default=False, nullable=False)
    
    # リレーションシップ
    creator_supporter = db.relationship('Supporter', back_populates='created_schedules')
    participants = db.relationship('ScheduleParticipant', back_populates='schedule', lazy=True)


# ----------------------------------------------------
# 2. ScheduleParticipant (参加者管理)
# ----------------------------------------------------
class ScheduleParticipant(db.Model):
    __tablename__ = 'schedule_participants'
    
    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedules.id'), nullable=False)
    
    # 参加者は利用者か職員のどちらか
    user_id = db.Column(db.Integer, db.ForeignKey('users.id')) 
    supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'))
    
    is_required = db.Column(db.Boolean, default=True, nullable=False)
    status = db.Column(db.String(20), default='参加予定', nullable=False) # '参加予定', '欠席', '未定'
    
    # リレーションシップ
    schedule = db.relationship('Schedule', back_populates='participants')
    user = db.relationship('User', back_populates='scheduled_participations')
    supporter = db.relationship('Supporter', back_populates='scheduled_participations')
