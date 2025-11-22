import pytest
import logging
from datetime import datetime, timedelta, timezone, date
from backend.app import db
from backend.app.models import (
    User, Supporter, StatusMaster, CommitteeTypeMaster,
    OfficeSetting, Corporation, MunicipalityMaster, IncidentReport, CommitteeActivityLog
)
from backend.app.services.compliance_service import ComplianceService

logger = logging.getLogger(__name__)

def test_incident_workflow_and_compliance(app):
    """
    インシデント報告の承認フローと、法令遵守チェック機能のテスト。
    """
    logger.info("🚀 TEST START: コンプライアンス機能の検証を開始します")

    with app.app_context():
        # --- 1. 準備 ---
        # 必要なマスタと組織
        status = StatusMaster(name="利用中")
        muni = MunicipalityMaster(municipality_code="999999", name="Test City")
        ctype = CommitteeTypeMaster(name="感染対策委員会", required_frequency_months=3)
        db.session.add_all([status, muni, ctype])
        db.session.flush()

        corp = Corporation(corporation_name="Test Corp", corporation_type="KK")
        db.session.add(corp)
        db.session.flush()

        office = OfficeSetting(corporation_id=corp.id, office_name="Test Office", municipality_id=muni.id)
        db.session.add(office)
        db.session.flush()

        user = User(display_name="UserA", status_id=status.id)
        staff = Supporter(
            last_name="Staff", first_name="A", last_name_kana="S", first_name_kana="A",
            employment_type="FULL_TIME", weekly_scheduled_minutes=2400, hire_date=date(2025, 1, 1)
        )
        manager = Supporter(
            last_name="Manager", first_name="B", last_name_kana="M", first_name_kana="B",
            employment_type="FULL_TIME", weekly_scheduled_minutes=2400, hire_date=date(2025, 1, 1)
        )
        db.session.add_all([user, staff, manager])
        db.session.commit()

        service = ComplianceService()

        # --- 2. インシデント報告ワークフロー ---
        logger.info("🔹 ステップ1: インシデント報告")
        incident_data = {
            "user_id": user.id,
            "incident_type": "ACCIDENT",
            "occurrence_timestamp": datetime.now(timezone.utc),
            "detailed_description": "転倒",
            "cause_analysis": "床が濡れていた",
            "preventive_action_plan": "清掃の徹底"
        }
        report = service.report_incident(staff.id, incident_data)
        assert report.report_status == 'PENDING_APPROVAL'
        logger.debug(f"   -> Report ID: {report.id} Created (Pending)")

        # 承認
        logger.info("🔹 ステップ2: 管理者承認")
        finalized_report = service.approve_incident_report(report.id, manager.id)
        assert finalized_report.report_status == 'FINALIZED'
        assert finalized_report.approver_id == manager.id
        logger.debug("   -> Report Finalized")

        # --- 3. 委員会開催頻度チェック ---
        logger.info("🔹 ステップ3: 委員会コンプライアンスチェック")
        
        # 記録なし -> NON_COMPLIANT
        check1 = service.check_committee_compliance(office.id, ctype.id)
        assert check1['status'] == 'NON_COMPLIANT'
        logger.debug("   -> 記録なし: 判定OK")

        # 記録あり(直近) -> COMPLIANT
        log = CommitteeActivityLog(
            office_id=office.id, committee_type_id=ctype.id,
            meeting_timestamp=datetime.now(timezone.utc),
            discussion_summary="インフルエンザ対策"
        )
        db.session.add(log)
        db.session.commit()

        check2 = service.check_committee_compliance(office.id, ctype.id)
        assert check2['status'] == 'COMPLIANT'
        logger.debug("   -> 直近開催あり: 判定OK")

        # 記録あり(古い) -> NON_COMPLIANT
        # 4ヶ月前の記録に書き換え
        log.meeting_timestamp = datetime.now(timezone.utc) - timedelta(days=120)
        db.session.commit()
        
        check3 = service.check_committee_compliance(office.id, ctype.id)
        assert check3['status'] == 'NON_COMPLIANT'
        logger.debug("   -> 期限切れ(4ヶ月前): 判定OK")
        
        logger.info("✅ コンプライアンス機能の検証完了")