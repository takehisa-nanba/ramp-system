# backend/app/models/support/support_plan.py
from backend.app.extensions import db
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, Text, func

# ====================================================================
# 1. CaseConferenceLog (ケース会議ログ)
# ====================================================================
class CaseConferenceLog(db.Model):
    """
    ケース会議の発動、記録、および決定事項を追跡するモデル。
    「分からない」を組織の知恵に変えるトリガー（随時）と、
    定期的な見直し（定例）の両方を管理する。
    """
    __tablename__ = 'case_conference_logs'
    
    id = Column(Integer, primary_key=True)
    
    # ----------------------------------------------------------------------
    # 1. 会議の性質
    # ----------------------------------------------------------------------
    # 発動/主催した職員
    initiator_supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False, index=True)
    # 対象利用者
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # ★ NEW: 会議種別 (例: 'AD_HOC', 'REGULAR', 'EMERGENCY')
    # 定例会議か、何かをきっかけとした随時会議かを区別する
    conference_type = Column(String(50), default='AD_HOC', nullable=False)
    
    # 会議発動の根拠となるログ (例: 'DailyLog:123', 'Incident:45')
    # 定例会議の場合は NULL になることもある
    triggering_log_reference = Column(String(100)) 
    
    # 懸念事項または議題の要約 (NULL禁止)
    concern_summary = Column(Text, nullable=False)

    # ----------------------------------------------------------------------
    # 2. 会議の決定と行動計画
    # ----------------------------------------------------------------------
    # 会議の開催日時
    conference_datetime = Column(DateTime, nullable=False, default=func.now())
    
    # 会議で決定されたアクション (例: 計画変更, 外部連携, 職員配置の変更)
    agreed_action = Column(Text, nullable=False)
    
    # 新しい支援計画の方向性 (SupportPlanへの更新指示)
    plan_direction_update = Column(Text)
    
    # 外部連携の必要性 (ExternalCollaborationLogへのリンクを想定)
    external_collaboration_required = Column(Boolean, default=False)

    # ----------------------------------------------------------------------
    # 3. ナレッジ共有 (原理2)
    # ----------------------------------------------------------------------
    # 問題の所在タグ (masters/master_definitions.py の IssueCategoryMaster を参照)
    # これにより、過去の類似ケースを「辞書」として検索可能にする
    issue_category_id = Column(Integer, ForeignKey('issue_category_master.id'))

    # ----------------------------------------------------------------------
    # 4. メタデータ
    # ----------------------------------------------------------------------
    created_at = Column(DateTime, default=func.now())

    # リレーション定義
    initiator = db.relationship('Supporter', foreign_keys=[initiator_supporter_id])
    user = db.relationship('User', back_populates='case_conferences')
    issue_category = db.relationship('IssueCategoryMaster')