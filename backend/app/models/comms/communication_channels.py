from backend.app.extensions import db
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, Text, func

# ====================================================================
# 1. SupportThread (チャットスレッド)
# ====================================================================
class SupportThread(db.Model):
    """
    利用者と職員間のチャットスレッド（匿名の継続支援チャットにも利用）。
    Userモデルの匿名ID(display_name)と連携する（原理5）。
    """
    __tablename__ = 'support_threads'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # スレッドの状態（例: 'OPEN', 'CLOSED', 'ARCHIVED'）
    status = Column(String(20), default='OPEN', nullable=False)
    
    # --- リレーションシップ ---
    user = relationship('User', back_populates='support_threads')
    messages = relationship('ChatMessage', back_populates='thread', lazy='dynamic', cascade="all, delete-orphan")

# ====================================================================
# 2. ChatMessage (チャットメッセージ)
# ====================================================================
class ChatMessage(db.Model):
    """
    チャットメッセージ（監査証跡として変更不可）。
    送信者が利用者か職員かを区別する。
    """
    __tablename__ = 'chat_messages'
    id = Column(Integer, primary_key=True)
    thread_id = Column(Integer, ForeignKey('support_threads.id'), nullable=False, index=True)
    
    # 誰がメッセージを送信したか（UserまたはSupporter）
    sender_user_id = Column(Integer, ForeignKey('users.id'), index=True) 
    sender_supporter_id = Column(Integer, ForeignKey('supporters.id'), index=True) 
    
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=func.now(), nullable=False)
    
    # --- リレーションシップ ---
    thread = relationship('SupportThread', back_populates='messages')
    sender_user = relationship('User', foreign_keys=[sender_user_id])
    sender_supporter = relationship('Supporter', foreign_keys=[sender_supporter_id])

# ====================================================================
# 3. UserRequest (利用者からのリクエスト)
# ====================================================================
class UserRequest(db.Model):
    """利用者からの構造化されたリクエスト（例: 欠席連絡、面談希望など）"""
    __tablename__ = 'user_requests'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    request_type = Column(String(50), nullable=False) # (例: 'ABSENCE_NOTIFICATION', 'INTERVIEW_REQUEST')
    details = Column(Text)
    is_resolved = Column(Boolean, default=False)
    
    user = relationship('User', back_populates='user_requests')