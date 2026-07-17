# backend/app/api/dashboard_staff.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app.extensions import db
from backend.app.models import Supporter, StaffActionLog, StaffDailyReport, SupporterTimecard, StaffDailyShift
from datetime import datetime, date

dashboard_staff_bp = Blueprint('dashboard_staff', __name__, url_prefix='/api/dashboard/staff')

@dashboard_staff_bp.route('/status', methods=['GET'])
@jwt_required()
def get_staff_status():
    """
    ダッシュボード用：今日の職員の勤務状況（シフトと実打刻状況）を取得する
    """
    identity = get_jwt_identity()
    if not identity.startswith('staff:'):
        return jsonify({"msg": "Unauthorized"}), 403
        
    today = date.today()
    
    # 本日のシフト
    shifts = StaffDailyShift.query.filter_by(target_date=today).all()
    # 本日の打刻
    timecards = SupporterTimecard.query.filter_by(work_date=today).all()
    
    staff_data = []
    
    supporters = Supporter.query.filter_by(is_active=True).all()
    for supporter in supporters:
        shift = next((s for s in shifts if s.supporter_id == supporter.id), None)
        timecard = next((t for t in timecards if t.supporter_id == supporter.id), None)
        
        status = "NOT_SCHEDULED"
        if timecard and timecard.check_in and not timecard.check_out:
            status = "WORKING"
        elif timecard and timecard.check_out:
            status = "FINISHED"
        elif shift:
            status = "SCHEDULED"
            
        staff_data.append({
            "supporter_id": supporter.id,
            "name": f"{supporter.last_name} {supporter.first_name}",
            "status": status,
            "shift": {
                "start": shift.planned_start_time.isoformat() if shift else None,
                "end": shift.planned_end_time.isoformat() if shift else None
            } if shift else None,
            "timecard": {
                "check_in": timecard.check_in.isoformat() if timecard and timecard.check_in else None,
                "check_out": timecard.check_out.isoformat() if timecard and timecard.check_out else None
            } if timecard else None
        })
        
    return jsonify({
        "current_staff_id": int(identity.split(':')[1]),
        "staff_list": staff_data
    }), 200

@dashboard_staff_bp.route('/action-logs', methods=['POST'])
@jwt_required()
def add_action_log():
    """職員のアクションログ（つぶやき）を追加"""
    identity = get_jwt_identity()
    if not identity.startswith('staff:'):
        return jsonify({"msg": "Unauthorized"}), 403
        
    supporter_id = int(identity.split(':')[1])
    data = request.get_json()
    content = data.get('content')
    
    if not content:
        return jsonify({"msg": "Content is required"}), 400
        
    log = StaffActionLog(
        supporter_id=supporter_id,
        action_content=content,
        action_timestamp=datetime.now()
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({"msg": "Action log added successfully", "id": log.id}), 201

@dashboard_staff_bp.route('/action-logs/today', methods=['GET'])
@jwt_required()
def get_today_action_logs():
    """職員の今日のアクションログ一覧を取得"""
    identity = get_jwt_identity()
    if not identity.startswith('staff:'):
        return jsonify({"msg": "Unauthorized"}), 403
        
    supporter_id = int(identity.split(':')[1])
    today = date.today()
    
    logs = StaffActionLog.query.filter(
        StaffActionLog.supporter_id == supporter_id,
        db.func.date(StaffActionLog.action_timestamp) == today
    ).order_by(StaffActionLog.action_timestamp.desc()).all()
    
    return jsonify([{
        "id": log.id,
        "content": log.action_content,
        "timestamp": log.action_timestamp.isoformat(),
        "is_processed_by_ai": log.is_processed_by_ai
    } for log in logs]), 200

@dashboard_staff_bp.route('/daily-report/generate', methods=['POST'])
@jwt_required()
def generate_daily_report():
    """AIを利用してアクションログから業務日報を下書きする（モック版）"""
    identity = get_jwt_identity()
    if not identity.startswith('staff:'):
        return jsonify({"msg": "Unauthorized"}), 403
        
    supporter_id = int(identity.split(':')[1])
    today = date.today()
    
    # 未処理のログを取得
    unprocessed_logs = StaffActionLog.query.filter(
        StaffActionLog.supporter_id == supporter_id,
        db.func.date(StaffActionLog.action_timestamp) == today,
        StaffActionLog.is_processed_by_ai == False
    ).all()
    
    if not unprocessed_logs:
        return jsonify({"msg": "No unprocessed logs available for today."}), 400
        
    # TODO: 実際のGemini APIを呼び出す。今回はモックテキストを生成
    aggregated_text = "【本日の業務ハイライト】\n"
    for log in unprocessed_logs:
        aggregated_text += f"- {log.action_timestamp.strftime('%H:%M')} : {log.action_content}\n"
        log.is_processed_by_ai = True
        
    # 日報モデルの作成または更新
    report = StaffDailyReport.query.filter_by(supporter_id=supporter_id, target_date=today).first()
    if report:
        report.report_content += "\n\n" + aggregated_text
        report.is_ai_draft = True
        report.is_submitted = False
    else:
        report = StaffDailyReport(
            supporter_id=supporter_id,
            target_date=today,
            report_content=aggregated_text,
            is_ai_draft=True,
            is_submitted=False
        )
        db.session.add(report)
        
    db.session.commit()
    
    return jsonify({
        "msg": "Daily report draft generated",
        "report_id": report.id,
        "content": report.report_content
    }), 200

@dashboard_staff_bp.route('/clock-in', methods=['POST'])
@jwt_required()
def clock_in():
    identity = get_jwt_identity()
    if not identity.startswith('staff:'):
        return jsonify({"msg": "Unauthorized"}), 403
    
    supporter_id = int(identity.split(':')[1])
    today = date.today()
    
    timecard = SupporterTimecard.query.filter_by(supporter_id=supporter_id, work_date=today).first()
    if not timecard:
        from backend.app.models import OfficeServiceConfiguration, Supporter
        supporter = Supporter.query.get(supporter_id)
        osc = OfficeServiceConfiguration.query.filter_by(office_id=supporter.office_id).first()
        if not osc:
            osc = OfficeServiceConfiguration.query.first() # fallback
            
        timecard = SupporterTimecard(
            supporter_id=supporter_id, 
            work_date=today,
            office_service_configuration_id=osc.id if osc else 1
        )
        db.session.add(timecard)
    
    if timecard.check_in:
        return jsonify({"msg": "Already clocked in"}), 400
        
    timecard.check_in = datetime.now()
    db.session.commit()
    return jsonify({"msg": "Clocked in successfully"}), 200

@dashboard_staff_bp.route('/clock-out', methods=['POST'])
@jwt_required()
def clock_out():
    identity = get_jwt_identity()
    if not identity.startswith('staff:'):
        return jsonify({"msg": "Unauthorized"}), 403
    
    supporter_id = int(identity.split(':')[1])
    today = date.today()
    
    data = request.get_json() or {}
    break_minutes = data.get('break_minutes', 0)
    
    timecard = SupporterTimecard.query.filter_by(supporter_id=supporter_id, work_date=today).first()
    if not timecard or not timecard.check_in:
        return jsonify({"msg": "Not clocked in"}), 400
        
    if timecard.check_out:
        return jsonify({"msg": "Already clocked out"}), 400
        
    timecard.check_out = datetime.now()
    try:
        timecard.total_break_minutes = int(break_minutes)
    except ValueError:
        timecard.total_break_minutes = 0
        
    db.session.commit()
    return jsonify({"msg": "Clocked out successfully"}), 200

@dashboard_staff_bp.route('/seed-shifts', methods=['POST'])
@jwt_required()
def seed_shifts():
    identity = get_jwt_identity()
    if not identity.startswith('staff:'):
        return jsonify({"msg": "Unauthorized"}), 403
        
    today = date.today()
    
    # 既存のシフトを削除
    StaffDailyShift.query.filter_by(target_date=today).delete()
    
    supporters = Supporter.query.filter_by(is_active=True).all()
    created = 0
    for s in supporters:
        shift = StaffDailyShift(
            supporter_id=s.id,
            target_date=today,
            planned_start_time=datetime(today.year, today.month, today.day, 9, 0),
            planned_end_time=datetime(today.year, today.month, today.day, 18, 0)
        )
        db.session.add(shift)
        created += 1
        
    db.session.commit()
    return jsonify({"msg": f"Seeded {created} shifts for today"}), 201

