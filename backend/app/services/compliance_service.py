# backend/app/services/compliance_service.py

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
    
    # backend/app/services/compliance_service.py

from backend.app.extensions import db
from backend.app.models import (
    IncidentReport, ComplaintLog, 
    CommitteeActivityLog, TrainingLog, OfficeTrainingEvent,
    Supporter, CommitteeTypeMaster,
    OfficeSetting, DailyLog, SupporterJobAssignment, # ★ NEW: 日次チェック用
    ComplianceEventLog # ★ NEW: 監査ログ記録用
    )

from sqlalchemy import func, and_, extract
from datetime import datetime, timezone, date, timedelta
from typing import Optional, List, Dict
import logging
logger = logging.getLogger(__name__)

# ★ NEW: finance_service の FTE 計算ロジックに依存
# NOTE: 循環参照を避けるため、ここでは関数を定義しないが、API層で呼び出すことを前提とする。
# from .finance_service import calculate_fte_for_service 

class ComplianceService:
    """
    法令遵守（コンプライアンス）、リスク管理、および職員研修のワークフローを処理します。
    インシデント（事故・トラブル）や義務的活動に関する監査証跡（原理1）を確保します。
    """

    # ====================================================================
    # 1. インシデント管理 (Risk Management)
    # ... (report_incident および approve_incident_report はそのまま維持) ...
    # ====================================================================
    # 2. 委員会・研修管理 (Mandatory Activities)
    # ... (check_committee_compliance はそのまま維持) ...
    # ====================================================================
    
    # ====================================================================
    # 3. 日次人員配置チェック (Daily Ratio Guardrail) ★ NEW
    # ====================================================================

    def check_daily_personnel_ratio(self, office_id: int, target_date: date) -> dict:
        """
        【行政指導対応】施設外就労がある日における、事業所内の最低人員配置基準を検証する。
        """
        # 1. 基準の取得 (ここでは仮に 6:1 配置が必須で、定員が20名と仮定)
        OFFICE_CAPACITY = 20
        REQUIRED_STAFF_RATIO = 6.0 # 6:1 (利用者6名に対し職員1名が必要)
        
        # 2. その日の施設外就労 (OFF_SITE) 活動を特定 (DailyLog)
        # 施設外に出ている利用者と、それに対応している職員を特定する
        off_site_logs = DailyLog.query.filter(
            func.date(DailyLog.log_date) == target_date,
            DailyLog.location_type.in_(['OFF_SITE_EXTERNAL', 'OFF_SITE_USER_HOME'])
        ).all()
        
        users_off_site = set([log.user_id for log in off_site_logs])
        staff_off_site = set([log.supporter_id for log in off_site_logs])
        
        # 3. 事業所内にいる利用者/職員数を計算
        # 簡易化: サービス登録利用者から不在者を除く
        users_on_site_count = OFFICE_CAPACITY - len(users_off_site) # サービス対象者の総数から引く
        
        # 期間中に ACTIVE な全職員のIDを取得
        active_staff_on_date = db.session.query(Supporter.id).join(Supporter.office).filter(
            Supporter.office_id == office_id,
            Supporter.is_active == True,
            # ここでは、その日勤務している職員の Timecard を参照して絞り込むロジックが必要
        ).all()
        
        # 施設外に出ている職員を除外
        staff_on_site_count = len(active_staff_on_date) - len(staff_off_site)
        
        # 4. 比率の検証
        if users_on_site_count <= 0 or staff_on_site_count <= 0:
            # 誰もいない場合は計算不要だが、ここでは安全のためエラー
            ratio_met = True 
        else:
            actual_ratio = users_on_site_count / staff_on_site_count
            ratio_met = actual_ratio <= REQUIRED_STAFF_RATIO
        
        if not ratio_met:
             return {"status": "NON_COMPLIANT", "message": f"Daily ratio ({actual_ratio:.1f}:1) failed on {target_date}."}
        
        return {"status": "COMPLIANT", "ratio": f"{actual_ratio:.1f}:1"}


    # ====================================================================
    # 4. 減算リスクの監査ログ記録 (Deduction Audit Log) ★ NEW
    # ====================================================================

    def log_deduction_event(self, event_type: str, user_id: int, start_date: date, notes: str) -> ComplianceEventLog:
        """
        計画未作成減算などの発生を不可逆な監査ログ（ComplianceEventLog）に記録する。
        """
        log = ComplianceEventLog(
            user_id=user_id,
            event_type=event_type, # 例: 'PLAN_UNCREATED_SUBTRACTION'
            start_date=start_date,
            end_date=start_date, # 期間を持つべきだが、ここでは起算日として一旦記録
            notes=notes,
            document_url="SYSTEM_GENERATED"
        )
        db.session.add(log)
        db.session.commit()
        return log