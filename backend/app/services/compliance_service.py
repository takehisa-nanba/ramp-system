# 🚨 修正点: 'from backend.app.extensions' (絶対参照)
from backend.app.extensions import db
from backend.app.models import (
    IncidentReport, ComplaintLog, 
    CommitteeActivityLog, TrainingLog, OfficeTrainingEvent,
    Supporter, CommitteeTypeMaster
)
from sqlalchemy import func
# ★ 修正: timezone をインポート
from datetime import datetime, timezone

class ComplianceService:
    """
    Handles compliance, risk management, and staff training workflows.
    Ensures audit trails for incidents and mandatory activities (Principle 1).
    """

    # ====================================================================
    # 1. インシデント管理 (Risk Management)
    # ====================================================================

    def report_incident(self, reporter_id: int, incident_data: dict) -> IncidentReport:
        """
        Creates a new incident report in DRAFT or PENDING status.
        """
        report = IncidentReport(
            reporting_staff_id=reporter_id,
            user_id=incident_data.get('user_id'),
            incident_type=incident_data.get('incident_type'),
            occurrence_timestamp=incident_data.get('occurrence_timestamp'),
            detailed_description=incident_data.get('detailed_description'),
            cause_analysis=incident_data.get('cause_analysis'),
            preventive_action_plan=incident_data.get('preventive_action_plan'),
            report_status='PENDING_APPROVAL'
        )
        
        db.session.add(report)
        db.session.commit()
        return report

    def approve_incident_report(self, report_id: int, approver_id: int) -> IncidentReport:
        """
        Finalizes an incident report, locking it for audit.
        """
        report = db.session.get(IncidentReport, report_id)
        if not report:
            raise ValueError("Incident report not found.")
            
        report.report_status = 'FINALIZED'
        report.approver_id = approver_id
        # ★ 修正: utcnow() -> now(timezone.utc)
        report.approved_at = datetime.now(timezone.utc)
        
        db.session.commit()
        return report

    # ====================================================================
    # 2. 委員会・研修管理 (Mandatory Activities)
    # ====================================================================
    
    def check_committee_compliance(self, office_id: int, committee_type_id: int) -> dict:
        """
        Checks if the mandatory committee meetings have been held within
        the required frequency (Principle 1).
        """
        committee_type = db.session.get(CommitteeTypeMaster, committee_type_id)
        if not committee_type or not committee_type.required_frequency_months:
            return {"status": "UNKNOWN", "message": "No frequency defined."}
            
        # Get the last log for this committee at this office
        last_log = CommitteeActivityLog.query.filter_by(
            office_id=office_id,
            committee_type_id=committee_type_id
        ).order_by(CommitteeActivityLog.meeting_timestamp.desc()).first()
        
        if not last_log:
            return {"status": "NON_COMPLIANT", "message": "No record found."}
            
        # ★ 修正: タイムゾーン対応 (Naive vs Aware の比較問題を回避)
        now = datetime.now(timezone.utc)
        last_meeting = last_log.meeting_timestamp
        
        # DBから来た日時がNaive(タイムゾーンなし)の場合、UTCとして扱う
        if last_meeting.tzinfo is None:
            last_meeting = last_meeting.replace(tzinfo=timezone.utc)
            
        months_since = (now - last_meeting).days / 30
        
        if months_since > committee_type.required_frequency_months:
             return {"status": "NON_COMPLIANT", "message": f"Overdue by {months_since - committee_type.required_frequency_months:.1f} months."}
             
        return {"status": "COMPLIANT", "last_meeting": last_log.meeting_timestamp}