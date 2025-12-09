# backend/app/models/compliance/audit_tracking.py

from backend.app.extensions import db
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, func

class UnresponsiveRiskCounter(db.Model):
    """
    管理者による構造化ブロックの無視を客観的な指標として記録するモデル (URAC)。
    """
    __tablename__ = 'unresponsive_risk_counters'
    
    id = Column(Integer, primary_key=True)
    
    # 最終責任者（無視した管理者）
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False, index=True)
    
    # リスクの種類 (例: 'PLAN_REVIEW_OVERDUE', 'PII_ACCESS_VIOLATION')
    risk_type = Column(String(50), nullable=False)
    
    # 無視された警告の累積回数
    cumulative_count = Column(Integer, default=1, nullable=False)
    
    # 最後に警告を無視した日時
    last_ignored_at = Column(DateTime, default=func.now(), nullable=False)

    # 追跡対象（例：どの計画の期限を無視したか）
    linked_entity_id = Column(Integer, nullable=True, index=True)
    linked_entity_type = Column(String(50), nullable=True)

    # 複合一意キー: 同じ管理者が同じタイプのリスクを追跡
    __table_args__ = (
        UniqueConstraint('supporter_id', 'risk_type', name='uq_urac_supporter_risk'),
    )