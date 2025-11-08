# backend/app/models/communication.py

from datetime import datetime
from app.extensions import db
from sqlalchemy.orm import relationship
from sqlalchemy import CheckConstraint, ForeignKey

# ----------------------------------------------------
# 1. SupportThread (利用者連絡帳スレッド)
# 目的: 利用者1名 ⇔ 職員N名 の証憑が残る連絡
# ----------------------------------------------------
class SupportThread(db.Model):
    __tablename__ = 'support_threads'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # このスレッドが「誰（利用者）」に紐づくか (必須)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    subject = db.Column(db.String(255), nullable=False) # スレッドの件名
    status = db.Column(db.String(50), default='open', nullable=False) # 'open', 'closed'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # アナウンス用 (Trueなら全利用者が閲覧可能)
    thread_type = db.Column(db.String(50), default='PERSONAL', nullable=False) # 'PERSONAL' or 'ANNOUNCEMENT'

    # このスレッドにぶら下がる全メッセージ (逆参照)
    messages = db.relationship('ChatMessage', back_populates='thread', lazy='dynamic', cascade="all, delete-orphan")
    
    # このスレッドの持ち主 (逆参照)
    user = db.relationship('User', back_populates='support_threads')

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
    
    # Trueの場合、利用者には表示しない (職員同士の内部メモ用)
    is_internal_note = db.Column(db.Boolean, default=False, nullable=False)

    # リレーションシップ
    thread = db.relationship('SupportThread', back_populates='messages')
    sender_supporter = db.relationship('Supporter', foreign_keys=[sender_supporter_id], back_populates='sent_support_messages')
    sender_user = db.relationship('User', foreign_keys=[sender_user_id], back_populates='sent_messages')

    # ★ 送信者は必ず1人だけであることを保証する制約 ★
    __table_args__ = (
        CheckConstraint(
            '(sender_supporter_id IS NOT NULL AND sender_user_id IS NULL) OR '
            '(sender_supporter_id IS NULL AND sender_user_id IS NOT NULL)',
            name='ck_chat_message_sender'
        ),
    )

# ----------------------------------------------------
# 3. ChatChannel (汎用チャットルーム - Slack/Teams)
# 目的: 職員間(STAFF_ONLY) または 訓練用(TRAINING)
# ----------------------------------------------------
class ChatChannel(db.Model):
    __tablename__ = 'chat_channels'
    id = db.Column(db.Integer, primary_key=True)
    
    name = db.Column(db.String(100), nullable=False) # 例: '浜松事業所', 'AさんBさんSST'
    
    # ★ ルールの核 ★
    # 'STAFF_ONLY' (職員専用) or 'TRAINING' (訓練用)
    channel_type = db.Column(db.String(50), nullable=False, default='STAFF_ONLY')
    
    messages = db.relationship('ChannelMessage', back_populates='channel', lazy='dynamic', cascade="all, delete-orphan")
    participants = db.relationship('ChannelParticipant', back_populates='channel', lazy=True, cascade="all, delete-orphan")
    u2u_request = db.relationship('UserRequest', back_populates='created_channel', uselist=False) # ★ 申請書からの逆参照

# ----------------------------------------------------
# 4. ChannelParticipant (汎用チャット参加者)
# ----------------------------------------------------
class ChannelParticipant(db.Model):
    __tablename__ = 'channel_participants'
    id = db.Column(db.Integer, primary_key=True)
    
    channel_id = db.Column(db.Integer, db.ForeignKey('chat_channels.id'), nullable=False)
    
    # ★ 参加者は「職員」か「利用者」のどちらか ★
    supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    channel = db.relationship('ChatChannel', back_populates='participants')
    supporter = db.relationship('Supporter', back_populates='staff_channel_participations')
    user = db.relationship('User', back_populates='channel_participations')
    
    # ★ 参加者は必ず1人だけであることを保証する制約 ★
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
    
    # ★ 送信者も「職員」か「利用者」のどちらか ★
    sender_supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=True)
    sender_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    message_text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    channel = db.relationship('ChatChannel', back_populates='messages')
    sender_supporter = db.relationship('Supporter', foreign_keys=[sender_supporter_id], back_populates='sent_staff_messages')
    sender_user = db.relationship('User', foreign_keys=[sender_user_id], back_populates='channel_messages') # Userからの逆参照

    # ★ 送信者は必ず1人だけであることを保証する制約 ★
    __table_args__ = (
        CheckConstraint(
            '(sender_supporter_id IS NOT NULL AND sender_user_id IS NULL) OR '
            '(sender_supporter_id IS NULL AND sender_user_id IS NOT NULL)',
            name='ck_channel_message_sender'
        ),
    )

# ----------------------------------------------------
# 6. UserRequest (★ 汎用的な「申請書」モデル ★)
# ----------------------------------------------------
class UserRequest(db.Model):
    __tablename__ = 'user_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # --- 1. 申請者 ---
    requester_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # --- 2. 申請タイプ (これが核) ---
    # 'U2U_CHAT' (利用者間チャット), 'ABSENCE' (欠席連絡), 'SCHEDULE_CHANGE' (予定変更申請), 
    # 'INTERVIEW_REQUEST' (面談申請), 'RESUME_REVIEW' (履歴書添削) など
    request_type = db.Column(db.String(50), nullable=False, index=True)
    
    # --- 3. 申請内容 (JSON形式で柔軟に保存) ---
    # 例: {'target_user_id': 12, 'topic': '...'}
    # 例: {'date': '2025-11-10', 'reason': '...'}
    details = db.Column(db.JSON, nullable=True) 
    
    # --- 4. 承認ワークフロー ---
    # 'pending' (申請中), 'approved' (承認済), 'rejected' (却下)
    status = db.Column(db.String(50), default='pending', nullable=False, index=True)
    
    approver_supporter_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_at = db.Column(db.DateTime, nullable=True)

    # --- 5. 関連リソース (どのオブジェクトに紐づくか) ---
    # 承認されて作成されたチャットルームのID
    created_channel_id = db.Column(db.Integer, db.ForeignKey('chat_channels.id'), nullable=True)
    
    # 変更対象のスケジュールID
    target_schedule_id = db.Column(db.Integer, db.ForeignKey('schedules.id'), nullable=True)
    
    # リレーションシップ
    requester_user = db.relationship('User', foreign_keys=[requester_user_id], back_populates='sent_requests')
    approver_supporter = db.relationship('Supporter', foreign_keys=[approver_supporter_id], back_populates='approved_requests')
    created_channel = db.relationship('ChatChannel', back_populates='u2u_request')
    target_schedule = db.relationship('Schedule', backref='user_requests')
