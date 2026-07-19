import os
import uuid
import pytest
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import scoped_session, sessionmaker

from backend.app import create_app, db
from backend.config import Config
from backend.app.models.staffing import (
    StaffingCalculationRule,
    IntegratedServiceOperation,
    IntegratedServiceOperationMember,
    StaffingCalculationRun,
    StaffingCalculationResult,
    StaffingCalculationResultException,
    StaffingCalculationException
)
from backend.app.models.core.supporter import SupporterTimecard, StaffActivityAllocationLog, SupporterJobAssignment, Supporter
from backend.app.models.core.office import OfficeServiceConfiguration, OfficeSetting, Corporation
from backend.app.models.masters.master_definitions import JobTitleMaster, StaffActivityMaster, MunicipalityMaster, ServiceTypeMaster

@pytest.fixture(scope="module")
def pg_app():
    class PGConfig(Config):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URL")
    
    app = create_app(PGConfig)
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        pytest.skip("TEST_DATABASE_URL is required for this test.")
        
    with app.app_context():
        yield app

@pytest.fixture(scope="function")
def pg_db_session(pg_app):
    with pg_app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()
        session_factory = sessionmaker(bind=connection)
        session = scoped_session(session_factory)
        
        original_session = db.session
        db.session = session
        try:
            yield session
        finally:
            session.remove()
            transaction.rollback()
            connection.close()
            db.session = original_session

@pytest.fixture
def test_corporation(pg_db_session):
    corp = Corporation(corporation_name="Test Corp", corporation_type="NPO")
    pg_db_session.add(corp)
    pg_db_session.commit()
    return corp

@pytest.fixture
def test_office_service_config(pg_db_session, test_corporation):
    mun = pg_db_session.merge(MunicipalityMaster(id=1, municipality_code="123456", name="Test City"))
    svc = pg_db_session.merge(ServiceTypeMaster(id=1, name="Test Service", service_code="123"))
    pg_db_session.commit()
    office = OfficeSetting(corporation_id=test_corporation.id, office_name="Test Office", municipality_id=1)
    pg_db_session.add(office)
    pg_db_session.commit()
    config = OfficeServiceConfiguration(
        office_id=office.id,
        service_type_master_id=1,
        capacity=10,
        jigyosho_bango=uuid.uuid4().hex[:10]
    )
    pg_db_session.add(config)
    pg_db_session.commit()
    return config

@pytest.fixture
def test_supporter(pg_db_session):
    code = uuid.uuid4().hex[:10]
    supporter = Supporter(
        staff_code=code,
        last_name="a",
        first_name="b",
        last_name_kana="a",
        first_name_kana="b",
        hire_date=date(2024,1,1),
        employment_type="FULL_TIME",
        weekly_scheduled_minutes=2400,
        is_active=True
    )
    pg_db_session.add(supporter)
    pg_db_session.commit()
    return supporter

@pytest.fixture
def test_job_title(pg_db_session):
    job = JobTitleMaster(title_name="Test Job " + uuid.uuid4().hex[:5])
    pg_db_session.add(job)
    pg_db_session.commit()
    return job

@pytest.fixture
def test_staff_activity(pg_db_session):
    activity = StaffActivityMaster(activity_name="Test Activity", is_direct_support=True)
    pg_db_session.add(activity)
    pg_db_session.commit()
    return activity

def test_create_app(pg_app):

    """create_app()が成功する"""
    assert pg_app is not None

def test_models_in_metadata(pg_app):
    """新しいモデルがmetadataに登録されているか確認"""
    tables = db.metadata.tables.keys()
    assert 'staffing_calculation_rules' in tables
    assert 'integrated_service_operations' in tables
    assert 'integrated_service_operation_members' in tables
    assert 'staffing_calculation_exceptions' in tables
    assert 'staffing_calculation_runs' in tables
    assert 'staffing_calculation_results' in tables
    assert 'staffing_calculation_result_exceptions' in tables

def test_result_exception_fk_metadata(pg_app):
    """metadataでstaffing_calculation_result_exceptionsのFKにstaffing_calculation_exception_idが含まれているか確認"""
    table = db.metadata.tables['staffing_calculation_result_exceptions']
    fk_columns = [fk.parent.name for fk in table.foreign_keys]
    assert 'staffing_calculation_exception_id' in fk_columns

def test_save_valid_new_models(pg_db_session, test_corporation, test_office_service_config):
    """新規テーブルへ正常データを保存できる、各FKが正しく参照する"""
    rule = StaffingCalculationRule(
        rule_code=uuid.uuid4().hex[:10],
        rule_name="Test Rule",
        rule_type="SIMULTANEOUS_COUNT",
        effective_from=date(2024, 1, 1),
        is_active=True
    )
    pg_db_session.add(rule)
    
    op = IntegratedServiceOperation(
        corporation_id=test_corporation.id,
        operation_name="Test Operation",
        effective_from=date(2024, 1, 1),
        status="APPROVED"
    )
    pg_db_session.add(op)
    pg_db_session.commit()
    
    member = IntegratedServiceOperationMember(
        integrated_service_operation_id=op.id,
        office_service_configuration_id=test_office_service_config.id
    )
    pg_db_session.add(member)
    pg_db_session.commit()
    
    assert rule.id is not None
    assert member.id is not None
    assert member.operation.corporation_id == test_corporation.id

def test_duplicate_rule_code_rejected(pg_db_session):
    """rule_codeの重複が拒否される"""
    code = uuid.uuid4().hex[:10]
    rule1 = StaffingCalculationRule(rule_code=code, rule_name="Rule 1", rule_type="T1", effective_from=date(2024, 1, 1))
    rule2 = StaffingCalculationRule(rule_code=code, rule_name="Rule 2", rule_type="T2", effective_from=date(2024, 1, 1))
    pg_db_session.add(rule1)
    pg_db_session.commit()
    
    pg_db_session.add(rule2)
    with pytest.raises(IntegrityError):
        pg_db_session.commit()
    pg_db_session.rollback()

def test_duplicate_integrated_member_rejected(pg_db_session, test_corporation, test_office_service_config):
    """IntegratedServiceOperationMemberの重複が拒否される"""
    op = IntegratedServiceOperation(corporation_id=test_corporation.id, operation_name="Op", effective_from=date(2024, 1, 1))
    pg_db_session.add(op)
    pg_db_session.commit()
    
    member1 = IntegratedServiceOperationMember(integrated_service_operation_id=op.id, office_service_configuration_id=test_office_service_config.id)
    member2 = IntegratedServiceOperationMember(integrated_service_operation_id=op.id, office_service_configuration_id=test_office_service_config.id)
    pg_db_session.add(member1)
    pg_db_session.commit()
    
    pg_db_session.add(member2)
    with pytest.raises(IntegrityError):
        pg_db_session.commit()
    pg_db_session.rollback()

def test_source_target_assignment_same_rejected(pg_db_session, test_supporter, test_office_service_config, test_job_title):
    """source_assignment_id == target_assignment_idが拒否される"""
    assign = SupporterJobAssignment(
        supporter_id=test_supporter.id,
        office_service_configuration_id=test_office_service_config.id,
        job_title_id=test_job_title.id,
        start_date=date(2024, 1, 1),
        assigned_minutes=2400
    )
    rule = StaffingCalculationRule(rule_code=uuid.uuid4().hex[:10], rule_name="Exc Rule", rule_type="T", effective_from=date(2024,1,1))
    pg_db_session.add(assign)
    pg_db_session.add(rule)
    pg_db_session.commit()
    
    exc = StaffingCalculationException(
        staffing_calculation_rule_id=rule.id,
        source_assignment_id=assign.id,
        target_assignment_id=assign.id,
        effective_from=date(2024, 1, 1)
    )
    pg_db_session.add(exc)
    with pytest.raises(IntegrityError):
        pg_db_session.commit()
    pg_db_session.rollback()

def test_invalid_effective_dates_rule(pg_db_session):
    rule = StaffingCalculationRule(rule_code=uuid.uuid4().hex[:10], rule_name="Date Rule", rule_type="T", effective_from=date(2024, 12, 31), effective_to=date(2024, 1, 1))
    pg_db_session.add(rule)
    with pytest.raises(IntegrityError):
        pg_db_session.commit()
    pg_db_session.rollback()

def test_invalid_effective_dates_integrated_operation(pg_db_session, test_corporation):
    operation = IntegratedServiceOperation(
        corporation_id=test_corporation.id,
        operation_name="Op",
        effective_from=date(2024, 12, 31),
        effective_to=date(2024, 1, 1)
    )
    pg_db_session.add(operation)
    with pytest.raises(IntegrityError):
        pg_db_session.commit()
    pg_db_session.rollback()

def test_invalid_effective_dates_exception(pg_db_session, test_supporter, test_office_service_config, test_job_title):
    rule = StaffingCalculationRule(rule_code=uuid.uuid4().hex[:10], rule_name="Test Rule", rule_type="SIMULTANEOUS_COUNT", effective_from=date(2024, 1, 1))
    pg_db_session.add(rule)
    pg_db_session.flush()
    assign1 = SupporterJobAssignment(supporter_id=test_supporter.id, office_service_configuration_id=test_office_service_config.id, job_title_id=test_job_title.id, start_date=date(2024, 1, 1), assigned_minutes=1)
    assign2 = SupporterJobAssignment(supporter_id=test_supporter.id, office_service_configuration_id=test_office_service_config.id, job_title_id=test_job_title.id, start_date=date(2024, 1, 2), assigned_minutes=2)
    pg_db_session.add(assign1)
    pg_db_session.add(assign2)
    pg_db_session.flush()
    
    exc = StaffingCalculationException(
        staffing_calculation_rule_id=rule.id,
        source_assignment_id=assign1.id,
        target_assignment_id=assign2.id,
        effective_from=date(2024, 12, 31),
        effective_to=date(2024, 1, 1)
    )
    pg_db_session.add(exc)
    with pytest.raises(IntegrityError):
        pg_db_session.commit()
    pg_db_session.rollback()

def test_invalid_effective_dates_run(pg_db_session, test_office_service_config):
    run = StaffingCalculationRun(
        office_service_configuration_id=test_office_service_config.id,
        period_start=date(2024, 12, 31),
        period_end=date(2024, 1, 1),
        rule_snapshot_at=datetime.utcnow()
    )
    pg_db_session.add(run)
    with pytest.raises(IntegrityError):
        pg_db_session.commit()
    pg_db_session.rollback()

def test_invalid_effective_dates_result_exception(pg_db_session, test_supporter, test_office_service_config, test_job_title):
    rule = StaffingCalculationRule(rule_code=uuid.uuid4().hex[:10], rule_name="R", rule_type="T", effective_from=date(2024, 1, 1))
    assign1 = SupporterJobAssignment(supporter_id=test_supporter.id, office_service_configuration_id=test_office_service_config.id, job_title_id=test_job_title.id, start_date=date(2024, 1, 1), assigned_minutes=1)
    assign2 = SupporterJobAssignment(supporter_id=test_supporter.id, office_service_configuration_id=test_office_service_config.id, job_title_id=test_job_title.id, start_date=date(2024, 1, 2), assigned_minutes=2)
    pg_db_session.add_all([rule, assign1, assign2])
    pg_db_session.flush()
    exc = StaffingCalculationException(staffing_calculation_rule_id=rule.id, source_assignment_id=assign1.id, target_assignment_id=assign2.id, effective_from=date(2024, 1, 1))
    run = StaffingCalculationRun(office_service_configuration_id=test_office_service_config.id, period_start=date(2024, 1, 1), period_end=date(2024, 1, 31), rule_snapshot_at=datetime.utcnow())
    pg_db_session.add_all([exc, run])
    pg_db_session.flush()
    result = StaffingCalculationResult(staffing_calculation_run_id=run.id, supporter_job_assignment_id=assign1.id, ordinary_minutes=1, exception_minutes=1, total_counted_minutes=2, full_time_required_minutes=10, fte_value=0.1)
    pg_db_session.add(result)
    pg_db_session.flush()
    result_exc = StaffingCalculationResultException(
        staffing_calculation_result_id=result.id,
        staffing_calculation_exception_id=exc.id,
        applied_rule_code=rule.rule_code,
        applied_rule_name=rule.rule_name,
        rule_effective_from=date(2024, 12, 31),
        rule_effective_to=date(2024, 1, 1),
        added_minutes=1,
        source_assignment_id=assign1.id,
        target_assignment_id=assign2.id
    )
    pg_db_session.add(result_exc)
    with pytest.raises(IntegrityError):
        pg_db_session.commit()
    pg_db_session.rollback()

def test_negative_minutes_rejected(pg_db_session, test_supporter, test_office_service_config, test_job_title):
    """負のminutesが拒否される"""
    assign = SupporterJobAssignment(
        supporter_id=test_supporter.id,
        office_service_configuration_id=test_office_service_config.id,
        job_title_id=test_job_title.id,
        start_date=date(2024, 1, 1),
        assigned_minutes=2400,
        weekly_assigned_minutes=-100
    )
    pg_db_session.add(assign)
    with pytest.raises(IntegrityError):
        pg_db_session.commit()
    pg_db_session.rollback()

def test_fte_value_decimal(pg_db_session, test_office_service_config, test_supporter, test_job_title):
    """fte_valueがDecimalとして保存・取得される"""
    run = StaffingCalculationRun(
        office_service_configuration_id=test_office_service_config.id,
        period_start=date(2024, 1, 1),
        period_end=date(2024, 1, 31),
        rule_snapshot_at=datetime.utcnow()
    )
    assign = SupporterJobAssignment(supporter_id=test_supporter.id, office_service_configuration_id=test_office_service_config.id, job_title_id=test_job_title.id, start_date=date(2024, 1, 1), assigned_minutes=2400)
    pg_db_session.add(run)
    pg_db_session.add(assign)
    pg_db_session.commit()

    result = StaffingCalculationResult(
        staffing_calculation_run_id=run.id,
        supporter_job_assignment_id=assign.id,
        ordinary_minutes=1200,
        exception_minutes=0,
        total_counted_minutes=1200,
        full_time_required_minutes=2400,
        fte_value=Decimal("0.50")
    )
    pg_db_session.add(result)
    pg_db_session.commit()
    
    fetched = pg_db_session.query(StaffingCalculationResult).get(result.id)
    assert isinstance(fetched.fte_value, Decimal)
    assert fetched.fte_value == Decimal("0.50")

def test_existing_tables_new_columns_nullable(pg_db_session, test_supporter, test_office_service_config):
    """追加した既存テーブルの新カラムがNULLのまま保存可能"""
    tc = SupporterTimecard(
        supporter_id=test_supporter.id,
        office_service_configuration_id=test_office_service_config.id,
        work_date=date(2024, 1, 1)
    )
    pg_db_session.add(tc)
    pg_db_session.commit()
    
    assert tc.id is not None
    assert tc.office_id is None
    assert tc.sequence_no is None
    
def test_existing_creation_process_succeeds(pg_db_session, test_supporter, test_office_service_config, test_job_title, test_staff_activity):
    """既存カラムだけを使った従来の作成処理が成功する"""
    assign = SupporterJobAssignment(
        supporter_id=test_supporter.id,
        office_service_configuration_id=test_office_service_config.id,
        job_title_id=test_job_title.id,
        start_date=date(2024, 1, 1),
        assigned_minutes=2400
    )
    pg_db_session.add(assign)
    pg_db_session.commit()
    assert assign.id is not None
    
    log = StaffActivityAllocationLog(
        supporter_id=test_supporter.id,
        activity_date=date(2024, 1, 1),
        staff_activity_master_id=test_staff_activity.id,
        allocated_duration_seconds=3600
    )
    pg_db_session.add(log)
    pg_db_session.commit()
    assert log.id is not None
