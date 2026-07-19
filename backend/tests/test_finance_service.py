# backend/tests/test_finance_service.py

import pytest
import time
from datetime import date, datetime, timedelta, timezone
from unittest.mock import Mock, patch
from backend.app import db
from backend.app.models import (
    MunicipalityMaster, ServiceTypeMaster,
    # Core Models
    User, Supporter, SupporterPII, StatusMaster, JobTitleMaster,
    # Finance Models
    Corporation, OfficeSetting, OfficeServiceConfiguration, ServiceUnitMaster, 
    BillingData,
    # Support/Process Models (Plan, Log, Timecard, Assignment)
    SupportPlan, UserDailyLog, SupporterTimecard, SupporterJobAssignment,
    # 依存関係としてインポート (テスト内で直接使用しなくても定義が必要な場合がある)
    LongTermGoal, ShortTermGoal, IndividualSupportGoal, SupportRecord, HolisticSupportPolicy 
)
from backend.app.services.finance_service import FinanceService
from backend.app.services.support_plan_service import SupportPlanService
from backend.app.services.compliance_service import ComplianceService

import logging
logger = logging.getLogger('TEST_FINANCE')
logger.setLevel(logging.INFO)

# =======================================================================
# UTILITY FUNCTIONS (共通のデータセットアップ - 堅牢性確保)
# =======================================================================

def setup_base_data(session, daily_unit_count=1000, full_time_minutes=2400):
    """
    テストに必要なマスタデータと、Office/ServiceConfigをセットアップする。
    データのUNIQUE制約違反とNULL制約違反を全て回避する。
    """
    
    # --- 1. マスタデータの重複排除と確実な取得 ---
    
    # StatusMaster
    status = session.query(StatusMaster).filter_by(name='利用中').first()
    if not status:
        status = StatusMaster(name='利用中', description='サービス利用中')
        session.add(status)
    
    # JobTitleMaster
    job_title = session.query(JobTitleMaster).filter_by(title_name='Support Staff').first()
    if not job_title:
        job_title = JobTitleMaster(title_name='Support Staff')
        session.add(job_title)

    # MunicipalityMaster (テスト実行ごとのUNIQUE制約違反回避)
    muni_code = f"999999{int(time.time() * 1000) % 10000}" 
    muni = MunicipalityMaster(municipality_code=muni_code, name="Test City")
    session.add(muni)
    
    # ServiceTypeMaster
    stype = session.query(ServiceTypeMaster).filter_by(service_code="TR").first()
    if not stype:
        stype = ServiceTypeMaster(name="Transition", service_code="TR", required_review_months=3)
        session.add(stype)

    corp = Corporation(corporation_name="Test Corp", corporation_type="KK")
    session.add(corp)
    session.flush()

    # ServiceUnitMaster 
    unit_master = session.query(ServiceUnitMaster).filter_by(service_type='TRAINING').first()
    if not unit_master:
        unit_master = ServiceUnitMaster(
            service_type='TRAINING', 
            unit_price=10.0, 
            unit_count=daily_unit_count, 
            start_date=date(2025, 1, 1), 
            end_date=date(9999, 12, 31),
            responsible_id=1 
        )
        session.add(unit_master)

    # Office Setting, Service Config の作成
    office = OfficeSetting(
        corporation_id=corp.id, 
        office_name="Test Office", 
        municipality_id=muni.id,
        full_time_weekly_minutes=full_time_minutes
    )
    session.add(office)
    session.flush()
    
    # 【修正】UNIQUE制約回避: 実行ごとにユニークな事業所番号を生成
    unique_bango = f"123456{int(time.time() * 1000) % 10000}" 
    
    service_config = OfficeServiceConfiguration(
        office_id=office.id,
        service_type_master_id=stype.id,
        jigyosho_bango=unique_bango, 
        capacity=20
    )
    session.add(service_config)
    
    # --- 2. User (NOT NULL回避) ---
    user = User(
        display_name="Tanaka", 
        status_id=status.id, 
        service_start_date=date(2025, 1, 1) 
    )
    session.add(user)
    
    session.commit()
    
    return user, service_config, office, job_title # job_titleを返却

# =======================================================================
# TEST 1: FTE (常勤換算) 計算の検証 (STEP 3-3)
# =======================================================================

def test_fte_calculation(app):
    """
    FTE 1.0 Capと、非常勤の有給(deemed_work_minutes)が常勤換算に含まれない検証。
    FTE = (実働時間 + 常勤の有給時間) / 常勤基準時間
    """
    logger.info("🚀 TEST START: 常勤換算 (FTE) 計算ロジック検証")
    WEEKLY_FULL_TIME_MINUTES = 2400 # 40時間/週 (常勤基準時間)

    with app.app_context():
        session = db.session
        user, service_config, office, job_title = setup_base_data(session, full_time_minutes=WEEKLY_FULL_TIME_MINUTES)
        finance_service = FinanceService()
        
        # 1. 職員セットアップ - NOT NULL フィールドを全て設定
        
        # Aさん: 常勤 (Full-Time) 
        supporter_a = Supporter(
            staff_code="S001_FTE", last_name="Full", first_name="Time", last_name_kana="フル", first_name_kana="タイム", 
            hire_date=date(2025, 1, 1), employment_type="FULL_TIME", 
            weekly_scheduled_minutes=WEEKLY_FULL_TIME_MINUTES
        )
        pii_a = SupporterPII(email="a_fte@test.com")
        pii_a.set_password("password123")
        supporter_a.pii = pii_a
        
        # Bさん: 非常勤 (Part-Time) 
        supporter_b = Supporter(
            staff_code="S002_FTE", last_name="Part", first_name="Time", last_name_kana="パート", first_name_kana="タイム", 
            hire_date=date(2025, 1, 1), employment_type="PART_TIME", 
            weekly_scheduled_minutes=1200
        )
        pii_b = SupporterPII(email="b_fte@test.com")
        pii_b.set_password("password123")
        supporter_b.pii = pii_b
        session.add_all([supporter_a, supporter_b])
        session.flush() # ID確定
        
        # 職務割り当て (Job Assignment)
        session.add(SupporterJobAssignment(supporter_id=supporter_a.id, job_title_id=job_title.id, office_service_configuration_id=service_config.id, start_date=date(2025, 1, 1), assigned_minutes=WEEKLY_FULL_TIME_MINUTES))
        session.add(SupporterJobAssignment(supporter_id=supporter_b.id, job_title_id=job_title.id, office_service_configuration_id=service_config.id, start_date=date(2025, 1, 1), assigned_minutes=1200))
        session.flush()
        
        # 2. 勤怠セットアップ (テスト日: 1/1)
        # 常勤換算対象の期間は、常勤の週労働時間（2400分）を基準に換算される。
        
        # Aさん (常勤): 
        # 実働 240分 + 有給(Deemed) 240分 = 合計 480分 -> FTE貢献: 480/2400 = 0.2
        tc_a = SupporterTimecard(
            supporter_id=supporter_a.id, work_date=date(2025, 1, 1), 
            office_service_configuration_id=service_config.id,
            check_in=datetime(2025, 1, 1, 9, 0), check_out=datetime(2025, 1, 1, 13, 0), # 実働4時間 (240分)
            deemed_work_minutes=240, 
            absence_type="PAID_LEAVE",
            total_break_minutes=0, scheduled_work_minutes=480, sequence_no=1
        )
        
        # Bさん (非常勤): 
        # 実働 240分 + 有給(Deemed) 240分 -> FTE貢献: 240/2400 = 0.1 (非常勤の有給は除外される)
        tc_b = SupporterTimecard(
            supporter_id=supporter_b.id, work_date=date(2025, 1, 1), 
            office_service_configuration_id=service_config.id,
            check_in=datetime(2025, 1, 1, 9, 0), check_out=datetime(2025, 1, 1, 13, 0), # 実働4時間 (240分)
            deemed_work_minutes=240, 
            absence_type="PAID_LEAVE",
            total_break_minutes=0, scheduled_work_minutes=480, sequence_no=1
        )
        
        session.add_all([tc_a, tc_b])
        session.commit()
        
        # 3. 計算実行 (期間: 1/1 - 1/7 の1週間)
        # 期待値: A(実働+有給) + B(実働のみ) = (240+240) + 240 = 720分 / 2400分 = 0.3 FTE
        fte_result = finance_service.calculate_fte_for_service(
            service_config.id, 
            date(2025, 1, 1), 
            date(2025, 1, 7)
        )
        
        # 4. 検証
        # 常勤Aの貢献(480分) + 非常勤Bの貢献(240分) / 常勤基準時間(2400分)
        EXPECTED_FTE = (480 + 240) / WEEKLY_FULL_TIME_MINUTES
        assert round(fte_result, 2) == round(EXPECTED_FTE, 2), f"FTE calculation failed. Expected: {EXPECTED_FTE:.2f}, Got: {fte_result:.2f}"
        
        logger.info(f"✅ FTE換算検証完了: Calculated FTE: {fte_result:.2f}, Expected: {EXPECTED_FTE:.2f}")

# =======================================================================
# TEST 2: 三段監査ロジックの検証 (STEP 3-3)
# =======================================================================

def test_support_consistency_missing_plan_creates_urac(app):
    """
    支援実績整合性チェックで計画が存在しない場合、URAC(未対応リスクカウンター)が生成されることを検証。
    """
    logger.info("🚀 TEST START: test_support_consistency_missing_plan_creates_urac")
    from backend.app.models import UnresolvedRiskCounter
    
    with app.app_context():
        session = db.session
        user, service_config, office, job_title = setup_base_data(session)
        finance_service = FinanceService()
        
        # Ensure user has a primary supporter so URAC can be assigned
        supporter = Supporter(
            staff_code="S_URAC_1", last_name="Mgr", first_name="Staff", 
            last_name_kana="マネ", first_name_kana="スタ", 
            hire_date=date(2025, 1, 1), employment_type="FULL_TIME", 
            weekly_scheduled_minutes=2400
        )
        session.add(supporter)
        session.flush()
        user.primary_supporter_id = supporter.id
        session.commit()
        
        # Setup SupportRecord so the second check passes, and only the plan check fails
        log = SupportRecord(
            user_id=user.id, 
            log_date=date(2025, 1, 15), 
            supporter_id=supporter.id, 
            support_content="Test", 
            support_record_type='DIRECT_SUPPORT'
        )
        session.add(log)
        session.commit()
        
        result = finance_service.check_support_consistency(user.id, date(2025, 1, 1))
        
        assert result['passed'] is False
        assert "有効な個別支援計画が存在しません" in result['errors'][0]
        
        # Verify URAC
        urac = UnresolvedRiskCounter.query.filter_by(supporter_id=supporter.id, risk_type='PLAN_UNCREATED').first()
        assert urac is not None
        assert urac.cumulative_count == 1
        assert urac.linked_entity_id == user.id

def test_support_consistency_duplicate_risk_increments_counter(app):
    """
    同一リスクを再度チェックした場合、URACレコードが重複せず、cumulative_countがインクリメントされることを検証。
    """
    logger.info("🚀 TEST START: test_support_consistency_duplicate_risk_increments_counter")
    from backend.app.models import UnresolvedRiskCounter
    
    with app.app_context():
        session = db.session
        user, service_config, office, job_title = setup_base_data(session)
        finance_service = FinanceService()
        
        supporter = Supporter(
            staff_code="S_URAC_2", last_name="Mgr2", first_name="Staff", 
            last_name_kana="マネ2", first_name_kana="スタ2", 
            hire_date=date(2025, 1, 1), employment_type="FULL_TIME", 
            weekly_scheduled_minutes=2400
        )
        session.add(supporter)
        session.flush()
        user.primary_supporter_id = supporter.id
        session.commit()
        
        # Setup SupportRecord
        log = SupportRecord(
            user_id=user.id, 
            log_date=date(2025, 1, 15), 
            supporter_id=supporter.id, 
            support_content="Test", 
            support_record_type='DIRECT_SUPPORT'
        )
        session.add(log)
        session.commit()
        
        # First check
        finance_service.check_support_consistency(user.id, date(2025, 1, 1))
        urac = UnresolvedRiskCounter.query.filter_by(supporter_id=supporter.id, risk_type='PLAN_UNCREATED').first()
        assert urac.cumulative_count == 1
        
        # Second check
        finance_service.check_support_consistency(user.id, date(2025, 1, 1))
        urac_after = UnresolvedRiskCounter.query.filter_by(supporter_id=supporter.id, risk_type='PLAN_UNCREATED').all()
        assert len(urac_after) == 1  # Record is not duplicated
        assert urac_after[0].cumulative_count == 2