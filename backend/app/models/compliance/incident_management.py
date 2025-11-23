# backend/app/models/compliance/incident_management.py

# 修正点: 'from backend.app.extensions' (絶対参照)
from backend.app.extensions import db
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
    
    user = db.relationship('User')
    reporting_staff = db.relationship('Supporter', foreign_keys=[reporting_staff_id])
    approver = db.relationship('Supporter', foreign_keys=[approver_id])
    issue_category = db.relationship('IssueCategoryMaster')

# ====================================================================
# 2. ComplaintLog (苦情対応記録)
# ====================================================================
class ComplaintLog(db.Model):
    """
    苦情対応記録。
    「誰に関する苦情か（target_user）」を軸に管理し、関係機関との紐づけも辿れるようにする。
    """
    __tablename__ = 'complaint_logs'
    
    id = Column(Integer, primary_key=True)
    
    # ★ 修正: 申立人IDではなく「対象利用者ID」とする
    # NULLの場合は「事業所全体」または「特定個人ではない」苦情として扱う
    target_user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    
    # 申立人の属性 (例: 'USER', 'FAMILY', 'RELATED_ORG', 'NEIGHBOR', 'ANONYMOUS')
    complainant_type = Column(String(50), nullable=False) 
    
    # 申立人の詳細（名前や連絡先をテキストで記録）
    # 関係機関の場合は「〇〇相談支援事業所 田中氏」のように記述
    complainant_name = Column(String(100)) 
    complainant_contact_info = Column(String(255)) 
    
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
    
    # ★ 修正: overlapsを追加して警告を消す
    # Userモデル側の 'complaints' との関係を整理
    # target_user とすることで、Userモデルから見た「自分に関する苦情」として取得可能にする
    target_user = db.relationship(
        'User', 
        foreign_keys=[target_user_id], 
        overlaps="complaints"
    )
    
    responsible_supporter = db.relationship('Supporter', foreign_keys=[responsible_supporter_id])