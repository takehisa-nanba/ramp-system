# backend/app/models/finance/billing_data.py (新規ファイル)

from backend.app.extensions import db
from sqlalchemy import Column, Integer, String, Date, Numeric, ForeignKey, DateTime, Text, Boolean, func

class BillingData(db.Model):
    """
    確定した請求データ (初期請求、日次変動費など)。
    三段監査ロジックが適用された最終監査証跡となる。
    """
    __tablename__ = 'billing_data'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # 請求根拠 (Plan-Activity ガードレール)
    plan_id = Column(Integer, ForeignKey('support_plans.id'), nullable=True, index=True)
    daily_log_id = Column(Integer, ForeignKey('daily_logs.id'), nullable=True, index=True)
    
    # 請求詳細
    service_type = Column(String(50), nullable=False)
    billing_date = Column(Date, nullable=False)
    unit_count = Column(Integer, nullable=False)
    cost = Column(Numeric(10, 2), nullable=False)
    
    # 三段監査の結果 (監査の堅牢性)
    is_audit_passed = Column(Boolean, default=False)
    audit_notes = Column(Text)
    
    created_at = Column(DateTime, default=func.now())
    
    user = db.relationship('User', back_populates='billings')
    support_plan = db.relationship('SupportPlan', back_populates='billings')
    daily_log = db.relationship('DailyLog', back_populates='billing_data')