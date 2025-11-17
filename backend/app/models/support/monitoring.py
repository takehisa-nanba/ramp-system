from ...extensions import db
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, Text, func

# ====================================================================
# 1. MonitoringReport (モニタリング報告書)
# ====================================================================
class MonitoringReport(db.Model):
    """
    モニタリング報告書（計画の見直しイベント）。
    計画が「作りっぱなし」になるムダを排除し、
    法定期間内の見直し（減算リスク回避）を担保する。
    """
    __tablename__ = 'monitoring_reports'
    
    id = Column(Integer, primary_key=True)
    
    # どの計画に対する見直しか
    support_plan_id = Column(Integer, ForeignKey('support_plans.id'), nullable=False, index=True)
    
    # 誰が実施したか
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False, index=True) # 担当サビ管など
    
    # --- 法令遵守（原理1） ---
    report_date = Column(Date, nullable=False) # モニタリング実施日
    
    # --- 証憑（原理4） ---
    # モニタリング結果のテキスト（システムがPDF化）
    monitoring_summary = Column(Text, nullable=False) 
    
    # --- 同意（原理1） ---
    # このモニタリング報告書に対する同意ログ (DocumentConsentLogへ紐づく)
    # consent_id = Column(Integer, ForeignKey('document_consent_logs.id'))
    
    # --- リレーションシップ ---
    plan = relationship('SupportPlan')
    supporter = relationship('Supporter')