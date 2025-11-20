# 🚨 修正点: 'from backend.app.extensions' (絶対参照)
from backend.app.extensions import db
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
    
    # --- 評価の内容（原理2：支援の質） ---
    # 全体的なサマリー
    monitoring_summary = Column(Text, nullable=False) 
    
    # 目標ごとの進捗所見 (定性評価)
    target_goal_progress_notes = Column(Text)
    
    # 背景分析 (個人・環境・指導因子など、評価の「文脈」を記録)
    contextual_analysis = Column(Text)
    
    # --- 証憑（原理1） ---
    # 署名済みモニタリング報告書のPDF URL (電子署名またはスキャン)
    document_url = Column(String(500)) 
    
    # --- リレーションシップ ---
    plan = relationship('SupportPlan')
    supporter = relationship('Supporter')