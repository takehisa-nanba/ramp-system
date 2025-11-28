from backend.app.extensions import db
from backend.app.models import (
    IncidentReport, ComplaintLog, 
    CommitteeActivityLog, TrainingLog, OfficeTrainingEvent,
    Supporter, CommitteeTypeMaster,
    OfficeSetting, DailyLog, SupporterJobAssignment, # ★ 日次チェック用モデル
    ComplianceEventLog, # ★ 減算監査ログ記録用
    UnresponsiveRiskCounter # ★ 断罪の証拠化 (URAC) モデル
)
from sqlalchemy import func, and_, extract
from datetime import datetime, timezone, date, timedelta
from typing import Optional, List, Dict, Any # Any を追加
import logging
from sqlalchemy.exc import IntegrityError # DB例外処理用
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
        report.approved_at = datetime.now(timezone.utc)
        
        db.session.commit()
        return report

    # ====================================================================
    # 2. 委員会・研修管理 (Mandatory Activities)
    # ... (check_committee_compliance はそのまま維持) ...
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
            
        now = datetime.now(timezone.utc)
        last_meeting = last_log.meeting_timestamp
        
        if last_meeting.tzinfo is None:
            last_meeting = last_meeting.replace(tzinfo=timezone.utc)
            
        months_since = (now - last_meeting).days / 30
        
        if months_since > committee_type.required_frequency_months:
             return {"status": "NON_COMPLIANT", "message": f"Overdue by {months_since - committee_type.required_frequency_months:.1f} months."}
             
        return {"status": "COMPLIANT", "last_meeting": last_log.meeting_timestamp}


    # ====================================================================
    # 3. 日次人員配置チェック (Daily Ratio Guardrail) ★ NEW
    # ====================================================================

    def check_daily_personnel_ratio(self, office_id: int, target_date: date) -> dict:
        """
        【行政指導対応】施設外就労がある日における、事業所内の最低人員配置基準を検証する。
        （施設外支援に出た職員と利用者を除外した純粋なオンサイト比率をチェック）
        """
        logger.info(f"🔍 Checking daily personnel ratio for office {office_id} on {target_date}.")
        
        office_setting = db.session.get(OfficeSetting, office_id)
        if not office_setting:
            raise ValueError(f"OfficeSetting ID {office_id} not found.")

        # NOTE: 基準（定員と比率）は OfficeSetting/OfficeServiceConfiguration から取得する必要があるが、ここでは仮定
        OFFICE_CAPACITY = 20
        REQUIRED_STAFF_RATIO = 6.0 
        
        # 1. 施設外活動の特定 (DailyLog)
        off_site_logs = DailyLog.query.filter(
            func.date(DailyLog.log_date) == target_date,
            DailyLog.location_type.in_(['OFF_SITE_EXTERNAL', 'OFF_SITE_USER_HOME'])
        ).all()
        
        users_off_site = set([log.user_id for log in off_site_logs])
        staff_off_site = set([log.supporter_id for log in off_site_logs])
        
        # 2. 事業所内にいる利用者/職員数を計算 (簡略化)
        users_on_site_count = max(0, OFFICE_CAPACITY - len(users_off_site)) 
        
        # 期間中に ACTIVE な全職員のIDを取得 (Timecard や JobAssignment で絞り込むべきだが、ここではアクティブ職員の総数で代用)
        active_staff_total = db.session.query(Supporter.id).join(Supporter.office).filter(
            Supporter.office_id == office_id,
            Supporter.is_active == True,
        ).count()
        
        # 施設外に出ている職員を除外
        staff_on_site_count = max(0, active_staff_total - len(staff_off_site))
        
        # 4. 比率の検証
        if staff_on_site_count == 0 and users_on_site_count > 0:
            actual_ratio = float('inf') # 無限大
        elif staff_on_site_count == 0 and users_on_site_count == 0:
            actual_ratio = 0.0
        else:
            actual_ratio = users_on_site_count / staff_on_site_count
        
        ratio_met = actual_ratio <= REQUIRED_STAFF_RATIO
        
        if not ratio_met:
            logger.warning(f"⚠️ Daily ratio NON-COMPLIANT ({actual_ratio:.1f}:1) on {target_date}.")
            return {
                "status": "NON_COMPLIANT", 
                "message": f"日次人員配置基準（{actual_ratio:.1f}:1）違反。オンサイトの職員を増やす必要があります。",
                "ratio": f"{actual_ratio:.1f}:1" # ★ 修正: ratio キーを追加
            }
        
        return {"status": "COMPLIANT", "ratio": f"{actual_ratio:.1f}:1"}
    

    # ====================================================================
    # 4. 減算リスクの監査ログ記録 (Deduction Audit Log)
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
    
    
    # ====================================================================
    # 5. 管理職の「無視」という状態を追跡 (URAC)
    # ====================================================================
    
    def track_risk_ignoring_manager(self, supporter_id: int, risk_type: str, linked_entity_id: int):
        """
        【断罪の証拠化コア / 管理職責任ロック】
        管理者が計画未作成などの重大なリスクを無視した回数を追跡し、累積回数を記録する。
        URAC（未対応リスク累積カウンター）モデルを操作し、リスク累積状態を不可逆的に確定させる。
        """
        try:
            urac_record = UnresponsiveRiskCounter.query.filter_by(
                supporter_id=supporter_id,
                risk_type=risk_type
            ).first()

            if urac_record:
                urac_record.cumulative_count += 1
                urac_record.last_ignored_at = datetime.now(timezone.utc)
                urac_record.linked_entity_id = linked_entity_id 
                urac_record.linked_entity_type = "SupportPlan" # 固定値と仮定
                
                db.session.add(urac_record)
                logger.critical(f"🔥 URAC INC: Supporter {supporter_id} ignored risk {risk_type}. Cumulative count: {urac_record.cumulative_count}")
            else:
                new_urac = UnresponsiveRiskCounter(
                    supporter_id=supporter_id,
                    risk_type=risk_type,
                    cumulative_count=1,
                    linked_entity_id=linked_entity_id,
                    linked_entity_type="SupportPlan"
                )
                db.session.add(new_urac)
                logger.critical(f"🔥 URAC NEW: Supporter {supporter_id} started tracking for risk {risk_type}.")

            db.session.commit()

        except IntegrityError:
            db.session.rollback()
            logger.error("❌ URAC Integrity Error occurred during tracking.")
        except Exception as e:
            logger.exception(f"🔥 CRITICAL: Failed to track URAC for supporter {supporter_id}: {e}")
            db.session.rollback()