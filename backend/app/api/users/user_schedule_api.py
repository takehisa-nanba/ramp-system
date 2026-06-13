# backend/app/api/users/user_schedule_api.py
from datetime import date, datetime, timedelta
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app.extensions import db
from backend.app.models import (
    UserScheduleTemplate, UserDailySchedule, UserScheduleRequest, User
)
from backend.app.services.user_schedule_service import UserScheduleService, get_legacy_schedule_status
from backend.app.utils.errors import ValidationError
from backend.app.utils.timezone import get_jst_today
from . import users_bp

@users_bp.route('/<int:user_id>/schedule-templates', methods=['GET'])
@jwt_required()
def get_schedule_templates(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({
            "success": False,
            "error": {
                "code": "NOT_FOUND",
                "message": "利用者が見つかりません。"
            }
        }), 404
    
    templates = UserScheduleTemplate.query.filter_by(user_id=user_id).all()
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    template_dict = {t.day_of_week: t for t in templates}
    
    result = []
    for day in day_order:
        t = template_dict.get(day)
        result.append({
            "day_of_week": day,
            "is_scheduled": t.is_scheduled if t else False,
            "start_time": t.start_time if t else None,
            "end_time": t.end_time if t else None,
            "location_type": t.location_type if t else "ON_SITE"
        })
    return jsonify({"items": result}), 200

@users_bp.route('/<int:user_id>/schedule-templates', methods=['POST'])
@jwt_required()
def save_schedule_templates(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({
            "success": False,
            "error": {
                "code": "NOT_FOUND",
                "message": "利用者が見つかりません。"
            }
        }), 404
        
    data = request.get_json() or []
    
    try:
        # トランザクション内で実行
        UserScheduleTemplate.query.filter_by(user_id=user_id).delete()
        
        for item in data:
            day = item.get('day_of_week')
            is_sch = item.get('is_scheduled', False)
            start = item.get('start_time')
            end = item.get('end_time')
            location_type = item.get('location_type', 'ON_SITE')
            
            if is_sch and start and end:
                sh, sm = map(int, start.split(':'))
                eh, em = map(int, end.split(':'))
                if (eh * 60 + em) <= (sh * 60 + sm):
                    raise ValidationError("終了時間は開始時間より後の時間に設定してください。")
            
            template = UserScheduleTemplate(
                user_id=user_id,
                day_of_week=day,
                is_scheduled=is_sch,
                start_time=start if is_sch else None,
                end_time=end if is_sch else None,
                location_type=location_type if is_sch else None
            )
            db.session.add(template)
            
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "曜日別予定テンプレートを保存しました。月間予定への反映は「一括適用」から行ってください。"
        }), 200
        
    except ValidationError as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(e)
            }
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": str(e)
            }
        }), 500

@users_bp.route('/<int:user_id>/schedule-requests', methods=['GET'])
@jwt_required()
def get_schedule_requests(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({
            "success": False,
            "error": {
                "code": "NOT_FOUND",
                "message": "利用者が見つかりません。"
            }
        }), 404
        
    requests = UserScheduleRequest.query.filter_by(user_id=user_id).order_by(UserScheduleRequest.target_date.desc()).all()
    
    result = []
    for r in requests:
        result.append({
            "id": r.id,
            "target_date": r.target_date.strftime('%Y-%m-%d'),
            "request_type": r.request_type,
            "requested_start_time": r.requested_start_time,
            "requested_end_time": r.requested_end_time,
            "request_reason": r.request_reason,
            "request_status": r.request_status,
            "requested_by_user_id": r.requested_by_user_id,
            "requested_by_supporter_id": r.requested_by_supporter_id,
            "decided_by_supporter_id": r.decided_by_supporter_id,
            "decided_at": r.decided_at.isoformat() if r.decided_at else None,
            "decision_reason": r.decision_reason
        })
    return jsonify({"items": result}), 200

@users_bp.route('/<int:user_id>/schedule-requests', methods=['POST'])
@jwt_required()
def create_schedule_request(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({
            "success": False,
            "error": {
                "code": "NOT_FOUND",
                "message": "利用者が見つかりません。"
            }
        }), 404
        
    data = request.get_json() or {}
    
    target_date_str = data.get('target_date')
    request_type = data.get('request_type')
    request_reason = data.get('request_reason')
    start_time = data.get('requested_start_time')
    end_time = data.get('requested_end_time')
    
    if not target_date_str or not request_type or not request_reason:
        return jsonify({
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "必須フィールドが不足しています。"
            }
        }), 400
        
    try:
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "日付フォーマットが不正です。YYYY-MM-DDを指定してください。"
            }
        }), 400
        
    identity = get_jwt_identity()
    requested_by_user_id = None
    requested_by_supporter_id = None
    
    if identity.startswith('staff:'):
        requested_by_supporter_id = int(identity.split(':')[1])
    elif identity.startswith('user:'):
        requested_by_user_id = int(identity.split(':')[1])
        if requested_by_user_id != user_id:
            return jsonify({
                "success": False,
                "error": {
                    "code": "FORBIDDEN",
                    "message": "他の利用者の申請を作成する権限がありません。"
                }
            }), 403
            
    service = UserScheduleService()
    try:
        req = service.create_schedule_request(
            user_id=user_id,
            target_date=target_date,
            request_type=request_type,
            request_reason=request_reason,
            requested_start_time=start_time,
            requested_end_time=end_time,
            requested_by_user_id=requested_by_user_id,
            requested_by_supporter_id=requested_by_supporter_id
        )
        return jsonify({
            "success": True,
            "item": {
                "id": req.id,
                "target_date": req.target_date.strftime('%Y-%m-%d'),
                "request_type": req.request_type,
                "request_status": req.request_status
            }
        }), 201
    except ValidationError as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(e)
            }
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": str(e)
            }
        }), 500

@users_bp.route('/<int:user_id>/daily-schedules', methods=['GET'])
@jwt_required()
def get_daily_schedules(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({
            "success": False,
            "error": {
                "code": "NOT_FOUND",
                "message": "利用者が見つかりません。"
            }
        }), 404
        
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    query = UserDailySchedule.query.filter_by(user_id=user_id)
    
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            query = query.filter(UserDailySchedule.date >= start_date)
        except ValueError:
            return jsonify({
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "start_date のフォーマットが不正です。"
                }
            }), 400
            
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            query = query.filter(UserDailySchedule.date <= end_date)
        except ValueError:
            return jsonify({
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "end_date のフォーマットが不正です。"
                }
            }), 400
            
    schedules = query.order_by(UserDailySchedule.date.asc()).all()
    
    # 打刻実績を取得してマージ
    from backend.app.models.support.attendance_workflow import AttendanceRecord
    from sqlalchemy import func
    
    attendances_in = AttendanceRecord.query.filter_by(
        user_id=user_id,
        record_type='CHECK_IN'
    )
    if start_date_str:
        attendances_in = attendances_in.filter(func.date(AttendanceRecord.timestamp) >= start_date)
    if end_date_str:
        attendances_in = attendances_in.filter(func.date(AttendanceRecord.timestamp) <= end_date)
    attendances_in = attendances_in.all()
    
    attendances_out = AttendanceRecord.query.filter_by(
        user_id=user_id,
        record_type='CHECK_OUT'
    )
    if start_date_str:
        attendances_out = attendances_out.filter(func.date(AttendanceRecord.timestamp) >= start_date)
    if end_date_str:
        attendances_out = attendances_out.filter(func.date(AttendanceRecord.timestamp) <= end_date)
    attendances_out = attendances_out.all()
    
    att_in_map = {att.timestamp.date(): att for att in attendances_in}
    att_out_map = {att.timestamp.date(): att for att in attendances_out}
    
    # パディング処理
    result = []
    if start_date_str and end_date_str:
        sched_map = {s.date: s for s in schedules}
        curr = start_date
        while curr <= end_date:
            check_in = att_in_map.get(curr)
            check_out = att_out_map.get(curr)
            s = sched_map.get(curr)
            
            if s:
                result.append({
                    "id": s.id,
                    "date": s.date.strftime('%Y-%m-%d'),
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                    "is_scheduled": s.is_scheduled,
                    "schedule_status": get_legacy_schedule_status(s),
                    "status": s.approval_status,
                    "approval_status": s.approval_status,
                    "location_type": s.location_type,
                    "schedule_request_id": s.schedule_request_id,
                    "decision_reason": s.decision_reason,
                    "actual_check_in": check_in.timestamp.strftime('%H:%M') if check_in else None,
                    "actual_check_out": check_out.timestamp.strftime('%H:%M') if check_out else None,
                })
            else:
                result.append({
                    "id": None,
                    "date": curr.strftime('%Y-%m-%d'),
                    "start_time": None,
                    "end_time": None,
                    "is_scheduled": False,
                    "schedule_status": "NORMAL",
                    "status": "NONE",
                    "approval_status": "NONE",
                    "location_type": None,
                    "schedule_request_id": None,
                    "decision_reason": None,
                    "actual_check_in": check_in.timestamp.strftime('%H:%M') if check_in else None,
                    "actual_check_out": check_out.timestamp.strftime('%H:%M') if check_out else None,
                })
            curr += timedelta(days=1)
    else:
        # パディングなし（通常はstart, endが指定される想定）
        for s in schedules:
            d = s.date
            check_in = att_in_map.get(d)
            check_out = att_out_map.get(d)
            
            result.append({
                "id": s.id,
                "date": s.date.strftime('%Y-%m-%d'),
                "start_time": s.start_time,
                "end_time": s.end_time,
                "is_scheduled": s.is_scheduled,
                "schedule_status": get_legacy_schedule_status(s),
                "status": s.approval_status,
                "approval_status": s.approval_status,
                "location_type": s.location_type,
                "schedule_request_id": s.schedule_request_id,
                "decision_reason": s.decision_reason,
                "actual_check_in": check_in.timestamp.strftime('%H:%M') if check_in else None,
                "actual_check_out": check_out.timestamp.strftime('%H:%M') if check_out else None,
            })
            
    return jsonify({"items": result}), 200

@users_bp.route('/<int:user_id>/daily-schedules/<date_str>', methods=['PUT'])
@jwt_required()
def update_daily_schedule(user_id, date_str):
    identity = get_jwt_identity()
    if not identity.startswith('staff:'):
        return jsonify({
            "success": False,
            "error": {
                "code": "FORBIDDEN",
                "message": "この操作には職員権限が必要です。"
            }
        }), 403

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"success": False, "error": {"code": "NOT_FOUND", "message": "利用者が見つかりません。"}}), 404
        
    from backend.app.models.core.audit_log import AuditActionLog
    import json
    
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"success": False, "error": {"code": "VALIDATION_ERROR", "message": "日付フォーマットが不正です。"}}), 400
        
    data = request.get_json() or {}
    
    schedule = UserDailySchedule.query.filter_by(user_id=user_id, date=target_date).first()
    
    before_state = None
    if schedule:
        before_state = {
            "is_scheduled": schedule.is_scheduled,
            "start_time": schedule.start_time,
            "end_time": schedule.end_time,
            "location_type": schedule.location_type,
            "decision_reason": schedule.decision_reason
        }
    else:
        schedule = UserDailySchedule(user_id=user_id, date=target_date, schedule_kind='NORMAL', approval_status='APPROVED')
        db.session.add(schedule)
        
    is_scheduled = data.get('is_scheduled')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    location_type = data.get('location_type')
    decision_reason = data.get('decision_reason')
    
    if is_scheduled is not None:
        if is_scheduled:
            schedule.approval_status = 'APPROVED'
        else:
            schedule.start_time = None
            schedule.end_time = None
            
    if start_time is not None:
        schedule.start_time = start_time
    if end_time is not None:
        schedule.end_time = end_time
    if location_type is not None:
        schedule.location_type = location_type
    if decision_reason is not None:
        schedule.decision_reason = decision_reason
        
    if is_scheduled and (not schedule.start_time or not schedule.end_time):
        return jsonify({"success": False, "error": {"code": "VALIDATION_ERROR", "message": "通所予定の場合、開始時間と終了時間は必須です。"}}), 400
        
    if schedule.is_scheduled and schedule.start_time and schedule.end_time:
        sh, sm = map(int, schedule.start_time.split(':'))
        eh, em = map(int, schedule.end_time.split(':'))
        if (eh * 60 + em) <= (sh * 60 + sm):
            return jsonify({"success": False, "error": {"code": "VALIDATION_ERROR", "message": "終了時間は開始時間より後の時間に設定してください。"}}), 400
            
    # キャンセル・臨時追加・大幅変更には decision_reason を残す
    if not schedule.is_scheduled and not schedule.decision_reason:
        return jsonify({"success": False, "error": {"code": "VALIDATION_ERROR", "message": "通所なしに変更する場合は理由（decision_reason）を入力してください。"}}), 400
        
    try:
        db.session.flush()
        
        after_state = {
            "is_scheduled": schedule.is_scheduled,
            "start_time": schedule.start_time,
            "end_time": schedule.end_time,
            "location_type": schedule.location_type,
            "decision_reason": schedule.decision_reason
        }
        
        supporter_id_int = int(identity.split(':')[1])
        audit_log = AuditActionLog(
            actor_supporter_id=supporter_id_int,
            action='UPDATE_DAILY_SCHEDULE',
            entity_type='user_daily_schedule',
            entity_id=schedule.id,
            before_value=json.dumps(before_state, ensure_ascii=False) if before_state else None,
            after_value=json.dumps(after_state, ensure_ascii=False),
            reason=decision_reason or "日別予定の直接編集"
        )
        db.session.add(audit_log)
        
        db.session.commit()
        return jsonify({
            "success": True,
            "item": {
                "id": schedule.id,
                "date": schedule.date.strftime('%Y-%m-%d'),
                "start_time": schedule.start_time,
                "end_time": schedule.end_time,
                "is_scheduled": schedule.is_scheduled,
                "location_type": schedule.location_type,
                "decision_reason": schedule.decision_reason
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": {"code": "SERVER_ERROR", "message": str(e)}}), 500

@users_bp.route('/schedule-requests/<int:request_id>/decide', methods=['POST'])
@jwt_required()
def decide_schedule_request(request_id):
    identity = get_jwt_identity()
    if not identity.startswith('staff:'):
        return jsonify({
            "success": False,
            "error": {
                "code": "FORBIDDEN",
                "message": "この操作には職員権限が必要です。"
            }
        }), 403
        
    supporter_id = int(identity.split(':')[1])
    
    data = request.get_json() or {}
    status = data.get('status')
    decision_reason = data.get('decision_reason')
    
    if not status or not decision_reason:
        return jsonify({
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "ステータスと判断理由は必須です。"
            }
        }), 400
        
    service = UserScheduleService()
    try:
        req = service.decide_schedule_request(
            request_id=request_id,
            supporter_id=supporter_id,
            status=status,
            decision_reason=decision_reason
        )
        return jsonify({
            "success": True,
            "item": {
                "id": req.id,
                "request_status": req.request_status,
                "decision_reason": req.decision_reason
            }
        }), 200
    except ValidationError as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(e)
            }
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": str(e)
            }
        }), 500

@users_bp.route('/<int:user_id>/schedule-templates/apply', methods=['POST'])
@jwt_required()
def apply_schedule_template(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({
            "success": False,
            "error": {
                "code": "NOT_FOUND",
                "message": "利用者が見つかりません。"
            }
        }), 404
        
    data = request.get_json() or {}
    year = data.get('year')
    month = data.get('month')
    
    if not year or not month:
        return jsonify({
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "年と月は必須です。"
            }
        }), 400
        
    try:
        target_month_date = date(int(year), int(month), 1)
        service = UserScheduleService()
        created_count = service.generate_daily_schedules_for_month(user_id, target_month_date, force_overwrite=True)
        return jsonify({
            "success": True,
            "message": f"{year}年{month}月の基本曜日予定を一括適用しました（更新件数: {created_count}件）。"
        }), 200
    except ValidationError as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(e)
            }
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "SERVER_ERROR",
                "message": str(e)
            }
        }), 500

@users_bp.route('/<int:user_id>/monthly-usage-summary', methods=['GET'])
@jwt_required()
def get_monthly_usage_summary(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({
            "success": False,
            "error": {
                "code": "NOT_FOUND",
                "message": "利用者が見つかりません。"
            }
        }), 404
        
    year_str = request.args.get('year')
    month_str = request.args.get('month')
    
    if not year_str or not month_str:
        return jsonify({
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "year と month は必須です。"
            }
        }), 400
        
    try:
        year = int(year_str)
        month = int(month_str)
    except ValueError:
        return jsonify({
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "日付パラメータが不正です。"
            }
        }), 400
        
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)

    from backend.app.models.core.service_certificate import GrantedService, ServiceCertificate
    
    granted_services = GrantedService.query.join(
        ServiceCertificate, GrantedService.certificate_id == ServiceCertificate.id
    ).filter(
        ServiceCertificate.user_id == user_id,
        ServiceCertificate.status == 'ACTIVE',
        GrantedService.granted_start_date <= end_date,
        GrantedService.granted_end_date >= start_date
    ).all()
    
    from backend.app.models.support.attendance_workflow import AttendanceRecord
    from backend.app.models import UserDailyLog
    from sqlalchemy import func
    
    attendances = AttendanceRecord.query.filter_by(
        user_id=user_id,
        record_type='CHECK_IN'
    ).filter(
        func.date(AttendanceRecord.timestamp) >= start_date,
        func.date(AttendanceRecord.timestamp) <= end_date
    ).all()
    
    attendance_dates = {att.timestamp.date() for att in attendances}
    
    daily_logs = UserDailyLog.query.filter_by(user_id=user_id).filter(
        UserDailyLog.log_date >= start_date,
        UserDailyLog.log_date <= end_date,
        UserDailyLog.auto_created == False
    ).filter(
        (UserDailyLog.morning_completed == True) | (UserDailyLog.evening_completed == True)
    ).all()
    
    log_dates = {log.log_date for log in daily_logs}
    
    actual_dates = attendance_dates.union(log_dates)
    
    daily_schedules = UserDailySchedule.query.filter_by(
        user_id=user_id
    ).filter(
        UserDailySchedule.date >= start_date,
        UserDailySchedule.date <= end_date
    ).all()
    
    scheduled_dates = {
        s.date for s in daily_schedules 
        if s.is_scheduled and s.approval_status == 'APPROVED'
    }
    
    total_usage_dates = actual_dates.union(scheduled_dates)
    
    summaries = []
    
    if not granted_services:
        summaries.append({
            "granted_service_id": None,
            "service_name": "未設定のサービス",
            "service_code": "UNKNOWN",
            "max_service_days": 23,
            "scheduled_days_count": len(scheduled_dates),
            "actual_days_count": len(actual_dates),
            "total_days_count": len(total_usage_dates),
            "is_exceeded": len(total_usage_dates) > 23,
            "exceeded_days": max(0, len(total_usage_dates) - 23)
        })
    else:
        for gs in granted_services:
            if gs.max_service_days_type == 'DYNAMIC_MONTH_MINUS_8':
                max_days = end_date.day - 8
            else:
                max_days = gs.max_service_days if gs.max_service_days is not None else 23
            
            gs_start = max(start_date, gs.granted_start_date)
            gs_end = min(end_date, gs.granted_end_date)
            
            gs_scheduled = {d for d in scheduled_dates if gs_start <= d <= gs_end}
            gs_actual = {d for d in actual_dates if gs_start <= d <= gs_end}
            gs_total = {d for d in total_usage_dates if gs_start <= d <= gs_end}
            
            summaries.append({
                "granted_service_id": gs.id,
                "service_name": gs.service_type.name if gs.service_type else "不明なサービス",
                "service_code": gs.service_type.service_code if gs.service_type else "UNKNOWN",
                "max_service_days": max_days,
                "scheduled_days_count": len(gs_scheduled),
                "actual_days_count": len(gs_actual),
                "total_days_count": len(gs_total),
                "is_exceeded": len(gs_total) > max_days,
                "exceeded_days": max(0, len(gs_total) - max_days)
            })
            
    return jsonify({
        "year": year,
        "month": month,
        "items": summaries
    }), 200

