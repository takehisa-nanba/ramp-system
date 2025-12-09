# backend/app/models/core/session_management.py

from backend.app.extensions import db
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func

class SessionLock(db.Model):
    """
    PII入力セッションの非活動時間ロックを管理する。データ揮発性ロジックの基盤。
    """
    __tablename__ = 'session_locks'
    
    id = Column(Integer, primary_key=True)
    
    # ユーザー/職員セッションを一意に識別する外部キー
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=True, index=True) 
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    
    # PIIが現在利用されているセッションかを判定（重要度の切り分け）
    is_pii_session = Column(Boolean, default=False, nullable=False)
    
    # 最終活動日時 (タイマーリセット用)
    last_activity_at = Column(DateTime, default=func.now(), nullable=False)
    
    # セッション開始日時
    session_start_at = Column(DateTime, default=func.now(), nullable=False)

    # リレーションシップ
    supporter = db.relationship('Supporter', foreign_keys=[supporter_id])
    user = db.relationship('User', foreign_keys=[user_id])