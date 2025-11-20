# 🚨 修正点: 'from backend.app.extensions' (絶対参照)
from backend.app.extensions import db
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, Text, func

# ====================================================================
# 1. IncidentReport (事故・ヒヤリハット報告 / 再発防止)
# ====================================================================
class IncidentReport(db.Model):
    """
    事故・ヒヤリハット報告（リスクマネジメントの核）。
    「事実の記録」と「再発防止策の追跡」を担う（原理1）。
    「問題の所在」タグ付けにより、ナレッジベース化する（原理2）。
    """
    __tablename__ = 'incident_reports'
    
    id = Column(Integer, primary_key=True)
    
    # 関連する利用者・職員
    user_id = Column(Integer, ForeignKey('users.id'), index=True)
    reporting_staff_id = Column(Integer, ForeignKey('supporters.id'), nullable=False, index=True) # 報告職員
    
    # (例: 'ACCIDENT', 'NEAR_MISS')
    incident_type = Column(String(30), nullable=False, index=True) 
    
    # ナレッジ共有のためのタグ (masters/master_definitions.py の IssueCategoryMaster を参照)
    issue_category_id = Column(Integer, ForeignKey('issue_category_master.id'))
    
    occurrence_timestamp = Column(DateTime, nullable=False, default=func.now()) # 発生日時
    detailed_description = Column(Text, nullable=False) # 詳細 (NULL禁止)
    
    # --- 監査証跡（原理1） ---
    cause_analysis = Column(Text, nullable=False) # 原因分析 (NULL禁止)
    preventive_action_plan = Column(Text, nullable=False) # 再発防止策 (NULL禁止)
    
    # --- 意味のポケット（原理2：ポジティブな転換） ---
    # トラブルの中に潜んでいた、肯定的な変化や兆し（任意）
    positive_turning_point = Column(Text)
    
    # --- ワークフロー ---
    # (DRAFT, PENDING_APPROVAL, FINALIZED)
    report_status = Column(String(30), default='DRAFT', nullable=False)
    approver_id = Column(Integer, ForeignKey('supporters.id')) # 管理者承認
    approved_at = Column(DateTime) # ロック日時
    
    user = relationship('User')
    reporting_staff = relationship('Supporter', foreign_keys=[reporting_staff_id])
    approver = relationship('Supporter', foreign_keys=[approver_id])
    issue_category = relationship('IssueCategoryMaster')

# ====================================================================
# 2. ComplaintLog (苦情対応記録)
# ====================================================================
class ComplaintLog(db.Model):
    """
    苦情対応記録。
    受付から解決までのプロセスを厳格に記録する（原理1, 6）。
    """
    __tablename__ = 'complaint_logs'
    
    id = Column(Integer, primary_key=True)
    
    # 苦情申立人（利用者、家族、外部機関など）
    complainant_user_id = Column(Integer, ForeignKey('users.id'), index=True)
    complainant_name = Column(String(100)) # 外部者の場合
    complainant_type = Column(String(50), nullable=False) # (例: 'USER', 'FAMILY', 'ORGANIZATION')
    
    reception_timestamp = Column(DateTime, nullable=False, default=func.now()) # 受付日時
    complaint_summary = Column(Text, nullable=False) # 苦情概要 (NULL禁止)
    
    # --- 監査証跡（原理1） ---
    investigation_details = Column(Text) # 調査内容
    resolution_action_taken = Column(Text) # 解決策・対応
    
    # --- ワークフロー ---
    # (RECEIVED, INVESTIGATING, RESOLVED, CLOSED)
    complaint_status = Column(String(30), default='RECEIVED', nullable=False)
    
    closure_timestamp = Column(DateTime) # 最終解決日時
    responsible_supporter_id = Column(Integer, ForeignKey('supporters.id')) # 対応責任者
    
    user = relationship('User', foreign_keys=[complainant_user_id])
    responsible_supporter = relationship('Supporter', foreign_keys=[responsible_supporter_id])