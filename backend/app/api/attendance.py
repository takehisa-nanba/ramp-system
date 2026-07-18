# backend/app/api/attendance.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date
from backend.app.extensions import db
from backend.app.models import SupporterTimecard, StaffDailyShift, AttendanceCorrectionRequest, Supporter, EmploymentShiftPattern, SupporterJobAssignment
from backend.app.services.attendance_service import AttendanceService

attendance_bp = Blueprint('attendance', __name__, url_prefix='/api/attendance')

@attendance_bp.route('/generate-shifts', methods=['POST'])
@jwt_required()
def generate_shifts():
    identity = get_jwt_identity()
    if not identity.startswith('staff:'):
        return jsonify({"msg": "Unauthorized"}), 403
        
    data = request.get_json() or {}
    year = data.get('year', date.today().year)
    month = data.get('month', date.today().month)
    supporter_id = data.get('supporter_id') # None if all
    ai_instruction = data.get('ai_instruction') # AI instruction if any
    
    svc = AttendanceService(db.session)
    count = svc.generate_monthly_shifts(year, month, supporter_id, ai_instruction)
    return jsonify({"msg": f"Generated {count} shifts.", "count": count}), 201

@attendance_bp.route('/shifts', methods=['GET'])
@jwt_required()
def get_shifts():
    identity = get_jwt_identity()
    if not identity.startswith('staff:'):
        return jsonify({"msg": "Unauthorized"}), 403
        
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    if not year or not month:
        return jsonify({"msg": "year and month are required"}), 400
        
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)
        
    shifts = StaffDailyShift.query.filter(
        StaffDailyShift.target_date >= start_date,
        StaffDailyShift.target_date < end_date
    ).order_by(StaffDailyShift.target_date.asc(), StaffDailyShift.planned_start_time.asc()).all()
    
    result = []
    for s in shifts:
        supporter = s.supporter
        if not supporter:
            continue
            
        supporter_name = f"{supporter.last_name} {supporter.first_name}"
        
        emp_type = supporter.employment_type
        if emp_type == 'FULL_TIME':
            emp_type_ja = '常勤'
        elif emp_type == 'PART_TIME':
            emp_type_ja = '非常勤'
        assignments = SupporterJobAssignment.query.filter(
            SupporterJobAssignment.supporter_id == supporter.id,
            SupporterJobAssignment.office_service_configuration_id == s.office_service_configuration_id,
            SupporterJobAssignment.start_date <= s.target_date,
            (SupporterJobAssignment.end_date >= s.target_date) | (SupporterJobAssignment.end_date == None)
        ).all()
        
        job_titles = []
        for a in assignments:
            if a.job_title:
                job_titles.append(a.job_title.title_name)
                
        if not job_titles:
            job_titles = ["職務未設定"]
            
        for title in job_titles:
            result.append({
                "id": s.id,
                "supporter_id": s.supporter_id,
                "supporter_name": supporter_name,
                "employment_type": emp_type_ja,
                "job_title": title,
                "target_date": s.target_date.isoformat(),
                "planned_start_time": s.planned_start_time.isoformat() if s.planned_start_time else None,
                "planned_end_time": s.planned_end_time.isoformat() if s.planned_end_time else None,
                "planned_break_minutes": s.planned_break_minutes,
                "is_confirmed": s.is_confirmed
            })
        
    return jsonify({"items": result}), 200

@attendance_bp.route('/shifts', methods=['POST'])
@jwt_required()
def create_shift():
    identity = get_jwt_identity()
    if not identity.startswith('staff:'):
        return jsonify({"msg": "Unauthorized"}), 403
    admin_id = int(identity.split(':')[1])
    data = request.get_json() or {}
    
    svc = AttendanceService(db.session)
    try:
        shift = svc.create_manual_shift(admin_id, data)
        return jsonify({"msg": "Shift created", "id": shift.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": str(e)}), 400

@attendance_bp.route('/shifts/<int:shift_id>', methods=['PUT'])
@jwt_required()
def update_shift(shift_id):
    identity = get_jwt_identity()
    if not identity.startswith('staff:'):
        return jsonify({"msg": "Unauthorized"}), 403
    admin_id = int(identity.split(':')[1])
    data = request.get_json() or {}
    
    svc = AttendanceService(db.session)
    try:
        svc.update_manual_shift(admin_id, shift_id, data)
        return jsonify({"msg": "Shift updated"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": str(e)}), 400

@attendance_bp.route('/shifts/<int:shift_id>', methods=['DELETE'])
@jwt_required()
def delete_shift(shift_id):
    identity = get_jwt_identity()
    if not identity.startswith('staff:'):
        return jsonify({"msg": "Unauthorized"}), 403
    admin_id = int(identity.split(':')[1])
    
    svc = AttendanceService(db.session)
    try:
        svc.delete_manual_shift(admin_id, shift_id)
        return jsonify({"msg": "Shift deleted"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": str(e)}), 400

@attendance_bp.route('/timecards/<int:timecard_id>', methods=['PUT'])
@jwt_required()
def direct_edit_timecard(timecard_id):
    """管理者によるタイムカードの直接編集"""
    identity = get_jwt_identity()
    if not identity.startswith('staff:'):
        return jsonify({"msg": "Unauthorized"}), 403
        
    approver_id = int(identity.split(':')[1])
        
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
    try:
        updated = svc.direct_edit_timecard(timecard_id, approver_id, edit_data)
        return jsonify({"msg": "Timecard updated successfully", "deemed_work_minutes": updated.deemed_work_minutes}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": str(e)}), 400

@attendance_bp.route('/requests', methods=['POST'])
@jwt_required()
def create_request():
    """一般スタッフからの修正申請"""
    identity = get_jwt_identity()
    supporter_id = int(identity.split(':')[1])
    
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
