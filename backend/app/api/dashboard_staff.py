# backend/app/api/dashboard_staff.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app.domain.attendance.exceptions import AttendanceDomainError
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
        
    import pytz
    tz = pytz.timezone('Asia/Tokyo')
    now = datetime.now(tz)
    today = now.date()
    
    # 本日のシフト
    shifts = StaffDailyShift.query.filter_by(target_date=today).all()
    # 本日の全打刻
    timecards = SupporterTimecard.query.filter_by(work_date=today).all()
    
    # 進行中の打刻（日付をまたいでいる可能性を考慮）
    ongoing_timecards = SupporterTimecard.query.filter(
        SupporterTimecard.check_in != None,
        SupporterTimecard.check_out == None
    ).all()
    ongoing_map = {tc.supporter_id: tc for tc in ongoing_timecards}
    
    # 本日の打刻をsupporter_idでグループ化し、完了済みのみに絞る
    completed_map = {}
    for tc in timecards:
        if tc.check_out is not None:
            if tc.supporter_id not in completed_map:
                completed_map[tc.supporter_id] = []
            completed_map[tc.supporter_id].append(tc)
    
    staff_data = []
    
    supporters = Supporter.query.filter_by(is_active=True).all()
    for supporter in supporters:
        shift = next((s for s in shifts if s.supporter_id == supporter.id), None)
        
        ongoing = ongoing_map.get(supporter.id)
        completed_list = completed_map.get(supporter.id, [])
        # sequence_noでソート
        completed_list.sort(key=lambda x: x.sequence_no or 0)
        
        rep_timecard = ongoing if ongoing else (completed_list[-1] if completed_list else None)
        
        total_worked_seconds = 0
        for tc in completed_list:
            if tc.check_in and tc.check_out:
                duration = (tc.check_out - tc.check_in).total_seconds()
                break_sec = (tc.total_break_minutes or 0) * 60
                total_worked_seconds += (duration - break_sec)
        
        status = "NOT_SCHEDULED"
        if ongoing:
            status = "WORKING"
        elif completed_list:
            status = "FINISHED"
        elif shift:
            status = "SCHEDULED"
            
        staff_data.append({
            "supporter_id": supporter.id,
            "name": f"{supporter.last_name} {supporter.first_name}",
            "status": status,
            "shift": {
                "start": shift.planned_start_time.isoformat() + "+09:00" if shift and shift.planned_start_time else None,
                "end": shift.planned_end_time.isoformat() + "+09:00" if shift and shift.planned_end_time else None
            } if shift else None,
            "timecard": {
                "check_in": rep_timecard.check_in.isoformat() + "+09:00" if rep_timecard and rep_timecard.check_in else None,
                "check_out": rep_timecard.check_out.isoformat() + "+09:00" if rep_timecard and rep_timecard.check_out else None,
                "total_worked_seconds": total_worked_seconds
            } if rep_timecard or completed_list else None
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
    data = request.get_json() or {}
    
    office_id = data.get('office_id')
    if not office_id:
        from backend.app.models import Supporter, SupporterJobAssignment
        from backend.app.models.core.office import OfficeServiceConfiguration
        supporter = Supporter.query.get(supporter_id)
        
        valid_offices = set()
        if supporter.office_id:
            valid_offices.add(supporter.office_id)
            
        assignments = SupporterJobAssignment.query.filter_by(supporter_id=supporter_id).all()
        for ja in assignments:
            if ja.office_service_configuration_id:
                osc = OfficeServiceConfiguration.query.get(ja.office_service_configuration_id)
                if osc:
                    valid_offices.add(osc.office_id)
                    
        if len(valid_offices) == 1:
            office_id = list(valid_offices)[0]
        else:
            return jsonify({"msg": "office_id is required or ambiguous"}), 400

    location_type = data.get('location_type', 'OFFICE')
    location_detail = data.get('location_detail', '')
    
    from backend.app.services.attendance_service import AttendanceService
    svc = AttendanceService(db.session)
    
    try:
        timecard = svc.clock_in(supporter_id, office_id, location_type, location_detail)
        db.session.commit()
        return jsonify({
            "msg": "Clocked in successfully",
            "timecard_id": timecard.id,
            "sequence_no": timecard.sequence_no,
            "check_in": timecard.check_in.isoformat() + "+09:00"
        }), 201
    except PermissionError as e:
        db.session.rollback()
        return jsonify({"msg": str(e)}), 403
    except AttendanceDomainError as e:
        db.session.rollback()
        return jsonify({"msg": str(e)}), e.status_code
    except Exception as e:
        db.session.rollback()
        # Log unexpected error here if needed
        return jsonify({"msg": "Internal Server Error"}), 500

@dashboard_staff_bp.route('/clock-out', methods=['POST'])
@jwt_required()
def clock_out():
    identity = get_jwt_identity()
    if not identity.startswith('staff:'):
        return jsonify({"msg": "Unauthorized"}), 403
    
    supporter_id = int(identity.split(':')[1])
    data = request.get_json() or {}
    break_minutes = data.get('break_minutes', 0)
    
    from backend.app.services.attendance_service import AttendanceService
    svc = AttendanceService(db.session)
    
    try:
        timecard = svc.clock_out(supporter_id, timecard_id=None, break_minutes=break_minutes)
        db.session.commit()
        return jsonify({
            "msg": "Clocked out successfully",
            "timecard_id": timecard.id,
            "check_out": timecard.check_out.isoformat() + "+09:00"
        }), 200

    except AttendanceDomainError as e:
        db.session.rollback()
        return jsonify({"msg": str(e)}), e.status_code
    except Exception as e:
        db.session.rollback()
        # Log unexpected error here if needed
        return jsonify({"msg": "Internal Server Error"}), 500

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

