import logging

logger = logging.getLogger(__name__)

class AttendanceDomainError(Exception):
    """Base exception for all attendance domain errors."""
    status_code = 500
    def __init__(self, message="Attendance domain error"):
        super().__init__(message)
        self.message = message

class AttendanceValidationError(AttendanceDomainError):
    """Validation errors, maps to HTTP 400."""
    status_code = 400

class AttendanceForbiddenError(AttendanceDomainError):
    """Forbidden actions, maps to HTTP 403."""
    status_code = 403

class AttendanceNotFoundError(AttendanceDomainError):
    """Resource not found, maps to HTTP 404."""
    status_code = 404

class AttendanceConflictError(AttendanceDomainError):
    """State conflict, maps to HTTP 409."""
    status_code = 409

def handle_attendance_errors(func):
    from functools import wraps
    from flask import jsonify

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AttendanceDomainError as e:
            from backend.app.extensions import db
            db.session.rollback()
            return jsonify({"msg": e.message}), e.status_code
        except Exception as e:
            from backend.app.extensions import db
            db.session.rollback()
            logger.exception("Unexpected error in attendance API")
            return jsonify({"msg": "Internal server error"}), 500
    return wrapper
