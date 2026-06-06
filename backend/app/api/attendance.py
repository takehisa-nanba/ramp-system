from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app import db
from backend.app.models import Supporter, SupporterTimecard, OfficeServiceConfiguration
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")

attendance_bp = Blueprint('attendance', __name__, url_prefix='/api/attendance')

def get_current_supporter_id():
    identity = get_jwt_identity()
    if isinstance(identity, str) and identity.startswith('staff:'):
        return int(identity.split(':')[1])
    try:
        return int(identity)
    except (ValueError, TypeError):
        return None

@attendance_bp.route('/status', methods=['GET'])
@jwt_required()
def get_status():
    supporter_id = get_current_supporter_id()
    if not supporter_id:
        return jsonify({"msg": "Unauthorized"}), 403

    today = datetime.now(JST).date()
    
    timecard = SupporterTimecard.query.filter_by(
        supporter_id=supporter_id,
        work_date=today
    ).first()
    
    if not timecard:
        return jsonify({
            "status": "IDLE",
            "check_in": None,
            "check_out": None
        }), 200
        
    status = "WORKING" if timecard.check_in and not timecard.check_out else "IDLE"
    if timecard.check_in and timecard.check_out:
        status = "COMPLETED"
        
    return jsonify({
        "status": status,
        "check_in": timecard.check_in.isoformat() if timecard.check_in else None,
        "check_out": timecard.check_out.isoformat() if timecard.check_out else None
    }), 200

@attendance_bp.route('/clock-in', methods=['POST'])
@jwt_required()
def clock_in():
    supporter_id = get_current_supporter_id()
    if not supporter_id:
        return jsonify({"msg": "Unauthorized"}), 403

    data = request.get_json() or {}
    location = data.get('location')
    
    supporter = db.session.get(Supporter, supporter_id)
    if not supporter:
        return jsonify({"msg": "Supporter not found"}), 404
        
    today = datetime.now(JST).date()
    
    # すでに本日の打刻があるか確認
    existing = SupporterTimecard.query.filter_by(supporter_id=supporter_id, work_date=today).first()
    if existing:
        return jsonify({"msg": "Already clocked in today"}), 400
        
    # 所属事業所のサービス設定を一つ取得（簡易化）
    service_config = OfficeServiceConfiguration.query.filter_by(office_id=supporter.office_id).first()
    if not service_config:
        return jsonify({"msg": "Office service configuration not found"}), 400
        
    new_card = SupporterTimecard(
        supporter_id=supporter_id,
        office_service_configuration_id=service_config.id,
        work_date=today,
        check_in=datetime.now(JST),
        check_in_location=location
    )
    
    db.session.add(new_card)
    db.session.commit()
    
    return jsonify({"msg": "Clocked in successfully", "time": new_card.check_in.isoformat()}), 201

@attendance_bp.route('/clock-out', methods=['POST'])
@jwt_required()
def clock_out():
    supporter_id = get_current_supporter_id()
    if not supporter_id:
        return jsonify({"msg": "Unauthorized"}), 403

    data = request.get_json() or {}
    location = data.get('location')
    
    today = datetime.now(JST).date()
    
    timecard = SupporterTimecard.query.filter_by(supporter_id=supporter_id, work_date=today).first()
    if not timecard or not timecard.check_in:
        return jsonify({"msg": "No active clock-in found for today"}), 400
        
    if timecard.check_out:
        return jsonify({"msg": "Already clocked out today"}), 400
        
    timecard.check_out = datetime.now(JST)
    timecard.check_out_location = location
    
    db.session.commit()
    
    return jsonify({"msg": "Clocked out successfully", "time": timecard.check_out.isoformat()}), 200
