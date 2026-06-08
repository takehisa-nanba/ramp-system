# backend/app/api/users/user_schedule_api.py
from datetime import date, datetime
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app.extensions import db
from backend.app.models import (
    UserScheduleTemplate, UserDailySchedule, UserScheduleRequest, User
)
from backend.app.services.user_schedule_service import UserScheduleService
from backend.app.utils.errors import ValidationError
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
            "end_time": t.end_time if t else None
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
                end_time=end if is_sch else None
            )
            db.session.add(template)
            
        db.session.commit()
        
        # テンプレート更新後、今月と来月の予定を自動生成/同期する
        service = UserScheduleService()
        today = date.today()
        service.generate_daily_schedules_for_month(user_id, today)
        if today.month == 12:
            next_month = date(today.year + 1, 1, 1)
        else:
            next_month = date(today.year, today.month + 1, 1)
        service.generate_daily_schedules_for_month(user_id, next_month)
        
        return jsonify({
            "success": True,
            "message": "曜日別予定テンプレートを保存し、日別予定を更新しました。"
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
    
    result = []
    for s in schedules:
        result.append({
            "id": s.id,
            "date": s.date.strftime('%Y-%m-%d'),
            "start_time": s.start_time,
            "end_time": s.end_time,
            "is_scheduled": s.is_scheduled,
            "schedule_status": s.schedule_status,
            "schedule_request_id": s.schedule_request_id
        })
    return jsonify({"items": result}), 200

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
