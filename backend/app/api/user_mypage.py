from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app.extensions import db
from backend.app.models.support.attendance_workflow import AttendanceRecord
from backend.app.models.support.daily_log import UserDailyLog
from datetime import date, datetime, timedelta
from sqlalchemy.exc import IntegrityError

bp = Blueprint('user_mypage', __name__, url_prefix='/api/mypage')

def get_current_user_id():
    identity = get_jwt_identity()
    if isinstance(identity, str) and identity.startswith('user:'):
        return int(identity.split(':')[1])
    return None

@bp.route('/today', methods=['GET'])
@jwt_required(optional=True)
def get_today():
    user_id = get_current_user_id()
    if not user_id:
        user_id = 1 # 開発・テスト用フォールバック

    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    tomorrow_start = today_start + timedelta(days=1)
    
    # 今日の打刻状態
    records = AttendanceRecord.query.filter(
        AttendanceRecord.user_id == user_id,
        AttendanceRecord.timestamp >= today_start,
        AttendanceRecord.timestamp < tomorrow_start
    ).order_by(AttendanceRecord.timestamp.asc()).all()
    
    check_in = next((r for r in records if r.record_type == 'CHECK_IN'), None)
    check_out = next((r for r in records if r.record_type == 'CHECK_OUT'), None)
    
    # 今日の日報状態
    daily_log = UserDailyLog.query.filter_by(user_id=user_id, log_date=today).first()
    
    return jsonify({
        'attendance': {
            'checked_in': check_in is not None,
            'check_in_time': check_in.timestamp.isoformat() if check_in else None,
            'checked_out': check_out is not None,
            'check_out_time': check_out.timestamp.isoformat() if check_out else None,
        },
        'daily_log': {
            'physical_condition_score': daily_log.physical_condition_score if daily_log and daily_log.physical_condition_score else 3,
            'sleep_quality_score': daily_log.sleep_quality_score if daily_log and daily_log.sleep_quality_score else 3,
            'user_self_evaluation': daily_log.user_self_evaluation if daily_log else ''
        }
    }), 200

@bp.route('/attendance', methods=['POST'])
@jwt_required(optional=True)
def post_attendance():
    user_id = get_current_user_id() or 1
    data = request.json
    record_type = data.get('record_type')
    
    if record_type not in ['CHECK_IN', 'CHECK_OUT']:
        return jsonify({'msg': 'Invalid record_type'}), 400
        
    record = AttendanceRecord(
        user_id=user_id,
        record_type=record_type,
        timestamp=datetime.now()
    )
    db.session.add(record)
    db.session.commit()
    return jsonify({'msg': 'Success'}), 200

@bp.route('/daily-log', methods=['POST'])
@jwt_required(optional=True)
def post_daily_log():
    user_id = get_current_user_id() or 1
    data = request.json
    today = date.today()
    
    daily_log = UserDailyLog.query.filter_by(user_id=user_id, log_date=today).first()
    if not daily_log:
        daily_log = UserDailyLog(
            user_id=user_id,
            log_date=today,
            location_type='ON_SITE',
            support_content_notes='',
            auto_created=False
        )
        db.session.add(daily_log)
        try:
            db.session.flush()
        except IntegrityError:
            db.session.rollback()
            daily_log = UserDailyLog.query.filter_by(user_id=user_id, log_date=today).first()
            
    daily_log.physical_condition_score = data.get('physical_condition_score', 3)
    daily_log.sleep_quality_score = data.get('sleep_quality_score', 3)
    daily_log.user_self_evaluation = data.get('user_self_evaluation', '')
    
    db.session.commit()
    return jsonify({'msg': 'Success'}), 200
