# backend/app/models/core/audit_log.py

# 修正点: 'from backend.app.extensions' (絶対参照)
from backend.app.extensions import db
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, Text, func

# ====================================================================
# 1. SystemLog (システムイベントログ)
# ====================================================================
class SystemLog(db.Model):
    """システムレベルの操作ログ（エラー、重要イベントなど）"""
    __tablename__ = 'system_logs'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=func.now(), nullable=False)
    log_level = Column(String(20)) # 例: ERROR, WARNING, INFO
    message = Column(Text, nullable=False)

# ====================================================================
# 2. AuditActionLog (操作監査証跡)
# ====================================================================
class AuditActionLog(db.Model):
    """利用者や職員による重要な操作の事実を記録する監査証跡"""
    __tablename__ = 'audit_action_logs'
    
    id = Column(Integer, primary_key=True)
    
    # 誰が操作したか
    actor_supporter_id = Column(Integer, ForeignKey('supporters.id'), index=True, nullable=True) # 操作を行った職員
    user_id = Column(Integer, ForeignKey('users.id'), index=True, nullable=True) # 操作を行った利用者（いる場合）
    
    action = Column(String(50), nullable=False) # 例: 'CREATE_SUPPORT_PLAN', 'VIEW_PII'
    entity_type = Column(String(50), nullable=False) # 変更対象のモデル名や概念
    entity_id = Column(Integer, nullable=True) # 変更対象のレコードID
    
    # 変更前後と理由の詳細データ
    before_value = Column(Text, nullable=True) 
    after_value = Column(Text, nullable=True) 
    reason = Column(Text, nullable=True) 
    
    # アクセス環境情報
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # リレーションシップ
    supporter = db.relationship('Supporter', foreign_keys=[actor_supporter_id])
    user = db.relationship('User', foreign_keys=[user_id])