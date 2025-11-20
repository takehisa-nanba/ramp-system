# 🚨 修正点: 'from backend.app.extensions' (絶対参照)
from backend.app.extensions import db
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, Text, func

# ====================================================================
# 1. AcquisitionActivityLog (利用者獲得活動ログ)
# ====================================================================
class AcquisitionActivityLog(db.Model):
    """
    利用者獲得のための営業・広報活動（アウトリーチ）のログ。
    どの活動が成果（リード獲得）に繋がったかを追跡する（原理4）。
    """
    __tablename__ = 'acquisition_activity_logs'
    
    id = Column(Integer, primary_key=True)
    
    # どの職員が活動したか
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False, index=True)
    
    activity_timestamp = Column(DateTime, nullable=False, default=func.now())
    
    # (例: 'HOSPITAL_VISIT', 'CONSULTATION_MEETING', 'PHONE_OUTREACH')
    activity_type = Column(String(50), nullable=False) 
    
    # どの外部機関（マスター）に対する活動か
    organization_id = Column(Integer, ForeignKey('organizations.id'))
    
    # (例: 'LEAD_GENERATED', 'FOLLOW_UP_SCHEDULED', 'NO_RESULT')
    result_status = Column(String(50)) 
    
    # この活動によって獲得（または関連）した見込み客
    prospect_user_id = Column(Integer, ForeignKey('users.id'), index=True)
    
    activity_summary = Column(Text) # 活動概要
    
    # --- リレーションシップ ---
    supporter = relationship('Supporter', foreign_keys=[supporter_id])
    organization = relationship('Organization', foreign_keys=[organization_id])
    prospect_user = relationship('User', foreign_keys=[prospect_user_id])