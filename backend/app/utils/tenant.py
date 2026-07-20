# backend/app/utils/tenant.py

from backend.app.models import Supporter, OfficeSetting, SupporterJobAssignment
from backend.app.domain.attendance.exceptions import AttendanceForbiddenError
from backend.app.extensions import db

def extract_staff_id(identity: str) -> int:
    """Extracts staff ID from JWT identity string strictly."""
    if not identity or not isinstance(identity, str):
        raise AttendanceForbiddenError("Invalid identity format")
    parts = identity.split(":")
    if len(parts) != 2 or parts[0] != "staff":
        raise AttendanceForbiddenError("Invalid identity format")
    staff_id_str = parts[1]
    if not staff_id_str.isascii() or not staff_id_str.isdecimal() or staff_id_str.startswith('0'):
        raise AttendanceForbiddenError("Invalid identity format")
    try:
        staff_id = int(staff_id_str)
        if staff_id <= 0:
            raise AttendanceForbiddenError("Invalid identity format")
        return staff_id
    except ValueError:
        raise AttendanceForbiddenError("Invalid identity format")

def resolve_tenant_scope(supporter_id: int, role_scopes: list) -> dict:
    has_system = 'SYSTEM' in role_scopes
    has_corporate = 'CORPORATE' in role_scopes
    has_job = 'JOB' in role_scopes

    if has_corporate:
        admin_supp = db.session.get(Supporter, supporter_id)
        if not admin_supp or not admin_supp.office_id:
            raise AttendanceForbiddenError("Supporter or office not found for corporate admin")

        office = db.session.get(OfficeSetting, admin_supp.office_id)
        if not office or not office.corporation_id:
            raise AttendanceForbiddenError("Office or corporation not found for corporate admin")

        return {'level': 'CORPORATE', 'corp_id': office.corporation_id, 'self_only': False}

    if has_system:
        # SYSTEM単独の場合は全件許可せず、SYSTEM_SELFとする
        return {'level': 'SYSTEM_SELF', 'corp_id': None, 'self_only': True}

    if has_job:
        # JOB admin scope is not fully implemented for cross-staff management.
        # Degrade to JOB_SELF level (self_only) for personal operations.
        return {'level': 'JOB_SELF', 'corp_id': None, 'self_only': True}

    # Empty role_scopes implies general staff
    return {'level': 'STAFF', 'corp_id': None, 'self_only': True}

def validate_target_supporter_tenant(scope: dict, requester_id: int, target_supporter_id: int):
    if scope['self_only']:
        if requester_id != target_supporter_id:
            raise AttendanceForbiddenError("Access to other staff's data is forbidden")
        return True

    target_supporter = db.session.get(Supporter, target_supporter_id)
    if not target_supporter or not target_supporter.office_id:
        raise AttendanceForbiddenError("Target supporter or office not found")

    if scope['level'] == 'CORPORATE':
        target_office = db.session.get(OfficeSetting, target_supporter.office_id)
        if not target_office or target_office.corporation_id != scope['corp_id']:
            raise AttendanceForbiddenError("Target supporter is outside of corporate scope")

    return True

def filter_query_by_tenant_scope(scope: dict, query_tcs=None, query_shifts=None, requester_id: int = None):
    from backend.app.models import SupporterTimecard, StaffDailyShift, OfficeSetting, OfficeServiceConfiguration
    if scope['level'] == 'CORPORATE':
        corp_id = scope['corp_id']
        if query_tcs is not None:
            query_tcs = query_tcs.join(Supporter, SupporterTimecard.supporter_id == Supporter.id).join(OfficeSetting, Supporter.office_id == OfficeSetting.id).filter(OfficeSetting.corporation_id == corp_id)
        if query_shifts is not None:
            query_shifts = query_shifts.join(Supporter, StaffDailyShift.supporter_id == Supporter.id).join(OfficeSetting, Supporter.office_id == OfficeSetting.id).filter(OfficeSetting.corporation_id == corp_id)
        return query_tcs, query_shifts, corp_id

    if query_tcs is not None:
        query_tcs = query_tcs.filter(SupporterTimecard.supporter_id == requester_id)
    if query_shifts is not None:
        query_shifts = query_shifts.filter(StaffDailyShift.supporter_id == requester_id)
    return query_tcs, query_shifts, None

def get_accessible_users_subquery(scope: dict, target_date, requester_id: int):
    from backend.app.models import ServiceCertificate, OfficeServiceConfiguration, OfficeSetting, SupporterJobAssignment
    from backend.app.extensions import db

    if scope['level'] == 'CORPORATE':
        corp_id = scope['corp_id']
        sq = db.session.query(ServiceCertificate.user_id).join(
            OfficeServiceConfiguration, ServiceCertificate.office_service_configuration_id == OfficeServiceConfiguration.id
        ).join(
            OfficeSetting, OfficeServiceConfiguration.office_id == OfficeSetting.id
        ).filter(OfficeSetting.corporation_id == corp_id).subquery()
        return sq

    # STAFF / SYSTEM_SELF / JOB_SELF level
    sq = db.session.query(ServiceCertificate.user_id).join(
        SupporterJobAssignment,
        ServiceCertificate.office_service_configuration_id == SupporterJobAssignment.office_service_configuration_id
    ).filter(
        SupporterJobAssignment.supporter_id == requester_id,
        SupporterJobAssignment.start_date <= target_date,
        (SupporterJobAssignment.end_date >= target_date) | (SupporterJobAssignment.end_date == None)
    ).subquery()
    return sq
