from backend.app.extensions import db
from sqlalchemy import Column, Integer, String, Date, DateTime, Text, ForeignKey, UniqueConstraint

class IntegratedServiceOperation(db.Model):
    """
    一体的運営関係のモデル
    """
    __tablename__ = 'integrated_service_operations'
    
    id = Column(Integer, primary_key=True)
    corporation_id = Column(Integer, ForeignKey('corporations.id'), nullable=False, index=True)
    operation_name = Column(String(200), nullable=False)
    
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    
    status = Column(String(20), default='DRAFT', nullable=False)
    
    approved_by_supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    evidence_document_url = Column(String(2048), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    corporation = db.relationship('Corporation')
    approved_by = db.relationship('Supporter', foreign_keys=[approved_by_supporter_id])
    members = db.relationship('IntegratedServiceOperationMember', back_populates='operation', cascade='all, delete-orphan')

    __table_args__ = (
        db.CheckConstraint('effective_to IS NULL OR effective_from <= effective_to', name='chk_integrated_operation_effective_dates'),
    )

class IntegratedServiceOperationMember(db.Model):
    """
    一体的運営に含まれるサービス（OfficeServiceConfiguration）の紐付け
    """
    __tablename__ = 'integrated_service_operation_members'
    
    id = Column(Integer, primary_key=True)
    integrated_service_operation_id = Column(Integer, ForeignKey('integrated_service_operations.id'), nullable=False, index=True)
    office_service_configuration_id = Column(Integer, ForeignKey('office_service_configurations.id'), nullable=False, index=True)
    
    operation = db.relationship('IntegratedServiceOperation', back_populates='members')
    office_service_configuration = db.relationship('OfficeServiceConfiguration')
    
    __table_args__ = (
        UniqueConstraint('integrated_service_operation_id', 'office_service_configuration_id', name='uq_integrated_operation_member'),
    )
