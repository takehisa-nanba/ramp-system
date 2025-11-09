# backend/app/models/audit_log.py

from app.extensions import db
from datetime import datetime
from sqlalchemy.orm import relationship

class SystemLog(db.Model):
    # (変更なし)
    __tablename__ = 'system_logs'
    id = db.Column(db.Integer, primary_key=True)
    
    action = db.Column(db.String(100), nullable=False) 
    supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=False)
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id')) 
    support_plan_id = db.Column(db.Integer, db.ForeignKey('support_plans.id'))
    # --- ★ ここに「詳細」カラムを追加 ★ ---
    details = db.Column(db.Text, nullable=True) # 監査ログの詳細
    # --- ★ 追加ここまで ★ ---
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    supporter = db.relationship('Supporter', foreign_keys=[supporter_id])
    user = db.relationship('User', back_populates='system_logs', foreign_keys=[user_id])
    
    ### plan.py 側で back_populates='system_logs' を追加したため、
    ### こちらの 'support_plan' のリレーションも修正します。
    support_plan = db.relationship('SupportPlan', back_populates='system_logs', foreign_keys=[support_plan_id])
