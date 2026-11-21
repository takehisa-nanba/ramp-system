"""Service-specific content; lifecycle and consent belong to SupportPlan."""
from backend.app.extensions import db
from backend.app.utils.custom_types import EncryptedString

retention_plan_organization_links = db.Table('retention_plan_organization_links',
    db.Column('plan_detail_id', db.Integer, db.ForeignKey('job_retention_plan_details.id'), primary_key=True),
    db.Column('user_organization_link_id', db.Integer, db.ForeignKey('user_organization_links.id'), primary_key=True))


class RetentionEncryptedText(EncryptedString):
    """Use the shared cipher, but fail closed rather than silently storing NULL."""
    cache_ok = True

    def process_bind_param(self, value, dialect):
        result = super().process_bind_param(value, dialect)
        if value is not None and result is None:
            raise ValueError('Retention private text encryption failed')
        return result

    def process_result_value(self, value, dialect):
        result = super().process_result_value(value, dialect)
        if value is not None and result is None:
            raise ValueError('Retention private text decryption failed')
        return result


class JobRetentionPlanDetail(db.Model):
    __tablename__ = 'job_retention_plan_details'
    id = db.Column(db.Integer, primary_key=True)
    support_plan_id = db.Column(db.Integer, db.ForeignKey('support_plans.id'), nullable=False, unique=True)
    job_placement_id = db.Column(db.Integer, db.ForeignKey('job_placement_logs.id'), nullable=True, index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('supporters.id'), nullable=False)
    version = db.Column(db.Integer, nullable=False, default=1)
    handover_notes = db.Column(db.Text)
    physical_work_environment = db.Column(db.Text)
    human_work_environment = db.Column(db.Text)
    job_description = db.Column(db.Text)
    contract_wage = db.Column(db.Text)
    holidays = db.Column(db.Text)
    daily_work_hours = db.Column(db.Text)
    break_time = db.Column(db.Text)
    health_status_notes = db.Column(RetentionEncryptedText())
    living_environment_notes = db.Column(RetentionEncryptedText())
    user_needs = db.Column(db.Text)
    special_notes = db.Column(db.Text)
    overall_evaluation = db.Column(db.Text)
    evaluation_date = db.Column(db.Date)
    evaluation_author_id = db.Column(db.Integer, db.ForeignKey('supporters.id'))
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now(), onupdate=db.func.now())
    plan = db.relationship('SupportPlan', back_populates='retention_detail')
    job_placement = db.relationship('JobPlacementLog')
    organization_links = db.relationship('UserOrganizationLink', secondary=retention_plan_organization_links)
    support_items = db.relationship('JobRetentionPlanSupportItem', back_populates='detail', order_by='JobRetentionPlanSupportItem.sequence_no')


class JobRetentionPlanSupportItem(db.Model):
    __tablename__ = 'job_retention_plan_support_items'
    id = db.Column(db.Integer, primary_key=True)
    plan_detail_id = db.Column(db.Integer, db.ForeignKey('job_retention_plan_details.id'), nullable=False, index=True)
    sequence_no = db.Column(db.Integer, nullable=False)
    support_policy_content = db.Column(db.Text, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    frequency = db.Column(db.Text, nullable=False)
    implementation_status = db.Column(db.String(20))
    achievement_status = db.Column(db.String(20))
    effect_satisfaction_notes = db.Column(db.Text)
    remaining_issues_and_actions = db.Column(db.Text)
    deleted_at = db.Column(db.DateTime)
    deleted_by_id = db.Column(db.Integer, db.ForeignKey('supporters.id'))
    delete_reason = db.Column(db.Text)
    detail = db.relationship('JobRetentionPlanDetail', back_populates='support_items')
    __table_args__ = (
        db.UniqueConstraint('plan_detail_id', 'sequence_no', name='uq_retention_item_sequence'),
        db.CheckConstraint('sequence_no > 0', name='ck_retention_item_sequence'),
        db.CheckConstraint('start_date <= end_date', name='ck_retention_item_period'),
        db.CheckConstraint("implementation_status IN ('DONE','PARTIAL','NOT_DONE')", name='ck_retention_item_implementation'),
        db.CheckConstraint("achievement_status IN ('ACHIEVED','PARTIAL','NOT_ACHIEVED')", name='ck_retention_item_achievement'),
    )
