# backend/app/models/communication.py

from datetime import datetime
from app.extensions import db
from sqlalchemy.orm import relationship
from sqlalchemy import CheckConstraint, ForeignKey

# ★★★ 最終修正: 外部の参照クラスを全て文字列で置き換え、インポートの順序に依存しないようにする ★★★
# Pythonは文字列リテラルを参照する際は、ロード順序を気にしません。

# ----------------------------------------------------
# 1. SupportThread (利用者連絡帳スレッド)
# ----------------------------------------------------
class SupportThread(db.Model):
    __tablename__ = 'support_threads'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # このスレッドが「誰（利用者）」に紐づくか (必須)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False) # ★ ForeignKeyは文字列
    
    subject = db.Column(db.String(255), nullable=False) 
    status = db.Column(db.String(50), default='open', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    thread_type = db.Column(db.String(50), default='PERSONAL', nullable=False)

    # リレーションシップ (User, ChatMessageは文字列)
    messages = db.relationship('ChatMessage', back_populates='thread', lazy='dynamic', cascade="all, delete-orphan")
    user = db.relationship('User', back_populates='support_threads') # ★ Userは文字列

# ----------------------------------------------------
# 2. ChatMessage (利用者連絡帳メッセージ)
# ----------------------------------------------------
class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # このメッセージが「どのスレッド」に投稿されたか (必須)
    thread_id = db.Column(db.Integer, db.ForeignKey('support_threads.id'), nullable=False)

    # 「誰が」発言したか (職員か利用者か、どちらか一方は必須)
    sender_supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=True)
    sender_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    message_text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_internal_note = db.Column(db.Boolean, default=False, nullable=False)

    # リレーションシップ (すべて文字列)
    thread = db.relationship('SupportThread', back_populates='messages')
    sender_supporter = db.relationship('Supporter', foreign_keys=[sender_supporter_id], back_populates='sent_support_messages')
    sender_user = db.relationship('User', foreign_keys=[sender_user_id], back_populates='sent_messages')

    __table_args__ = (
        CheckConstraint(
            '(sender_supporter_id IS NOT NULL AND sender_user_id IS NULL) OR '
            '(sender_supporter_id IS NULL AND sender_user_id IS NOT NULL)',
            name='ck_chat_message_sender'
        ),
    )

# ----------------------------------------------------
# 3. ChatChannel (汎用チャットルーム)
# ----------------------------------------------------
class ChatChannel(db.Model):
    __tablename__ = 'chat_channels'
    id = db.Column(db.Integer, primary_key=True)
    
    name = db.Column(db.String(100), nullable=False) 
    channel_type = db.Column(db.String(50), nullable=False, default='STAFF_ONLY')
    
    # リレーションシップ (すべて文字列)
    messages = db.relationship('ChannelMessage', back_populates='channel', lazy='dynamic', cascade="all, delete-orphan")
    participants = db.relationship('ChannelParticipant', back_populates='channel', lazy=True, cascade="all, delete-orphan")
    u2u_request = db.relationship('UserRequest', back_populates='created_channel', uselist=False)

# ----------------------------------------------------
# 4. ChannelParticipant (汎用チャット参加者)
# ----------------------------------------------------
class ChannelParticipant(db.Model):
    __tablename__ = 'channel_participants'
    id = db.Column(db.Integer, primary_key=True)
    
    channel_id = db.Column(db.Integer, db.ForeignKey('chat_channels.id'), nullable=False)
    
    # 参加者は「職員」か「利用者」のどちらか
    supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # リレーションシップ (すべて文字列)
    channel = db.relationship('ChatChannel', back_populates='participants')
    supporter = db.relationship('Supporter', back_populates='staff_channel_participations')
    user = db.relationship('User', back_populates='channel_participations')
    
    __table_args__ = (
        CheckConstraint(
            '(supporter_id IS NOT NULL AND user_id IS NULL) OR '
            '(supporter_id IS NULL AND user_id IS NOT NULL)',
            name='ck_channel_participant_user_type'
        ),
    )

# ----------------------------------------------------
# 5. ChannelMessage (汎用チャットメッセージ)
# ----------------------------------------------------
class ChannelMessage(db.Model):
    __tablename__ = 'channel_messages'
    id = db.Column(db.Integer, primary_key=True)
    
    channel_id = db.Column(db.Integer, db.ForeignKey('chat_channels.id'), nullable=False)
    
    # 送信者も「職員」か「利用者」のどちらか
    sender_supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=True)
    sender_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    message_text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # リレーションシップ (すべて文字列)
    channel = db.relationship('ChatChannel', back_populates='messages')
    sender_supporter = db.relationship('Supporter', foreign_keys=[sender_supporter_id], back_populates='sent_staff_messages')
    sender_user = db.relationship('User', foreign_keys=[sender_user_id], back_populates='channel_messages') 

    __table_args__ = (
        CheckConstraint(
            '(sender_supporter_id IS NOT NULL AND sender_user_id IS NULL) OR '
            '(sender_supporter_id IS NULL AND sender_user_id IS NOT NULL)',
            name='ck_channel_message_sender'
        ),
    )

# ----------------------------------------------------
# 6. UserRequest (汎用的な「申請書」モデル)
# ----------------------------------------------------
class UserRequest(db.Model):
    __tablename__ = 'user_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # --- 1. 申請者 ---
    requester_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # --- 2. 申請タイプ (これが核) ---
    request_type = db.Column(db.String(50), nullable=False, index=True)
    
    # --- 3. 申請内容 (JSON形式で柔軟に保存) ---
    details = db.Column(db.JSON, nullable=True) 
    
    # --- 4. 承認ワークフロー ---
    status = db.Column(db.String(50), default='pending', nullable=False, index=True)
    approver_supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_at = db.Column(db.DateTime, nullable=True)

    # --- 5. 関連リソース (どのオブジェクトに紐づくか) ---
    created_channel_id = db.Column(db.Integer, db.ForeignKey('chat_channels.id'), nullable=True)
    target_schedule_id = db.Column(db.Integer, db.ForeignKey('schedules.id'), nullable=True)
    
    # リレーションシップ (すべて文字列)
    requester_user = db.relationship('User', foreign_keys=[requester_user_id], back_populates='sent_requests')
    approver_supporter = db.relationship('Supporter', foreign_keys=[approver_supporter_id], back_populates='approved_requests')
    created_channel = db.relationship('ChatChannel', back_populates='u2u_request')
    target_schedule = db.relationship('Schedule', back_populates='user_requests')