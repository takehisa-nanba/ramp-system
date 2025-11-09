# backend/app/models/audit_log.py

from app.extensions import db
from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, Column # ★ インポートを修正

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

# ----------------------------------------------------
# 2. SystemAdminActionLog (★ 新規追加: 破壊的操作の責任承認ログ ★)
# ----------------------------------------------------
class SystemAdminActionLog(db.Model):
    __tablename__ = 'system_admin_action_logs'
    
    id = Column(Integer, primary_key=True)
    
    # 実行者 (SystemAdminである職員)
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False)
    
    # 危険な操作 (例: 'SUPPORTER_DELETE', 'ALL_DATA_EXPORT')
    action_type = Column(String(100), nullable=False)
    
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # ★ 責任の証明 (PINコード認証のハッシュ) ★
    pin_approval_hash = Column(String(128), nullable=False)
    
    details = Column(Text, nullable=True) # どのユーザー、どのデータが対象か

    # リレーションシップ
    supporter = relationship('Supporter', back_populates='admin_action_logs')

