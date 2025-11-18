from backend.app.extensions import db
from sqlalchemy.orm import relationship
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
    """利用者や職員による重要な操作の監査証跡（誰が、何を、いつ）"""
    __tablename__ = 'audit_action_logs'
    
    id = Column(Integer, primary_key=True)
    
    # 誰が操作したか
    user_id = Column(Integer, ForeignKey('users.id'), index=True) # 操作を行った利用者（いる場合）
    supporter_id = Column(Integer, ForeignKey('supporters.id'), index=True) # 操作を行った職員（いる場合）
    
    action_type = Column(String(50), nullable=False) # 例: 'CREATE_PLAN', 'USER_LOGIN', 'DATA_EXPORT'
    target_table = Column(String(50)) # 変更対象のテーブル名
    target_id = Column(Integer) # 変更対象のレコードID
    
    # 変更前後の詳細データやリクエストの詳細を保持
    change_details = Column(Text) 
    timestamp = Column(DateTime, default=func.now(), nullable=False)
    
    # リレーションシップ（core/user.py, core/supporter.py を参照）
    user = relationship('User', foreign_keys=[user_id])
    supporter = relationship('Supporter', foreign_keys=[supporter_id])