from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app import db
from backend.app.models import User, AttendanceRecord, UserDailyLog, IndividualSupportGoal, SupportPlan, UserDailyLogSetting

from datetime import datetime
from backend.app.utils.timezone import JST

user_support_bp = Blueprint('user_support', __name__, url_prefix='/api/user')

def get_current_user_id():
    identity = get_jwt_identity()
    if isinstance(identity, str) and identity.startswith('user:'):
        return int(identity.split(':')[1])
    return None

@user_support_bp.route('/status', methods=['GET'])
@jwt_required()
def get_user_status():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"msg": "Unauthorized or not a client account"}), 403
        
    today = datetime.now(JST).date()
    
    # 勤怠状況 (最新のレコードを取得)
    last_record = AttendanceRecord.query.filter_by(user_id=user_id)\
        .order_by(AttendanceRecord.timestamp.desc()).first()
    
    status = "IDLE"
    if last_record and last_record.timestamp.date() == today:
        status = "CLOCKED_IN" if last_record.record_type == 'CHECK_IN' else "CLOCKED_OUT"
        
    # 本日の日報を取得
    daily_log = UserDailyLog.query.filter_by(user_id=user_id, log_date=today).first()
    
    # 事業所の設定を取得

    user = User.query.get(user_id)
    office_id = user.primary_supporter.office_id if user.primary_supporter else None
    
    log_setting = UserDailyLogSetting.query.filter_by(office_id=office_id).first()
    config = log_setting.config if log_setting else {
        "morning_fields": [
            {"id": "mood", "label": "今日の気分", "type": "score", "required": True}
        ],
        "evening_fields": [
            {"id": "review", "label": "今日頑張ったことや、明日の目標", "type": "text", "required": True}
        ]
    }
    
    return jsonify({
        "attendance_status": status,
        "last_record_time": last_record.timestamp.isoformat() if last_record else None,
        "has_morning_log": daily_log.morning_completed if daily_log else False,
        "has_evening_log": daily_log.evening_completed if daily_log else False,
        "log_config": config
    }), 200




@user_support_bp.route('/attendance', methods=['POST'])
@jwt_required()
def record_attendance():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"msg": "Unauthorized"}), 403
        
    data = request.get_json() or {}
    record_type = data.get('type') # 'CHECK_IN' or 'CHECK_OUT'
    location = data.get('location')
    
    if record_type not in ['CHECK_IN', 'CHECK_OUT']:
        return jsonify({"msg": "Invalid record type"}), 400
        
    new_record = AttendanceRecord(
        user_id=user_id,
        record_type=record_type,
        timestamp=datetime.now(JST),
        location_data=location
    )
    db.session.add(new_record)
    db.session.commit()
    
    return jsonify({"msg": "Recorded successfully", "time": new_record.timestamp.isoformat()}), 201

@user_support_bp.route('/daily-log', methods=['POST'])
@jwt_required()
def submit_daily_log():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"msg": "Unauthorized"}), 403
        
    data = request.get_json() or {}
    today = datetime.now(JST).date()
    
    daily_log = UserDailyLog.query.filter_by(user_id=user_id, log_date=today).first()
    
    physical_condition = data.get('physical_condition_score')
    sleep_quality = data.get('sleep_quality_score')
    user_eval = data.get('user_self_evaluation')
    custom_data = data.get('custom_data', {})
    
    if not daily_log:
        daily_log = UserDailyLog(
            user_id=user_id,
            log_date=today,
            location_type='ON_SITE',
            support_content_notes='利用者の入力待ち'
        )
        db.session.add(daily_log)
    
    if physical_condition is not None:
        daily_log.physical_condition_score = physical_condition
    if sleep_quality is not None:
        daily_log.sleep_quality_score = sleep_quality
    if user_eval is not None:
        daily_log.user_self_evaluation = user_eval
        
    # custom_data をマージ
    if daily_log.custom_data:
        merged = dict(daily_log.custom_data)
        merged.update(custom_data)
        daily_log.custom_data = merged
    else:
        daily_log.custom_data = custom_data
        
    # 入力完了フラグの更新
    if data.get('morning_completed'):
        daily_log.morning_completed = True
    if data.get('evening_completed'):
        daily_log.evening_completed = True
        
    db.session.commit()



    return jsonify({"msg": "Updated successfully"}), 200

@user_support_bp.route('/goals', methods=['GET'])
@jwt_required()
def get_goals():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"msg": "Unauthorized"}), 403
        
    # 最新の有効な支援計画を取得
    plan = SupportPlan.query.filter_by(user_id=user_id)\
        .order_by(SupportPlan.plan_start_date.desc()).first()
        
    if not plan:
        return jsonify({"goals": []}), 200
        
    # 長期目標 -> 短期目標 -> 個別目標 の順に辿る
    goals = []
    for ltg in plan.long_term_goals:
        for stg in ltg.short_term_goals:
            for goal in stg.individual_goals:
                goals.append({
                    "id": goal.id,
                    "content": goal.concrete_goal
                })


            
    return jsonify({"goals": goals}), 200
