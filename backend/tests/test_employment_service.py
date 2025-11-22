import pytest
import logging
from datetime import date, datetime, timedelta, timezone
from backend.app import db
from backend.app.models import User, Supporter, StatusMaster, EmployerMaster
from backend.app.services.employment_service import EmploymentService

logger = logging.getLogger(__name__)

def test_placement_and_retention(app):
    """
    就労登録と定着率判定ロジックのテスト。
    """
    logger.info("🚀 TEST START: 就労支援機能の検証を開始します")

    with app.app_context():
        # --- 1. 準備 ---
        status = StatusMaster(name="利用中")
        db.session.add(status)
        db.session.flush()

        user = User(display_name="WorkerA", status_id=status.id)
        staff = Supporter(
            last_name="Dev", first_name="Staff", last_name_kana="D", first_name_kana="S",
            employment_type="FULL_TIME", weekly_scheduled_minutes=2400, hire_date=date(2025, 1, 1)
        )
        employer = EmployerMaster(company_name="Tech Corp", industry_type="IT")
        
        db.session.add_all([user, staff, employer])
        db.session.commit()

        service = EmploymentService()

        # --- 2. 就職登録 ---
        logger.info("🔹 ステップ1: 就職登録")
        # 7ヶ月前に就職したことにする
        placement_date = date.today() - timedelta(days=210)
        
        placement = service.register_placement(
            user_id=user.id,
            employer_id=employer.id,
            placement_date=placement_date,
            scenario="NEW_PLACEMENT"
        )
        assert placement.id is not None
        logger.debug(f"   -> Placement Registered: {placement_date}")

        # --- 3. 定着確認 (6ヶ月達成) ---
        logger.info("🔹 ステップ2: 定着マイルストーン判定")
        status = service.check_retention_status(user.id)
        
        assert status['status'] == 'EMPLOYED'
        assert status['milestone_reached'] is True
        logger.debug(f"   -> Result: {status}")

        # --- 4. 企業開拓ログ ---
        logger.info("🔹 ステップ3: 企業開拓ログ")
        log = service.log_development_activity(
            supporter_id=staff.id,
            activity_type="VISIT",
            summary="定着支援訪問。様子良好。",
            employer_id=employer.id
        )
        assert log.id is not None
        logger.debug("   -> Activity Logged")
        
        logger.info("✅ 就労支援機能の検証完了")