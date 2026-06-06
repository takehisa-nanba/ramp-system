from backend.app.extensions import db
from backend.app.models import MonitoringReport, SupportPlan, AuditActionLog
from backend.app.utils.errors import NotFoundError
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class MonitoringService:
    def create_monitoring_report(self, plan_id: int, supporter_id: int, report_date: datetime.date, summary: str, goal_notes: str = None, context: str = None) -> MonitoringReport:
        """
        モニタリングを実施し、評価を記録する。
        （次期計画の作成判定は SupportPlanService 側で行う）
        """
        plan = db.session.get(SupportPlan, plan_id)
        if not plan:
            raise NotFoundError("Support Plan not found")
            
        report = MonitoringReport(
            support_plan_id=plan_id,
            supporter_id=supporter_id,
            report_date=report_date,
            monitoring_summary=summary,
            target_goal_progress_notes=goal_notes,
            contextual_analysis=context
        )
        db.session.flush() # get ID
        
        audit_log = AuditActionLog(
            action="CREATE_MONITORING_REPORT",
            user_id=plan.user_id,
            actor_supporter_id=supporter_id,
            entity_type="MonitoringReport",
            entity_id=report.id,
            reason=f"Monitoring report created for Plan {plan_id}"
        )
        db.session.add(audit_log)
        
        logger.info(f"Monitoring report created for Plan {plan_id} by Supporter {supporter_id}")
        return report

    def complete_monitoring(self, report_id: int, document_url: str = None):
        """
        モニタリング報告を完了し、証憑を保存する。
        """
        report = db.session.get(MonitoringReport, report_id)
        if not report:
            raise NotFoundError("Monitoring Report not found")
            
        if document_url:
            report.document_url = document_url
            
        # user_id を特定するため、SupportPlanを経由
        plan = db.session.get(SupportPlan, report.support_plan_id)
        user_id = plan.user_id if plan else None
        
        audit_log = AuditActionLog(
            action="COMPLETE_MONITORING_REPORT",
            user_id=user_id,
            actor_supporter_id=report.supporter_id,
            entity_type="MonitoringReport",
            entity_id=report.id,
            reason=f"Monitoring report {report_id} completed."
        )
        db.session.add(audit_log)
            
        logger.info(f"Monitoring report {report_id} completed.")
        return report
