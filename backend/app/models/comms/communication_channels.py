# backend/app/models/comms/communication_channels.py

# 修正点: 'from backend.app.extensions' (絶対参照)
from backend.app.extensions import db
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
    
    # 問題の所在タグ (Knowledge Baseへの入り口)
    # どのカテゴリの相談か (masters/master_definitions.py の IssueCategoryMaster を参照)
    issue_category_id = Column(Integer, ForeignKey('issue_category_master.id'))

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # --- リレーションシップ ---
    user = db.relationship('User', back_populates='support_threads')
    messages = db.relationship('ChatMessage', back_populates='thread', lazy='dynamic', cascade="all, delete-orphan")
    issue_category = db.relationship('IssueCategoryMaster')

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
    
    # 既読状態（オプション）
    is_read = Column(Boolean, default=False)
    
    # --- リレーションシップ ---
    thread = db.relationship('SupportThread', back_populates='messages')
    sender_user = db.relationship('User', foreign_keys=[sender_user_id])
    sender_supporter = db.relationship('Supporter', foreign_keys=[sender_supporter_id])

# ====================================================================
# 3. UserRequest (利用者からのリクエスト)
# ====================================================================
class UserRequest(db.Model):
    """
    利用者からの構造化されたリクエスト（例: 欠席連絡、面談希望など）。
    チャットとは異なり、ステータス管理を伴うタスクとして扱う。
    """
    __tablename__ = 'user_requests'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # (例: 'ABSENCE_NOTIFICATION', 'INTERVIEW_REQUEST', 'DOC_REQUEST')
    request_type = Column(String(50), nullable=False) 
    
    details = Column(Text)
    
    # 対応ステータス
    is_resolved = Column(Boolean, default=False)
    resolution_notes = Column(Text) # 対応内容
    resolved_at = Column(DateTime)
    resolved_by_supporter_id = Column(Integer, ForeignKey('supporters.id'))
    
    created_at = Column(DateTime, default=func.now())
    
    user = db.relationship('User', back_populates='user_requests')
    resolver = db.relationship('Supporter', foreign_keys=[resolved_by_supporter_id])