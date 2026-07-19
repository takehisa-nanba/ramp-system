from backend.app.extensions import db
from sqlalchemy import Column, Integer, String, Date, DateTime, Text, ForeignKey, Numeric

class StaffingCalculationRun(db.Model):
    """
    常勤換算の計算処理の実行単位
    """
    __tablename__ = 'staffing_calculation_runs'
    
    id = Column(Integer, primary_key=True)
    office_service_configuration_id = Column(Integer, ForeignKey('office_service_configurations.id'), nullable=False, index=True)
    
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    
    calculation_basis = Column(Text, nullable=True) # 計算根拠メモ等
    rule_snapshot_at = Column(DateTime, nullable=False) # 計算時点
    
    # DRAFT, CALCULATED, CONFIRMED, SUPERSEDED
    status = Column(String(20), default='DRAFT', nullable=False)
    
    office_service_configuration = db.relationship('OfficeServiceConfiguration')
    results = db.relationship('StaffingCalculationResult', back_populates='run', cascade='all, delete-orphan')

    __table_args__ = (
        db.CheckConstraint('period_start <= period_end', name='chk_run_period_dates'),
    )

class StaffingCalculationResult(db.Model):
    """
    配置(Assignment)単位の計算結果
    """
    __tablename__ = 'staffing_calculation_results'
    
    id = Column(Integer, primary_key=True)
    staffing_calculation_run_id = Column(Integer, ForeignKey('staffing_calculation_runs.id'), nullable=False, index=True)
    supporter_job_assignment_id = Column(Integer, ForeignKey('supporter_job_assignments.id'), nullable=False, index=True)
    
    ordinary_minutes = Column(Integer, default=0, nullable=False)
    exception_minutes = Column(Integer, default=0, nullable=False)
    total_counted_minutes = Column(Integer, default=0, nullable=False)
    
    # FTEの分母となった常勤所定時間スナップショット
    full_time_required_minutes = Column(Integer, nullable=False)
    
    # fte_valueはNumeric/Decimalを使用
    fte_value = Column(Numeric(precision=5, scale=2), default=0.00, nullable=False)
    
    run = db.relationship('StaffingCalculationRun', back_populates='results')
    assignment = db.relationship('SupporterJobAssignment')
    result_exceptions = db.relationship('StaffingCalculationResultException', back_populates='result', cascade='all, delete-orphan')
    
    __table_args__ = (
        db.CheckConstraint('ordinary_minutes >= 0', name='chk_result_ordinary_minutes_positive'),
        db.CheckConstraint('exception_minutes >= 0', name='chk_result_exception_minutes_positive'),
        db.CheckConstraint('total_counted_minutes >= 0', name='chk_result_total_minutes_positive'),
        db.CheckConstraint('full_time_required_minutes > 0', name='chk_result_ft_required_minutes_positive'),
        db.CheckConstraint('fte_value >= 0', name='chk_result_fte_positive'),
    )
    
class StaffingCalculationResultException(db.Model):
    """
    結果算出に使われた特例履歴スナップショット
    """
    __tablename__ = 'staffing_calculation_result_exceptions'
    
    id = Column(Integer, primary_key=True)
    staffing_calculation_result_id = Column(Integer, ForeignKey('staffing_calculation_results.id'), nullable=False, index=True)
    staffing_calculation_exception_id = Column(Integer, ForeignKey('staffing_calculation_exceptions.id'), nullable=False, index=True)
    
    # 計算時点の情報をすべてコピーして保存
    applied_rule_code = Column(String(50), nullable=False)
    applied_rule_name = Column(String(200), nullable=False)
    applied_legal_basis = Column(Text, nullable=True)
    rule_effective_from = Column(Date, nullable=False)
    rule_effective_to = Column(Date, nullable=True)
    
    added_minutes = Column(Integer, default=0, nullable=False)
    source_assignment_id = Column(Integer, ForeignKey('supporter_job_assignments.id'), nullable=False)
    target_assignment_id = Column(Integer, ForeignKey('supporter_job_assignments.id'), nullable=False)
    
    result = db.relationship('StaffingCalculationResult', back_populates='result_exceptions')
    exception = db.relationship('StaffingCalculationException')

    __table_args__ = (
        db.CheckConstraint('added_minutes >= 0', name='chk_result_exception_added_minutes_positive'),
        db.CheckConstraint('rule_effective_to IS NULL OR rule_effective_from <= rule_effective_to', name='chk_result_exception_effective_dates'),
    )
