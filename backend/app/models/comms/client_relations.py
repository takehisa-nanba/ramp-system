# 🚨 修正点: 'from backend.app.extensions' (絶対参照)
from backend.app.extensions import db
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, Text, func

# ====================================================================
# 1. Organization (組織マスター)
# ====================================================================
class Organization(db.Model):
    """
    関係機関のマスターデータ（病院、ハローワーク、相談支援事業所など）。
    情報を一元管理し、重複登録のムダを排除する（原理4）。
    """
    __tablename__ = 'organizations'
    
    id = Column(Integer, primary_key=True)
    
    # 組織の基本情報
    organization_name = Column(String(255), nullable=False, index=True)
    
    # (例: 'HOSPITAL', 'HELLO_WORK', 'CONSULTATION_OFFICE', 'SCHOOL')
    organization_type = Column(String(50), nullable=False, index=True)
    
    # 代表連絡先
    main_phone = Column(String(20))
    main_email = Column(String(120))
    main_address = Column(String(255))
    
    # 逆参照
    user_links = relationship('UserOrganizationLink', back_populates='organization', lazy='dynamic')
    
    def __repr__(self):
        return f'<Organization {self.id}: {self.organization_name}>'

# ====================================================================
# 2. UserOrganizationLink (利用者と組織の連携ログ)
# ====================================================================
class UserOrganizationLink(db.Model):
    """
    「利用者」と「関係機関」を紐づける連携ログ（Many-to-Many）。
    利用者ごとの担当者名や連携開始日を記録する（原理10）。
    """
    __tablename__ = 'user_organization_links'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey('organizations.id'), nullable=False, index=True)
    
    # --- 利用者固有の連携情報 ---
    # (例: 相談支援専門員名、主治医名、担当ジョブコーチ名)
    responsible_person_name = Column(String(100)) 
    
    link_start_date = Column(Date, default=func.now())
    link_end_date = Column(Date) # 連携終了日 (NULLなら継続中)
    
    is_primary_contact = Column(Boolean, default=False) # メインの連携先か（例：計画相談先）
    
    # --- リレーションシップ ---
    user = relationship('User', back_populates='organization_links')
    organization = relationship('Organization', back_populates='user_links')