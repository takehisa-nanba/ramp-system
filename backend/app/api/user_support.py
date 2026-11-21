from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app import db
from backend.app.models import User, AttendanceRecord, UserDailyLog, IndividualSupportGoal, SupportPlan, UserDailyLogSetting

from backend.app.models.support.daily_log import ParticipantActivity
from uuid import UUID
from datetime import datetime, time, timedelta
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
    start = datetime.combine(today, time.min)
    records = AttendanceRecord.query.filter(
        AttendanceRecord.user_id == user_id, AttendanceRecord.timestamp >= start,
        AttendanceRecord.timestamp < start + timedelta(days=1),
    ).order_by(AttendanceRecord.timestamp.asc(), AttendanceRecord.id.asc()).all()
    stamps = {record.record_type: record.timestamp for record in records}
    last_record = records[-1] if records else None
    status = "IDLE" if not last_record else (
        "CLOCKED_IN" if last_record.record_type == "CHECK_IN" else "CLOCKED_OUT"
    )

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
        "activities": [dict(id=a.id, content=a.content) for a in ParticipantActivity.query.filter_by(
            user_id=user_id, log_date=today).order_by(ParticipantActivity.id)],
        "pending_plan": SupportPlan.query.filter(SupportPlan.user_id == user_id,
            SupportPlan.plan_status == "PENDING_CONSENT", SupportPlan.sabikan_approved_by_id.isnot(None)).first() is not None,
        "attendance_status": status,
        "attendance": {
            "checked_in": "CHECK_IN" in stamps,
            "check_in_time": stamps["CHECK_IN"].replace(tzinfo=JST).isoformat() if "CHECK_IN" in stamps else None,
            "checked_out": "CHECK_OUT" in stamps,
            "check_out_time": stamps["CHECK_OUT"].replace(tzinfo=JST).isoformat() if "CHECK_OUT" in stamps else None,
        },
        "daily_log": {
            "morning_plan": (daily_log.custom_data or {}).get("morning_plan", "") if daily_log else "",
            "physical_condition_score": daily_log.physical_condition_score if daily_log else None,
            "sleep_quality_score": daily_log.sleep_quality_score if daily_log else None,
            "user_self_evaluation": daily_log.user_self_evaluation if daily_log else None,
        },
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
        
    User.query.filter_by(id=user_id).with_for_update().one()
    now = datetime.now(JST).replace(tzinfo=None)
    start = datetime.combine(now.date(), time.min)
    records = AttendanceRecord.query.filter(
        AttendanceRecord.user_id == user_id, AttendanceRecord.timestamp >= start,
        AttendanceRecord.timestamp < start + timedelta(days=1),
    ).all()
    existing = next((record for record in records if record.record_type == record_type), None)
    if existing:
        return jsonify({"msg": "Already recorded", "time": existing.timestamp.isoformat()}), 200
    if (record_type == "CHECK_OUT" and not records) or (record_type == "CHECK_IN" and records):
        return jsonify({"msg": "本日の打刻順序を確認してください。"}), 409
    journal = data.get("journal")
    if journal is not None:
        if not isinstance(journal, dict):
            return jsonify(msg="日報の入力を確認してください。"), 400
        field = "morning_plan" if record_type == "CHECK_IN" else "user_self_evaluation"
        value = journal.get(field)
        if not isinstance(value, str) or len(value) > 5000:
            return jsonify(msg="日報は5000字以内で入力してください。"), 400
        log = UserDailyLog.query.filter_by(user_id=user_id, log_date=now.date()).first()
        if not log:
            log = UserDailyLog(user_id=user_id, log_date=now.date(), location_type="ON_SITE", support_content_notes="")
            db.session.add(log)
        if record_type == "CHECK_IN":
            for key in ("physical_condition_score", "sleep_quality_score"):
                score = journal.get(key)
                if score is not None:
                    if type(score) is not int or not 1 <= score <= 5:
                        return jsonify(msg="体調・睡眠は1から5で選んでください。"), 400
                    setattr(log, key, score)
            log.custom_data = {**(log.custom_data or {}), field: value.strip()}
            log.morning_completed = True
        else:
            log.user_self_evaluation = value.strip()
            log.evening_completed = True
    new_record = AttendanceRecord(
        user_id=user_id,
        record_type=record_type,
        timestamp=now,
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
    
    User.query.filter_by(id=user_id).with_for_update().one()
    daily_log = UserDailyLog.query.filter_by(user_id=user_id, log_date=today).first()
    
    physical_condition = data.get('physical_condition_score')
    sleep_quality = data.get('sleep_quality_score')
    user_eval = data.get('user_self_evaluation')
    custom_data = data.get('custom_data', {})
    
    for score in (physical_condition, sleep_quality):
        if score is not None and (type(score) is not int or not 1 <= score <= 5):
            return jsonify({"msg": "評価は1から5で指定してください。"}), 400
    if not isinstance(custom_data, dict) or (user_eval is not None and not isinstance(user_eval, str)):
        return jsonify({"msg": "日報の入力を確認してください。"}), 400

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
    plan = SupportPlan.query.filter_by(user_id=user_id, office_service_configuration_id=None, plan_status="ACTIVE")\
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


@user_support_bp.get('/support-plans')
@jwt_required()
def list_my_support_plans():
    from backend.app.services.user_plan_consent import present_user_plan
    plans = SupportPlan.query.filter(
        SupportPlan.user_id == get_current_user_id(),
        db.or_(SupportPlan.plan_status == "ACTIVE",
               db.and_(SupportPlan.plan_status == "PENDING_CONSENT", SupportPlan.sabikan_approved_by_id.isnot(None))),
    ).order_by(SupportPlan.plan_start_date.desc(), SupportPlan.id.desc()).all()
    return jsonify(items=[present_user_plan(plan) for plan in plans])


@user_support_bp.post('/support-plans/<int:plan_id>/consent')
@jwt_required()
def consent_my_support_plan(plan_id):
    from backend.app.services.user_plan_consent import confirm_user_plan
    from backend.app.utils.errors import ValidationError
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or data.get("confirmed") is not True:
        raise ValidationError("内容を確認してから同意してください。")
    revision = data.get("revision")
    if not isinstance(revision, str) or len(revision) != 64:
        raise ValidationError("確認した計画をもう一度開いてください。")
    confirm_user_plan(get_current_user_id(), plan_id, revision)
    return jsonify(status="ACTIVE")

@user_support_bp.post('/activities')
@jwt_required()
def add_participant_activity():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify(msg="本人のログインが必要です。"), 403
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(msg="活動を入力してください。"), 400
    content = data.get("content")
    try:
        request_id = str(UUID(str(data.get("request_id"))))
    except ValueError:
        return jsonify(msg="活動の送信番号を確認してください。"), 400
    if not isinstance(content, str) or not 0 < len(content.strip()) <= 2000:
        return jsonify(msg="活動を2000字以内で入力してください。"), 400
    User.query.filter_by(id=user_id).with_for_update().one()
    duplicate = ParticipantActivity.query.filter_by(user_id=user_id, request_id=request_id).first()
    if duplicate:
        if duplicate.content != content.strip():
            return jsonify(msg="別の活動として再送してください。"), 409
        return jsonify(id=duplicate.id)
    today = datetime.now(JST).date()
    start = datetime.combine(today, time.min)
    latest = AttendanceRecord.query.filter(AttendanceRecord.user_id == user_id,
        AttendanceRecord.timestamp >= start, AttendanceRecord.timestamp < start + timedelta(days=1)
    ).order_by(AttendanceRecord.timestamp.desc(), AttendanceRecord.id.desc()).first()
    if not latest or latest.record_type != "CHECK_IN":
        return jsonify(msg="通所中に活動を追加できます。"), 409
    activity = ParticipantActivity(user_id=user_id, request_id=request_id, log_date=today, content=content.strip())
    db.session.add(activity)
    db.session.commit()
    return jsonify(id=activity.id), 201
