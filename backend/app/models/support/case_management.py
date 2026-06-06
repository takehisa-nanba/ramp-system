# backend/app/models/support/case_management.py

# 修正点: 'from backend.app.extensions' (絶対参照)
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
    # 3.5. 支援計画サイクル連携 (本人同席・遅延監査)
    # ----------------------------------------------------------------------
    support_plan_id = Column(Integer, ForeignKey('support_plans.id'), nullable=True, index=True)
    user_participated = Column(Boolean, default=True, nullable=False) # 本人参加フラグ
    reason_for_user_absence = Column(Text, nullable=True) # 本人不在のやむを得ない理由
    is_sabikan_digital_declaration = Column(Boolean, default=False, nullable=False) # サビ管デジタル宣誓
    absence_monitoring_summary = Column(Text, nullable=True) # 不在時の状況モニタリング概要

    # ----------------------------------------------------------------------
    # 4. メタデータ
    # ----------------------------------------------------------------------
    created_at = Column(DateTime, default=func.now())

    # リレーション定義
    initiator = db.relationship('Supporter', foreign_keys=[initiator_supporter_id])
    user = db.relationship('User', back_populates='case_conferences')
    issue_category = db.relationship('IssueCategoryMaster')
    support_plan = db.relationship('SupportPlan', backref=db.backref('case_conference_logs', lazy='dynamic'))

    # 論理削除用フィールド
    deleted_at = Column(DateTime, nullable=True)
    deleted_by_id = Column(Integer, ForeignKey('supporters.id'), nullable=True)
    delete_reason = Column(String(255), nullable=True)

class CaseConferenceParticipant(db.Model):
    """
    ケース会議の参加者（複数）を管理するテーブル。
    """
    __tablename__ = 'case_conference_participants'
    
    id = Column(Integer, primary_key=True)
    case_conference_log_id = Column(Integer, ForeignKey('case_conference_logs.id'), nullable=False, index=True)
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False, index=True)
    
    # 参加者としての役割など（必要に応じて拡張可能）
    # role = Column(String(50))
    
    created_at = Column(DateTime, default=func.now())
    
    # リレーション
    case_conference_log = db.relationship('CaseConferenceLog', backref=db.backref('participants', lazy='dynamic', cascade='all, delete-orphan'))
    supporter = db.relationship('Supporter')