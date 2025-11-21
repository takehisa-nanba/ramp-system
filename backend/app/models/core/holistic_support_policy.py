# 🚨 修正点: 'from backend.app.extensions' (絶対参照)
from backend.app.extensions import db
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, Text, func

# ====================================================================
# 1. HolisticSupportPolicy (総合支援方針と本人の意向)
# ====================================================================
class HolisticSupportPolicy(db.Model):
    """
    利用者の総合支援方針と本人の意向（履歴管理）。
    計画(SupportPlan)に依存しない、支援の核となる文書。
    Userと1対多の関係で、変更履歴をすべて保持する。
    """
    __tablename__ = 'holistic_support_policies'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # --- 履歴管理（原理1） ---
    effective_date = Column(Date, nullable=False) # 適用開始日
    
    # --- 責務の分離（原理2） ---
    user_intention_content = Column(Text, nullable=False) # 本人の意向
    support_policy_content = Column(Text, nullable=False) # 支援の方針（専門職の判断）
    support_considerations = Column(Text) # 障害特性・留意点
    
    # --- タイムスタンプ ---
    created_at = Column(DateTime, default=func.now())
    
    # --- リレーションシップ ---
    user = db.relationship('User', back_populates='holistic_policies')