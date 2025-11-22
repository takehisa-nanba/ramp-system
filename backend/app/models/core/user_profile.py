# backend/app/models/core/user_profile.py
from backend.app.extensions import db
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text

# ====================================================================
# 1. UserProfile (利用者の詳細情報)
# ====================================================================
class UserProfile(db.Model):
    """
    利用者の詳細情報（Userモデルの1対1拡張）。
    PIIとは異なる、支援に必要な補足情報を管理する。
    """
    __tablename__ = 'user_profiles'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    
    # 支援に必要な詳細な情報
    emergency_contact_notes = Column(Text) # 緊急連絡先に関する特記事項
    insurance_details = Column(Text) # 健康保険情報など
    
    # Userモデルへのリレーション (1対1)
    user = db.relationship('User', back_populates='profile', uselist=False)

# ====================================================================
# 2. FamilyMember (家族構成)
# ====================================================================
class FamilyMember(db.Model):
    """家族構成（Userと1対多）"""
    __tablename__ = 'family_members'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    name = Column(String(100), nullable=False)
    relation = Column(String(50)) # 続柄
    phone_number = Column(String(20))
    is_main_contact = Column(Boolean, default=False) # メインの連絡先か
    
    user = db.relationship('User', back_populates='family_members')

# ====================================================================
# 3. EmergencyContact (緊急連絡先)
# ====================================================================
class EmergencyContact(db.Model):
    """緊急連絡先（Userと1対多）"""
    __tablename__ = 'emergency_contacts'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    name = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=False)
    relation = Column(String(50)) # 続柄

    user = db.relationship('User', back_populates='emergency_contacts')