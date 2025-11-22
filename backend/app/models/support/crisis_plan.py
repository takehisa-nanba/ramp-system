# backend/app/models/support/support_plan.py
from backend.app.extensions import db
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, Text, func

# ====================================================================
# 1. CrisisPlan (危機対応計画)
# ====================================================================
class CrisisPlan(db.Model):
    """
    利用者個別の危機対応計画（クライシスプラン）。
    緊急時の対応（サイン、対処法、連絡先）を管理する。
    """
    __tablename__ = 'crisis_plans'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # --- 計画の基本情報 ---
    version = Column(Integer, default=1, nullable=False)
    effective_date = Column(Date, nullable=False) # 適用開始日
    review_date = Column(Date) # 次回レビュー予定日
    
    # --- 主要なクライシス要素（原理2：質の均一化） ---
    crisis_signs = Column(Text)      # 危機状態の兆候（何をサインと捉えるか）
    coping_strategies = Column(Text) # 対処方法（利用者、職員が取るべき行動）
    emergency_contacts_detail = Column(Text) # 緊急連絡先、医療機関情報など（Textで詳細を保持）
    
    # --- 監査証跡（原理1） ---
    created_by_supporter_id = Column(Integer, ForeignKey('supporters.id'))
    
    # --- タイムスタンプ ---
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # --- リレーションシップ ---
    user = db.relationship('User', back_populates='crisis_plans')
    creator = db.relationship('Supporter', foreign_keys=[created_by_supporter_id])
    
    # 監査ログ（`compliance`パッケージ）への逆参照
    # crisis_logs = db.relationship('CrisisLog', back_populates='plan', cascade="all, delete-orphan")