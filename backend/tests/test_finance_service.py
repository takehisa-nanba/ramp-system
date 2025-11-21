import pytest
from datetime import date, datetime, timedelta
from backend.app import db
from backend.app.models import (
    Corporation, OfficeSetting, OfficeServiceConfiguration,
    MunicipalityMaster, ServiceTypeMaster, Supporter, SupporterPII, # ★ SupporterPIIを追加
    SupporterJobAssignment, SupporterTimecard, JobTitleMaster
)
from backend.app.services.finance_service import FinanceService

def test_fte_calculation(app):
    """
    常勤換算(FTE)計算ロジックのテスト。
    - 常勤・専従: 実働 + 有給
    - 非常勤: 実働のみ
    """
    with app.app_context():
        # --- 1. マスタ & 組織セットアップ ---
        muni = MunicipalityMaster(municipality_code="999999", name="Test City")
        stype = ServiceTypeMaster(name="Transition", service_code="TR", required_review_months=3)
        job = JobTitleMaster(title_name="Support Staff")
        
        db.session.add_all([muni, stype, job])
        db.session.flush()
        
        corp = Corporation(corporation_name="Test Corp", corporation_type="KK")
        db.session.add(corp)
        db.session.flush()
        
        # 常勤基準: 40時間/週 = 2400分
        office = OfficeSetting(
            corporation_id=corp.id, 
            office_name="Test Office", 
            municipality_id=muni.id,
            full_time_weekly_minutes=2400
        )
        db.session.add(office)
        db.session.flush()
        
        service_config = OfficeServiceConfiguration(
            office_id=office.id,
            service_type_master_id=stype.id,
            jigyosho_bango="1234567890",
            capacity=20
        )
        db.session.add(service_config)
        db.session.flush()
        
        # --- 2. 職員セットアップ (PII分離対応) ---
        
        # Aさん: 常勤・専従 (Full-Time)
        supporter_a = Supporter(
            last_name="Full", first_name="Time", last_name_kana="フル", first_name_kana="タイム",
            employment_type="FULL_TIME", weekly_scheduled_minutes=2400, hire_date=date.today()
        )
        # PII (メールアドレス) を紐づける
        supporter_a.pii = SupporterPII(email="a@test.com")

        # Bさん: 非常勤 (Part-Time)
        supporter_b = Supporter(
            last_name="Part", first_name="Time", last_name_kana="パート", first_name_kana="タイム",
            employment_type="PART_TIME", weekly_scheduled_minutes=1200, hire_date=date.today()
        )
        supporter_b.pii = SupporterPII(email="b@test.com")

        db.session.add_all([supporter_a, supporter_b])
        db.session.flush()
        
        # 職務割り当て (両名ともこのサービスに配置)
        assign_a = SupporterJobAssignment(
            supporter_id=supporter_a.id, job_title_id=job.id, 
            office_service_configuration_id=service_config.id,
            start_date=date(2025, 1, 1), assigned_minutes=2400
        )
        assign_b = SupporterJobAssignment(
            supporter_id=supporter_b.id, job_title_id=job.id, 
            office_service_configuration_id=service_config.id,
            start_date=date(2025, 1, 1), assigned_minutes=1200
        )
        db.session.add_all([assign_a, assign_b])
        db.session.flush()
        
        # --- 3. 勤怠セットアップ (テスト対象期間: 1/1 ~ 1/7) ---
        
        # Aさん (常勤): 実働4時間(240分) + 有給4時間(240分) = 計8時間(480分)
        # -> 常勤換算対象: 480分
        tc_a = SupporterTimecard(
            supporter_id=supporter_a.id,
            office_service_configuration_id=service_config.id,
            work_date=date(2025, 1, 1),
            check_in=datetime(2025, 1, 1, 9, 0),
            check_out=datetime(2025, 1, 1, 13, 0), # 4時間
            total_break_minutes=0,
            deemed_work_minutes=240, # 有給4時間
            absence_type="PAID_LEAVE"
        )
        
        # Bさん (非常勤): 実働4時間(240分) + 有給4時間(240分)
        # -> 常勤換算対象: 240分 (有給は除外されるべき！)
        tc_b = SupporterTimecard(
            supporter_id=supporter_b.id,
            office_service_configuration_id=service_config.id,
            work_date=date(2025, 1, 1),
            check_in=datetime(2025, 1, 1, 9, 0),
            check_out=datetime(2025, 1, 1, 13, 0), # 4時間
            total_break_minutes=0,
            deemed_work_minutes=240, # 有給4時間
            absence_type="PAID_LEAVE"
        )
        
        db.session.add_all([tc_a, tc_b])
        db.session.commit()
        
        # --- 4. 計算実行 ---
        service = FinanceService()
        fte = service.calculate_fte_for_service(
            service_config.id, 
            date(2025, 1, 1), 
            date(2025, 1, 7)
        )
        
        # --- 5. 検証 ---
        # Aさん貢献分: 480 / 2400 = 0.2
        # Bさん貢献分: 240 / 2400 = 0.1 (有給分240は無視される)
        # 合計: 0.3
        
        assert fte == 0.3