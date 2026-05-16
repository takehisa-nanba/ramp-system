from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app import db
from backend.app.models import StaffActivityMaster, DailyLog, DailyLogActivity, StaffActivityAllocationLog, User
from datetime import datetime, date, timedelta, timezone
try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Python < 3.9 fallback (though the user has 3.12)
    from backports.zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")

activities_bp = Blueprint('activities', __name__, url_prefix='/api/activities')

@activities_bp.route('/tags', methods=['GET'])
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

@activities_bp.route('/log', methods=['POST'])
@jwt_required()
def log_activity():
    """
    活動を記録する。直接支援ならDailyLogActivityへ、間接業務ならStaffActivityAllocationLogへ。
    """
    data = request.get_json()
    supporter_id = get_jwt_identity()
    
    tag_id = data.get('tag_id')
    user_id = data.get('user_id')
    start_time_str = data.get('start_time') # ISO format
    end_time_str = data.get('end_time')     # ISO format
    duration_minutes = data.get('duration_minutes', 0)
    
    tag = db.session.get(StaffActivityMaster, tag_id)
    if not tag:
        return jsonify({"msg": "Invalid activity tag"}), 400
        
    log_date = datetime.now(JST).date() # 日本時間での当日とする
    
    if tag.is_direct_support:
        if not user_id:
            return jsonify({"msg": "User selection is required for direct support"}), 400
            
        # 該当利用者の当日のDailyLogを探す（なければ作成）
        daily_log = DailyLog.query.filter_by(user_id=user_id, log_date=log_date).first()
        if not daily_log:
            daily_log = DailyLog(
                user_id=user_id,
                log_date=log_date,
                location_type='ON_SITE', # デフォルト値
                support_content_notes='活動トラッカーによる自動生成', # 必須項目
                log_status='DRAFT'
            )
            db.session.add(daily_log)
            db.session.flush() # ID確定
            
        # 活動を保存
        # Note: DailyLogActivity requires support_goal_id. 
        # 該当利用者の最新の目標を自動取得する（簡易化のため）
        from backend.app.models import IndividualSupportGoal, ShortTermGoal, LongTermGoal, SupportPlan
        goal = db.session.query(IndividualSupportGoal)\
            .join(ShortTermGoal)\
            .join(LongTermGoal)\
            .join(SupportPlan)\
            .filter(SupportPlan.user_id == user_id)\
            .first()
            
        if not goal:
            return jsonify({"msg": "No active support goal found for this user. Cannot log activity."}), 400

        activity = DailyLogActivity(
            daily_log_id=daily_log.id,
            supporter_id=supporter_id, 
            support_goal_id=goal.id, 
            support_content=f"[{tag.activity_name}] {data.get('notes', '')}",
            support_start_time=datetime.fromisoformat(start_time_str) if start_time_str else datetime.now(JST),
            support_end_time=datetime.fromisoformat(end_time_str) if end_time_str else datetime.now(JST)
        )

        db.session.add(activity)

    else:
        # 間接業務として保存
        # 既存の同一タグのログがあれば加算、なければ新規作成
        allocation = StaffActivityAllocationLog.query.filter_by(
            supporter_id=supporter_id,
            activity_date=log_date,
            staff_activity_master_id=tag_id
        ).first()
        
        if allocation:
            allocation.allocated_minutes += duration_minutes
        else:
            allocation = StaffActivityAllocationLog(
                supporter_id=supporter_id,
                activity_date=log_date,
                staff_activity_master_id=tag_id,
                allocated_minutes=duration_minutes
            )
            db.session.add(allocation)
            
    db.session.commit()
    return jsonify({"msg": "Activity logged successfully"}), 201

@activities_bp.route('/today', methods=['GET'])
@jwt_required()
def get_today_timeline():
    """
    本日のタイムライン（活動履歴）を取得する。
    """
    supporter_id = get_jwt_identity()
    today = datetime.now(JST).date()
    
    # 直接支援の取得
    # 自分が担当したActivityをすべて取得
    direct_activities = db.session.query(DailyLogActivity, User.display_name)\
        .join(DailyLog, DailyLogActivity.daily_log_id == DailyLog.id)\
        .join(User, DailyLog.user_id == User.id)\
        .filter(DailyLog.log_date == today, DailyLogActivity.supporter_id == supporter_id)\
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
