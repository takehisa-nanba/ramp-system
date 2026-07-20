# backend/app/api/activities.py

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app.extensions import db
from datetime import datetime, date
from zoneinfo import ZoneInfo
from backend.app.services.daily_log_service import DailyLogService
from backend.app.domain.attendance.exceptions import handle_attendance_errors

activities_bp = Blueprint('activities', __name__, url_prefix='/api/activities')

@activities_bp.route('/allocations', methods=['POST'])
@jwt_required()
@handle_attendance_errors
def allocate_activity():
    from backend.app.utils.tenant import extract_staff_id
    supporter_id = extract_staff_id(get_jwt_identity())
    if not supporter_id:
        return jsonify({"msg": "Unauthorized"}), 403
    data = request.get_json() or {}
    
    required_fields = [
        "supporter_timecard_id",
        "office_service_configuration_id",
        "job_title_id",
        "staff_activity_master_id",
        "allocation_recording_mode"
    ]
    for field in required_fields:
        if field not in data:
            from backend.app.domain.attendance.exceptions import AttendanceValidationError
            raise AttendanceValidationError(f"Missing required field: {field}")
            
        if field in ["office_service_configuration_id", "job_title_id"]:
            val = data.get(field)
            if val is None or not isinstance(val, int) or val <= 0:
                from backend.app.domain.attendance.exceptions import AttendanceValidationError
                raise AttendanceValidationError(f"Invalid value for field: {field}")

    svc = DailyLogService()
    allocation = svc.record_activity_allocation(supporter_id, data)
    db.session.commit()
    return jsonify({
        "msg": "Activity allocated successfully",
        "allocation_id": allocation.id
    }), 201
