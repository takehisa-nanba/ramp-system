from backend.app.extensions import db
from sqlalchemy import Column, Integer, String, Date, DateTime, Text, ForeignKey, UniqueConstraint, Boolean

class StaffingCalculationRule(db.Model):
    """
    配置人員の常勤換算等の算定における「特例ルール」の定義マスタ。
    法令や通知に基づく具体的な特例（例：就労移行と就労定着の兼務特例）を管理する。
    """
    __tablename__ = 'staffing_calculation_rules'
    
    id = Column(Integer, primary_key=True)
    rule_code = Column(String(50), nullable=False) # 例: R6_SECHAKU_KENMU
    rule_name = Column(String(200), nullable=False) # 例: 就労移行・就労定着の兼務特例
    
    # 適用される特例の種類 (SIMULTANEOUS_COUNT など)
    rule_type = Column(String(50), nullable=False)
    
    # 法的根拠
    legal_basis = Column(Text)
    description = Column(Text)
    
    # 有効期間
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    
    __table_args__ = (
        UniqueConstraint('rule_code', name='uq_staffing_calculation_rule_code'),
        db.CheckConstraint('effective_to IS NULL OR effective_from <= effective_to', name='chk_rule_effective_dates'),
    )

class StaffingCalculationException(db.Model):
    """
    配置同士の関係に対して、制度上の算入特例を適用した意思決定の証跡。
    """
    __tablename__ = 'staffing_calculation_exceptions'
    
    id = Column(Integer, primary_key=True)
    
    # 適用される特例ルールの定義
    staffing_calculation_rule_id = Column(Integer, ForeignKey('staffing_calculation_rules.id'), nullable=False)
    
    # どの配置とどの配置の組み合わせに対する特例か
    source_assignment_id = Column(Integer, ForeignKey('supporter_job_assignments.id'), nullable=False)
    target_assignment_id = Column(Integer, ForeignKey('supporter_job_assignments.id'), nullable=False)
    
    # 適用期間
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    
    # DRAFT, APPROVED, REVOKED, EXPIRED
    status = Column(String(20), default='DRAFT', nullable=False)
    
    # 承認情報
    approved_by_supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    approval_reason = Column(Text, nullable=True)
    
    # 利用者支援に支障がないことの確認証跡
    no_service_disruption_confirmed = Column(Boolean, default=False, nullable=False)
    no_service_disruption_confirmed_by_supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=True)
    no_service_disruption_confirmed_at = Column(DateTime, nullable=True)
    no_service_disruption_reason = Column(Text, nullable=True)
    evidence_document_url = Column(String(2048), nullable=True)
    
    # 取消情報
    revoked_by_supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    revocation_reason = Column(Text, nullable=True)
    
    # リレーションシップ
    rule = db.relationship('StaffingCalculationRule')
    source_assignment = db.relationship('SupporterJobAssignment', foreign_keys=[source_assignment_id])
    target_assignment = db.relationship('SupporterJobAssignment', foreign_keys=[target_assignment_id])
    approved_by = db.relationship('Supporter', foreign_keys=[approved_by_supporter_id])
    no_service_disruption_confirmed_by = db.relationship('Supporter', foreign_keys=[no_service_disruption_confirmed_by_supporter_id])
    revoked_by = db.relationship('Supporter', foreign_keys=[revoked_by_supporter_id])
    
    __table_args__ = (
        db.CheckConstraint('source_assignment_id != target_assignment_id', name='chk_source_neq_target_assignment'),
        db.CheckConstraint('effective_to IS NULL OR effective_from <= effective_to', name='chk_exception_effective_dates'),
    )
