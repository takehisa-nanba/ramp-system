# backend/app/api/attendance.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime, date
from zoneinfo import ZoneInfo
from backend.app.extensions import db
from backend.app.models import SupporterTimecard, StaffDailyShift, AttendanceCorrectionRequest, Supporter, EmploymentShiftPattern, SupporterJobAssignment, OfficeSetting, OfficeServiceConfiguration
from backend.app.services.attendance_service import AttendanceService
from backend.app.domain.attendance.exceptions import handle_attendance_errors, AttendanceForbiddenError, AttendanceNotFoundError
from backend.app.utils.tenant import extract_staff_id, resolve_tenant_scope, validate_target_supporter_tenant, filter_query_by_tenant_scope

attendance_bp = Blueprint('attendance', __name__, url_prefix='/api/attendance')

@attendance_bp.route('/generate-shifts', methods=['POST'])
@jwt_required()
@handle_attendance_errors
def generate_shifts():
    identity = get_jwt_identity()
    admin_id = extract_staff_id(identity)
    claims = get_jwt()
    role_scopes = claims.get('role_scopes', [])

    scope = resolve_tenant_scope(admin_id, role_scopes)
    if scope['level'] not in ['SYSTEM', 'CORPORATE']:
        raise AttendanceForbiddenError("Unauthorized")
        
    data = request.get_json() or {}
    year = data.get('year', date.today().year)
    month = data.get('month', date.today().month)
    supporter_id = data.get('supporter_id')

    if supporter_id:
        validate_target_supporter_tenant(scope, admin_id, supporter_id)

    ai_instruction = data.get('ai_instruction')

    svc = AttendanceService(db.session)
    count = svc.generate_monthly_shifts(year, month, supporter_id, ai_instruction, corp_id=scope['corp_id'])
    return jsonify({"msg": f"Generated {count} shifts.", "count": count}), 201

@attendance_bp.route('/shifts', methods=['GET'])
@jwt_required()
@handle_attendance_errors
def get_shifts():
    identity = get_jwt_identity()
    staff_id = extract_staff_id(identity)

    claims = get_jwt()
    role_scopes = claims.get('role_scopes', [])

    scope = resolve_tenant_scope(staff_id, role_scopes)
        
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    if not year or not month:
        return jsonify({"msg": "year and month are required"}), 400
        
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)
        
    query_shifts = StaffDailyShift.query.filter(
        StaffDailyShift.target_date >= start_date,
        StaffDailyShift.target_date < end_date
    )
    query_tcs = SupporterTimecard.query.filter(
        SupporterTimecard.work_date >= start_date,
        SupporterTimecard.work_date < end_date
    )

    query_tcs, query_shifts, _ = filter_query_by_tenant_scope(scope, query_tcs, query_shifts, requester_id=staff_id)

    shifts = query_shifts.all()
    tcs = query_tcs.all()

    records = {}
    for s in shifts:
        key = (s.supporter_id, s.target_date)
        records[key] = {"shift": s, "tcs": []}
        
    for tc in tcs:
        key = (tc.supporter_id, tc.work_date)
        if key not in records:
            records[key] = {"shift": None, "tcs": [tc]}
        else:
            records[key]["tcs"].append(tc)

    supporter_ids = list(set([k[0] for k in records.keys()]))
    supporters = Supporter.query.filter(Supporter.id.in_(supporter_ids)).all() if supporter_ids else []
    supporter_dict = {s.id: s for s in supporters}

    result = []
    for (supp_id, rec_date), data in records.items():
        supporter = supporter_dict.get(supp_id)
        if not supporter:
            continue

        s = data["shift"]
        tcs_list = data["tcs"]
        tcs_list.sort(key=lambda x: x.sequence_no)
        
        supporter_name = f"{supporter.last_name} {supporter.first_name}"
        emp_type = supporter.employment_type
        emp_type_ja = '常勤' if emp_type == 'FULL_TIME' else ('非常勤' if emp_type == 'PART_TIME' else emp_type)

        ongoing_tcs = [tc for tc in tcs_list if tc.check_out is None]
        rep_tc = None
        if len(ongoing_tcs) > 0:
            rep_tc = ongoing_tcs[-1]
        elif len(tcs_list) > 0:
            rep_tc = tcs_list[-1]

        title = "職務未設定"
        ref_obj = s if s else rep_tc
        if ref_obj:
            assignments = SupporterJobAssignment.query.filter(
                SupporterJobAssignment.supporter_id == supporter.id,
                SupporterJobAssignment.office_service_configuration_id == ref_obj.office_service_configuration_id,
                SupporterJobAssignment.start_date <= rec_date,
                (SupporterJobAssignment.end_date >= rec_date) | (SupporterJobAssignment.end_date == None)
            ).all()
            for a in assignments:
                if a.job_title:
                    title = a.job_title.title_name
                    break
        
        timecards_arr = []
        total_worked_seconds = 0
        actual_check_in = None
        actual_check_out = None
        has_ongoing = False

        for tc in tcs_list:
            if not actual_check_in or (tc.check_in and tc.check_in < actual_check_in):
                actual_check_in = tc.check_in

            if tc.check_out is None:
                has_ongoing = True
            elif not has_ongoing:
                if not actual_check_out or tc.check_out > actual_check_out:
                    actual_check_out = tc.check_out

            if tc.check_out and tc.check_in:
                duration = (tc.check_out - tc.check_in).total_seconds()
                break_sec = (tc.total_break_minutes or 0) * 60
                total_worked_seconds += max(0, duration - break_sec)

            timecards_arr.append({
                "id": tc.id,
                "sequence_no": tc.sequence_no,
                "office_id": tc.office_id,
                "location_type": tc.location_type,
                "check_in": tc.check_in.replace(tzinfo=ZoneInfo("Asia/Tokyo")).isoformat() if tc.check_in else None,
                "check_out": tc.check_out.replace(tzinfo=ZoneInfo("Asia/Tokyo")).isoformat() if tc.check_out else None,
                "total_break_minutes": tc.total_break_minutes or 0
            })

        if has_ongoing:
            actual_check_out = None
        
        result.append({
            "id": s.id if s else f"tc_{rep_tc.id}" if rep_tc else None,
            "supporter_id": supp_id,
            "supporter_name": supporter_name,
            "employment_type": emp_type_ja,
            "job_title": title,
            "target_date": rec_date.isoformat(),
            "planned_start_time": s.planned_start_time.isoformat() if s and s.planned_start_time else None,
            "planned_end_time": s.planned_end_time.isoformat() if s and s.planned_end_time else None,
            "planned_break_minutes": s.planned_break_minutes if s else 0,
            "is_confirmed": s.is_confirmed if s else True,
            "actual_check_in": actual_check_in.replace(tzinfo=ZoneInfo("Asia/Tokyo")).isoformat() if actual_check_in else None,
            "actual_check_out": actual_check_out.replace(tzinfo=ZoneInfo("Asia/Tokyo")).isoformat() if actual_check_out else None,
            "total_worked_seconds": total_worked_seconds,
            "timecards": timecards_arr
        })
        
    result.sort(key=lambda x: (x["target_date"], x["planned_start_time"] or "99:99"))

    return jsonify({"items": result}), 200

@attendance_bp.route('/shifts', methods=['POST'])
@jwt_required()
@handle_attendance_errors
def create_shift():
    identity = get_jwt_identity()
    admin_id = extract_staff_id(identity)
    claims = get_jwt()
    role_scopes = claims.get('role_scopes', [])

    scope = resolve_tenant_scope(admin_id, role_scopes)
    if scope['level'] not in ['SYSTEM', 'CORPORATE']:
        raise AttendanceForbiddenError("Unauthorized")

    data = request.get_json() or {}

    target_supporter_id = data.get('supporter_id')
    if not target_supporter_id:
        return jsonify({"msg": "supporter_id is required"}), 400

    validate_target_supporter_tenant(scope, admin_id, target_supporter_id)

    svc = AttendanceService(db.session)
    shift = svc.create_manual_shift(admin_id, data)
    return jsonify({"msg": "Shift created", "id": shift.id}), 201

@attendance_bp.route('/shifts/<int:shift_id>', methods=['PUT'])
@jwt_required()
@handle_attendance_errors
def update_shift(shift_id):
    identity = get_jwt_identity()
    admin_id = extract_staff_id(identity)
    claims = get_jwt()
    role_scopes = claims.get('role_scopes', [])

    scope = resolve_tenant_scope(admin_id, role_scopes)
    if scope['level'] not in ['SYSTEM', 'CORPORATE']:
        raise AttendanceForbiddenError("Unauthorized")

    # Check existing shift
    shift = StaffDailyShift.query.get(shift_id)
    if not shift:
        raise AttendanceNotFoundError("Shift not found")

    validate_target_supporter_tenant(scope, admin_id, shift.supporter_id)

    data = request.get_json() or {}
    target_supporter_id = data.get('supporter_id')
    if target_supporter_id and target_supporter_id != shift.supporter_id:
        validate_target_supporter_tenant(scope, admin_id, target_supporter_id)

    svc = AttendanceService(db.session)
    svc.update_manual_shift(admin_id, shift_id, data)
    return jsonify({"msg": "Shift updated"}), 200

@attendance_bp.route('/shifts/<int:shift_id>', methods=['DELETE'])
@jwt_required()
@handle_attendance_errors
def delete_shift(shift_id):
    identity = get_jwt_identity()
    admin_id = extract_staff_id(identity)
    claims = get_jwt()
    role_scopes = claims.get('role_scopes', [])

    scope = resolve_tenant_scope(admin_id, role_scopes)
    if scope['level'] not in ['SYSTEM', 'CORPORATE']:
        raise AttendanceForbiddenError("Unauthorized")

    shift = StaffDailyShift.query.get(shift_id)
    if not shift:
        raise AttendanceNotFoundError("Shift not found")

    validate_target_supporter_tenant(scope, admin_id, shift.supporter_id)

    svc = AttendanceService(db.session)
    svc.delete_manual_shift(admin_id, shift_id)
    return jsonify({"msg": "Shift deleted"}), 200

@attendance_bp.route('/timecards/<int:timecard_id>', methods=['PUT'])
@jwt_required()
@handle_attendance_errors
def direct_edit_timecard(timecard_id):
    """管理者によるタイムカードの直接編集"""
    identity = get_jwt_identity()
    admin_id = extract_staff_id(identity)
    claims = get_jwt()
    role_scopes = claims.get('role_scopes', [])

    scope = resolve_tenant_scope(admin_id, role_scopes)
    if scope['level'] not in ['SYSTEM', 'CORPORATE']:
        raise AttendanceForbiddenError("Unauthorized")
        
    timecard = SupporterTimecard.query.get(timecard_id)
    if not timecard:
        raise AttendanceNotFoundError("Timecard not found")

    validate_target_supporter_tenant(scope, admin_id, timecard.supporter_id)
        
    data = request.get_json() or {}

    # ISO string to datetime parsing
    check_in = datetime.fromisoformat(data['check_in'].replace('Z', '+00:00')) if data.get('check_in') else None
    check_out = datetime.fromisoformat(data['check_out'].replace('Z', '+00:00')) if data.get('check_out') else None

    edit_data = {
        'check_in': check_in,
        'check_out': check_out,
        'break_minutes': data.get('break_minutes'),
        'is_absent': data.get('is_absent'),
        'absence_type': data.get('absence_type')
    }

    svc = AttendanceService(db.session)
    updated = svc.direct_edit_timecard(timecard_id, admin_id, edit_data)
    return jsonify({"msg": "Timecard updated successfully", "deemed_work_minutes": updated.deemed_work_minutes}), 200

@attendance_bp.route('/requests', methods=['POST'])
@jwt_required()
@handle_attendance_errors
def create_request():
    """一般スタッフからの修正申請"""
    identity = get_jwt_identity()
    supporter_id = extract_staff_id(identity)

    data = request.get_json() or {}
    req = AttendanceCorrectionRequest(
        supporter_id=supporter_id,
        target_date=date.fromisoformat(data['target_date']),
        record_type=data.get('record_type', 'TIMECARD'),
        requested_timestamp=datetime.now(),
        request_reason=data.get('reason', ''),
        request_status='PENDING'
    )
    db.session.add(req)
    db.session.commit()
    return jsonify({"msg": "Request created", "id": req.id}), 201

@attendance_bp.route('/clock-in', methods=['POST'])
@jwt_required()
@handle_attendance_errors
def clock_in():
    identity = get_jwt_identity()
    supporter_id = extract_staff_id(identity)

    data = request.get_json() or {}
    office_id = data.get('office_id')
    if not office_id:
        return jsonify({"msg": "office_id is required"}), 400
        
    location_type = data.get('location_type')
    if not location_type:
        return jsonify({"msg": "location_type is required"}), 400
        
    location_detail = data.get('location_detail', '')

    svc = AttendanceService(db.session)
    timecard = svc.clock_in(supporter_id, office_id, location_type, location_detail)
    db.session.commit()
    return jsonify({
        "msg": "Clocked in successfully",
        "timecard_id": timecard.id,
        "sequence_no": timecard.sequence_no,
        "check_in": timecard.check_in.replace(tzinfo=ZoneInfo("Asia/Tokyo")).isoformat()
    }), 201

@attendance_bp.route('/timecards/<int:timecard_id>/clock-out', methods=['POST'])
@jwt_required()
@handle_attendance_errors
def clock_out(timecard_id):
    identity = get_jwt_identity()
    supporter_id = extract_staff_id(identity)

    data = request.get_json() or {}
    break_minutes = data.get('break_minutes', 0)

    svc = AttendanceService(db.session)
    timecard = svc.clock_out(supporter_id, timecard_id=timecard_id, break_minutes=break_minutes)
    db.session.commit()
    return jsonify({
        "msg": "Clocked out successfully",
        "timecard_id": timecard.id,
        "check_out": timecard.check_out.replace(tzinfo=ZoneInfo("Asia/Tokyo")).isoformat()
    }), 200

@attendance_bp.route('/timecards', methods=['GET'])
@jwt_required()
@handle_attendance_errors
def get_timecards():
    identity = get_jwt_identity()
    staff_id = extract_staff_id(identity)
        
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({"msg": "date is required"}), 400
        
    try:
        target_date = date.fromisoformat(date_str)
    except ValueError:
        return jsonify({"msg": "Invalid date format"}), 400
        
    claims = get_jwt()
    role_scopes = claims.get('role_scopes', [])

    scope = resolve_tenant_scope(staff_id, role_scopes)

    query = SupporterTimecard.query.filter(SupporterTimecard.work_date == target_date)
    query, _, _ = filter_query_by_tenant_scope(scope, query_tcs=query, requester_id=staff_id)

    timecards = query.order_by(SupporterTimecard.sequence_no).all()

    result = []
    for tc in timecards:
        result.append({
            "id": tc.id,
            "sequence_no": tc.sequence_no,
            "office_id": tc.office_id,
            "location_type": tc.location_type,
            "check_in": tc.check_in.replace(tzinfo=ZoneInfo("Asia/Tokyo")).isoformat() if tc.check_in else None,
            "check_out": tc.check_out.replace(tzinfo=ZoneInfo("Asia/Tokyo")).isoformat() if tc.check_out else None,
            "total_break_minutes": tc.total_break_minutes or 0
        })
        
    return jsonify(result), 200
