"""One transaction, only for the dedicated local sample database."""
from datetime import timedelta

from backend.app.extensions import db
from backend.app.models import (
    Corporation, EmployerMaster, GrantedService, JobPlacementLog,
    JobTitleMaster, LongTermGoal, MunicipalityMaster, OfficeServiceConfiguration, OfficeSetting,
    PermissionMaster, RoleMaster, ServiceCertificate, ServiceTypeMaster, StatusMaster,
    SupportPlan, Supporter, SupporterJobAssignment, SupporterPII, User, UserPII,
)
from backend.app.services.job_retention_service import JobRetentionService
from backend.app.utils.timezone import get_jst_today, get_jst_now


def seed_demo():
    if db.engine.url.database != "ramp_demo":
        raise RuntimeError("The local demo requires the dedicated ramp_demo database.")
    if Corporation.query.filter_by(tenant_id="ramp-local-demo").first():
        return
    if Corporation.query.first() or User.query.first() or Supporter.query.first():
        raise RuntimeError("Local demo initialization requires an empty database.")
    today = get_jst_today()
    corp = Corporation(corporation_name="サンプル法人", corporation_type="株式会社", tenant_id="ramp-local-demo")
    municipality = MunicipalityMaster(name="浜松市（サンプル）", municipality_code="221309")
    status = StatusMaster(name="利用中")
    transition = ServiceTypeMaster(name="就労移行支援", service_code="TRANSITION", required_review_months=6)
    retention = ServiceTypeMaster(name="就労定着支援", service_code="RETENTION", required_review_months=6)
    permissions = [PermissionMaster(name=p) for p in (
        "VIEW","CREATE","EDIT","APPROVE","DELETE","VIEW_PII","EDIT_PII","EXPORT_PII","VIEW_AUDIT_LOG",
        "VIEW_STAFF","CREATE_STAFF","EDIT_STAFF",
    )]
    role = RoleMaster(name="ローカル法人管理者", role_scope="CORPORATE", is_admin=True, permissions=permissions)
    title = JobTitleMaster(title_name="サービス管理責任者", is_qualified_role=True)
    db.session.add_all([corp, municipality, status, transition, retention, role, title])
    db.session.flush()
    office = OfficeSetting(office_name="ランプ浜松（サンプル）", corporation_id=corp.id, municipality_id=municipality.id)
    db.session.add(office)
    db.session.flush()
    configs = [OfficeServiceConfiguration(office_id=office.id, service_type_master_id=service.id,
        jigyosho_bango=str(9000000000+i), capacity=10, initial_designation_date=today-timedelta(days=400),
        designation_expiry_date=today+timedelta(days=730)) for i,service in enumerate((transition, retention))]
    staff = Supporter(staff_code="demo-staff", last_name="サンプル", first_name="職員", last_name_kana="サンプル",
        first_name_kana="ショクイン", office_id=office.id, employment_type="FULL_TIME", weekly_scheduled_minutes=2400,
        hire_date=today-timedelta(days=400), roles=[role])
    employer = EmployerMaster(company_name="サンプル就労先")
    db.session.add_all([staff, employer, *configs])
    db.session.flush()
    staff_pii = SupporterPII(supporter_id=staff.id, email="staff@example.invalid")
    staff_pii.set_password("RampDemo-Local1")
    db.session.add(staff_pii)
    for config, service, code, name in zip(configs, (transition, retention), ("demo-user","demo-retention"), ("移行","定着")):
        db.session.add(SupporterJobAssignment(supporter_id=staff.id, job_title_id=title.id,
            office_service_configuration_id=config.id, start_date=staff.hire_date, assigned_minutes=1200))
        user = User(user_code=code, display_name=f"サンプル {name}", status_id=status.id,
            primary_supporter_id=staff.id, service_start_date=today-timedelta(days=30))
        db.session.add(user)
        db.session.flush()
        pii = UserPII(user_id=user.id, email=f"{code}@example.invalid")
        pii.last_name, pii.first_name = "サンプル", name
        pii.set_password("RampDemo-Local1")
        certificate = ServiceCertificate(user_id=user.id, office_service_configuration_id=config.id,
            certificate_issue_date=today-timedelta(days=60), municipality_master_id=municipality.id, status="ACTIVE")
        db.session.add_all([pii, certificate])
        db.session.flush()
        db.session.add(GrantedService(certificate_id=certificate.id, service_type_master_id=service.id,
            granted_start_date=today-timedelta(days=30), granted_end_date=today+timedelta(days=330)))
        if service == retention:
            db.session.add(JobPlacementLog(user_id=user.id, employer_id=employer.id,
                placement_date=today-timedelta(days=300), support_scenario="NEW_PLACEMENT"))
            db.session.flush()
            # The regular service commits; seed it last so a failure can roll back the whole fixture.
            JobRetentionService.start_retention_support(user.id, config.id, today, today+timedelta(days=149),
                                                        staff.id, "サンプル利用の開始")
        else:
            plan = SupportPlan(user_id=user.id, plan_status="PENDING_CONSENT", sabikan_approved_by_id=staff.id,
                sabikan_approved_at=get_jst_now(), plan_start_date=today, plan_end_date=today+timedelta(days=90),
                draft_created_at=today, plan_version=1)
            db.session.add(plan)
            db.session.flush()
            db.session.add(LongTermGoal(plan_id=plan.id, description="週3日の通所を続ける",
                challenges="本人が無理なく続けられる通所ペースを確かめたい",
                target_period_start=plan.plan_start_date, target_period_end=plan.plan_end_date))
