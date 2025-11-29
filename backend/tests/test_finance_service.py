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
    SupportPlan, DailyLog, SupporterTimecard, SupporterJobAssignment,
    # 依存関係としてインポート (テスト内で直接使用しなくても定義が必要な場合がある)
    LongTermGoal, ShortTermGoal, IndividualSupportGoal, DailyLogActivity, HolisticSupportPolicy 
)
from backend.app.services.finance_service import FinanceService
from backend.app.services.support_service import SupportService

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
            staff_code="S001", last_name="Full", first_name="Time", last_name_kana="フル", first_name_kana="タイム", 
            hire_date=date(2025, 1, 1), employment_type="FULL_TIME", 
            weekly_scheduled_minutes=WEEKLY_FULL_TIME_MINUTES
        )
        supporter_a.pii = SupporterPII(email="a@test.com")
        
        # Bさん: 非常勤 (Part-Time) 
        supporter_b = Supporter(
            staff_code="S002", last_name="Part", first_name="Time", last_name_kana="パート", first_name_kana="タイム", 
            hire_date=date(2025, 1, 1), employment_type="PART_TIME", 
            weekly_scheduled_minutes=1200
        )
        supporter_b.pii = SupporterPII(email="b@test.com")
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
            total_break_minutes=0, scheduled_work_minutes=480 # 【修正】NOT NULL回避
        )
        
        # Bさん (非常勤): 
        # 実働 240分 + 有給(Deemed) 240分 -> FTE貢献: 240/2400 = 0.1 (非常勤の有給は除外される)
        tc_b = SupporterTimecard(
            supporter_id=supporter_b.id, work_date=date(2025, 1, 1), 
            office_service_configuration_id=service_config.id,
            check_in=datetime(2025, 1, 1, 9, 0), check_out=datetime(2025, 1, 1, 13, 0), # 実働4時間 (240分)
            deemed_work_minutes=240, 
            absence_type="PAID_LEAVE",
            total_break_minutes=0, scheduled_work_minutes=480 # 【修正】NOT NULL回避
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

def test_three_stage_audit_logic(app):
    """
    請求データが三段監査ロジック (Plan Guardrail, Daily Validation, Audit Flag) に準拠しているか検証する。
    FinanceService.audit_billing_data(billing_id) をモックせず、実際のロジックの呼び出しを想定。
    """
    logger.info("🚀 TEST START: 三段監査ロジック検証")
    
    with app.app_context():
        session = db.session
        user, service_config, office, job_title = setup_base_data(session)
        finance_service = FinanceService()
        
        # FinanceServiceの内部で参照される PlanGuardrail をモック
        with patch.object(FinanceService, '_check_plan_guardrail', return_value=True) as mock_guardrail, \
             patch.object(FinanceService, '_check_daily_validation', return_value=True) as mock_daily_check:

            # 1. 監査が成功する請求データ
            valid_billing = BillingData(
                user_id=user.id, 
                service_type='TRAINING', 
                unit_count=100, 
                cost=1000.0, 
                billing_date=date(2025, 1, 5),
                plan_id=1, daily_log_id=1 
            )
            session.add(valid_billing)
            session.flush() # ID確定
            
            # 2. 監査の実行 (成功ケース)
            audit_result_valid = finance_service.audit_billing_data(valid_billing.id)
            
            # 3. 検証 (成功ケース)
            assert audit_result_valid is True, "有効な請求データは監査を通過すべき。"
            mock_guardrail.assert_called_with(valid_billing)
            mock_daily_check.assert_called_with(valid_billing)

        # 4. 監査が失敗する請求データ (不正請求: Plan Guardrail/Daily Validation 失敗を想定)
        # モックを戻して、監査失敗ロジックのパスをテスト
        with patch.object(FinanceService, '_check_plan_guardrail', return_value=False) as mock_guardrail_fail:
            invalid_billing = BillingData(
                user_id=user.id, 
                service_type='TRAINING', 
                unit_count=500, 
                cost=5000.0, 
                billing_date=date(2024, 12, 31), # 計画開始前の不正請求をシミュレーション
                plan_id=1, daily_log_id=2
            )
            session.add(invalid_billing)
            session.commit()
            
            # 5. 監査の実行 (失敗ケース)
            audit_result_invalid = finance_service.audit_billing_data(invalid_billing.id)
            
            # 6. 検証 (失敗ケース)
            assert audit_result_invalid is False, "Plan Guardrailに失敗する請求データは監査に失敗すべき。"
            mock_guardrail_fail.assert_called_with(invalid_billing)
        
        logger.info("✅ 三段監査ロジック検証完了: 成功ケースと失敗ケースの分離を検証")