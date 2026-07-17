# backend/app/api/attendance.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date
from backend.app.extensions import db
from backend.app.models import SupporterTimecard, StaffDailyShift, AttendanceCorrectionRequest, Supporter, EmploymentShiftPattern
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
    
    svc = AttendanceService(db.session)
    count = svc.generate_monthly_shifts(year, month, supporter_id)
    return jsonify({"msg": f"Generated {count} shifts.", "count": count}), 201

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
