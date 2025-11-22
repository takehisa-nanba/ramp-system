# backend/app/models/support/follow_up.py
from backend.app.extensions import db
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, Text, func

# ====================================================================
# 1. PostTransitionFollowUp (移行後6ヶ月の義務的支援ログ)
# ====================================================================
class PostTransitionFollowUp(db.Model):
    """
    移行後6ヶ月の義務的支援（就職後フォローアップ）の記録。
    基本報酬の範囲内で行う活動の証跡（原理1）。
    請求対象のJobRetentionRecordとは責務を分離する（原理3）。
    """
    __tablename__ = 'post_transition_follow_ups'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    record_date = Column(Date, nullable=False) # 支援実施日
    
    # 支援方法 (例: '企業訪問', '利用者面談（対面）', '利用者面談（電話/オンライン）')
    support_method = Column(String(50), nullable=False)
    
    support_details = Column(Text, nullable=False) # 支援内容 (NULL禁止)
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False) # 担当職員
    
    # --- 証憑（原理1） ---
    document_url = Column(String(500)) # 詳細な面談記録票や確認書などのファイルURL
    
    # --- タイムスタンプ ---
    created_at = Column(DateTime, default=func.now())
    
    # --- リレーションシップ ---
    user = db.relationship('User', back_populates='follow_ups')
    supporter = db.relationship('Supporter', foreign_keys=[supporter_id])