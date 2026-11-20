from backend.app.extensions import db


class PlanAssessment(db.Model):
    """本人との面談記録。新規または次期の原案一件の根拠となる。"""
    __tablename__ = "plan_assessments"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.ForeignKey("users.id"), nullable=False, index=True)
    office_service_configuration_id = db.Column(db.ForeignKey("office_service_configurations.id"))
    plan_id = db.Column(db.ForeignKey("support_plans.id"), unique=True)
    supporter_id = db.Column(db.ForeignKey("supporters.id"), nullable=False)
    interview_date = db.Column(db.Date, nullable=False)
    method = db.Column(db.String(20), nullable=False)
    exception_reason = db.Column(db.Text)
    summary = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
