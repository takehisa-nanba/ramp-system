# backend/app/models/compliance/audit_tracking.py

from backend.app.extensions import db
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, func

class UnresolvedRiskCounter(db.Model):
    """
    管理者への未対応リスクを可視化・保護するために記録するモデル (URAC)。
    """
    __tablename__ = 'unresolved_risk_counters'
    
    id = Column(Integer, primary_key=True)
    
    # 最終責任者（対応を保留している管理者）
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False, index=True)
    
    # リスクの種類 (例: 'PLAN_REVIEW_OVERDUE', 'PII_ACCESS_VIOLATION')
    risk_type = Column(String(50), nullable=False)
    
    # 未対応状態の継続回数
    cumulative_count = Column(Integer, default=1, nullable=False)
    
    # 最後に警告が保留された日時
    last_unresolved_at = Column(DateTime, default=func.now(), nullable=False)

    # 追跡対象（例：どの計画の期限を無視したか）
    linked_entity_id = Column(Integer, nullable=True, index=True)
    linked_entity_type = Column(String(50), nullable=True)

    # 複合一意キー: 同じ管理者が同じタイプのリスクを追跡
    __table_args__ = (
        UniqueConstraint('supporter_id', 'risk_type', name='uq_urac_supporter_risk'),
    )