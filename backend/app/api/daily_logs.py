from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app import db
from backend.app.models import StaffActivityMaster, UserDailyLog, SupportRecord, StaffActivityAllocationLog, User
from datetime import datetime, date, timedelta, timezone
try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Python < 3.9 fallback (though the user has 3.12)
    from backports.zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")

daily_logs_bp = Blueprint('daily_logs', __name__, url_prefix='/api/daily-logs')

def get_current_supporter_id():
    identity = get_jwt_identity()
    if isinstance(identity, str) and identity.startswith('staff:'):
        return int(identity.split(':')[1])
    try:
        return int(identity)
    except (ValueError, TypeError):
        return None

@daily_logs_bp.route('/tags', methods=['GET'])
@jwt_required()
def get_activity_tags():
    """
    活動タグ一覧（直接支援フラグ付き）を取得する。
    """
    tags = StaffActivityMaster.query.all()
    return jsonify([
        {
            "id": tag.id,
            "name": tag.activity_name,
            "is_direct_support": tag.is_direct_support
        } for tag in tags
    ]), 200

@daily_logs_bp.route('', methods=['POST'])
@jwt_required()
def log_activity():
    """
    活動を記録する。直接支援ならDailyLogActivityへ、間接業務ならStaffActivityAllocationLogへ。
    """
    from backend.app.services.daily_log_service import DailyLogService
    from backend.app.utils.errors import ValidationError

    data = request.get_json()
    supporter_id = get_current_supporter_id()
    if not supporter_id:
        return jsonify({"msg": "Unauthorized"}), 403
    
    tag_id = data.get('tag_id')
    user_id = data.get('user_id')
    start_time_str = data.get('start_time')
    end_time_str = data.get('end_time')
    duration_minutes = data.get('duration_minutes', 0)
    notes = data.get('notes', '')
    log_status = data.get('log_status', 'DRAFT')
    attendance_record_id = data.get('attendance_record_id') # 追加
    
    start_time = datetime.fromisoformat(start_time_str) if start_time_str else datetime.now(JST)
    end_time = datetime.fromisoformat(end_time_str) if end_time_str else datetime.now(JST)
    log_date = start_time.date() # start_time から日付を決定
    
    try:
        service = DailyLogService()
        service.record_daily_log(
            supporter_id=supporter_id,
            tag_id=tag_id,
            log_date=log_date,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration_minutes,
            user_id=user_id,
            notes=notes,
            log_status=log_status,
            attendance_record_id=attendance_record_id # 追加
        )
        db.session.commit()
        return jsonify({"msg": "Activity logged successfully"}), 201
    except ValidationError as e:
        db.session.rollback()
        return jsonify({"msg": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        import logging
        logging.getLogger(__name__).exception(e)
        return jsonify({"msg": "Failed to log activity"}), 500

@daily_logs_bp.route('/today', methods=['GET'])
@jwt_required()
def get_today_timeline():
    """
    本日のタイムライン（活動履歴）を取得する。
    """
    supporter_id = get_current_supporter_id()
    if not supporter_id:
        return jsonify({"msg": "Unauthorized"}), 403

    today = datetime.now(JST).date()
    
    # 直接支援の取得
    # 自分が担当したSupportRecordをすべて取得
    direct_activities = db.session.query(SupportRecord, User.display_name)\
        .join(User, SupportRecord.user_id == User.id)\
        .filter(SupportRecord.log_date == today, SupportRecord.supporter_id == supporter_id)\
        .all()

        
    # 間接業務の取得
    indirect_allocations = StaffActivityAllocationLog.query.filter_by(
        supporter_id=supporter_id,
        activity_date=today
    ).all()
    
    timeline = []
    for act, user_name in direct_activities:
        timeline.append({
            "type": "support",
            "title": act.support_content, # 保存時に [タグ名] を含めるようにしたのでここを使用
            "user": user_name,
            "startTime": act.support_start_time.strftime('%H:%M') if act.support_start_time else "--:--",
            "endTime": act.support_end_time.strftime('%H:%M') if act.support_end_time else "--:--",
            "notes": ""
        })
        
    for alloc in indirect_allocations:
        timeline.append({
            "type": "office",
            "title": alloc.activity_type.activity_name,
            "duration": alloc.allocated_minutes,
            "startTime": "間接", # 間接業務は時間が固定されない設計
            "endTime": ""
        })
        
    # 時間順にソート（簡易的に）
    timeline.sort(key=lambda x: x['startTime'])
    
    return jsonify(timeline), 200
