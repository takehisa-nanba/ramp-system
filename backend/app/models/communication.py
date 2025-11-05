# backend/app/models/communication.py

from datetime import datetime
from app.extensions import db
from sqlalchemy.orm import relationship

# ----------------------------------------------------
# 1. ChatMessage (メッセージ本体)
# ----------------------------------------------------
class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 送受信者
    sender_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('supporters.id')) # 1対1の場合
    channel_id = db.Column(db.Integer) # グループチャットの場合 (簡易化のため外部キーは設定しない)
    
    message_text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # 既読管理
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    
    # セキュリティ・コンプライアンス強化 (機密情報流出リスク対策)
    target_user_id = db.Column(db.Integer, db.ForeignKey('users.id')) # メッセージが言及している利用者ID
    is_sensitive = db.Column(db.Boolean, default=False, nullable=False) # 機密性の高い情報が含まれるか (監査のトリガー)
    
    # リレーションシップ
    sender = db.relationship('Supporter', foreign_keys=[sender_id], back_populates='sent_messages')
    recipient = db.relationship('Supporter', foreign_keys=[recipient_id], back_populates='received_messages')
    target_user = db.relationship('User')
