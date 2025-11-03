# app/models/user/profile.py
from app.extensions import db
from datetime import datetime, timezone
from sqlalchemy.orm import relationship

# --- ▼▼▼ 成育歴カテゴリとの中間テーブル ▼▼▼ ---
# DevelopmentalHistoryItem と HistoryCategoryMaster の多対多の関係
developmental_history_categories_association = db.Table(
    'developmental_history_categories_association',
    db.Model.metadata,
    db.Column('history_item_id', db.Integer, db.ForeignKey('developmental_history_items.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('history_category_master.id'), primary_key=True)
)
# --- ▲▲▲ 中間テーブル ▲▲▲ ---

class FamilyMember(db.Model):
    """
    家族構成モデル (利用者に1対多)
    """
    __tablename__ = 'family_members'
    __table_args__ = ({"extend_existing": True},)
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    name = db.Column(db.String(100), nullable=False) # 氏名
    relationship = db.Column(db.String(50)) # 続柄
    is_living_together = db.Column(db.Boolean, default=True) # 同居フラグ
    occupation = db.Column(db.String(100)) # 職業 (任意)
    health_status = db.Column(db.Text) # 健康状態 (任意)
    notes = db.Column(db.Text) # 利用者との関係性、関わり方など
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Userモデルへの参照
    user = db.relationship('User', back_populates='family_members')

    def __repr__(self):
        return f'<FamilyMember {self.id} (User: {self.user_id})>'

class EmergencyContact(db.Model):
    """
    緊急連絡先モデル (利用者に1対多)
    """
    __tablename__ = 'emergency_contacts'
    __table_args__ = ({"extend_existing": True},)
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    name = db.Column(db.String(100), nullable=False) # 連絡先氏名
    relationship = db.Column(db.String(50)) # 続柄
    phone_number = db.Column(db.String(20), nullable=False) # 電話番号
    address = db.Column(db.String(255)) # 住所 (任意)
    priority = db.Column(db.Integer, default=1, index=True) # 連絡優先度 (1が最高)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    remarks = db.Column(db.Text)

    # Userモデルへの参照
    user = db.relationship('User', back_populates='emergency_contacts')

    def __repr__(self):
        return f'<EmergencyContact {self.id} (User: {self.user_id})>'

class DevelopmentalHistoryItem(db.Model):
    """
    成育歴項目モデル (利用者に1対多)
    カテゴリと多対多の関係を持つ
    """
    __tablename__ = 'developmental_history_items'
    __table_args__ = ({"extend_existing": True},)
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    event_period = db.Column(db.String(50), nullable=False, index=True) # 例: "2010年4月"
    description = db.Column(db.Text, nullable=False) # 例: "〇〇小学校入学"
    sort_order = db.Column(db.Integer, default=0) 
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # 多対多のリレーションシップ (HistoryCategoryMasterへ)
    categories = db.relationship(
        'HistoryCategoryMaster',
        secondary=developmental_history_categories_association,
        back_populates='history_items',
        lazy='dynamic'
    )
    
    # Userモデルへの参照
    user = db.relationship('User', back_populates='developmental_history_items')

    def __repr__(self):
        return f'<DevelopmentalHistoryItem {self.id} (User: {self.user_id})>'