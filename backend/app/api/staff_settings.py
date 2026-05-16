from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app import db
from backend.app.models import Supporter, UserDailyLogSetting

staff_settings_bp = Blueprint('staff_settings', __name__, url_prefix='/api/staff/settings')

def get_current_staff():
    identity = get_jwt_identity()
    if isinstance(identity, str) and identity.startswith('staff:'):
        staff_id = int(identity.split(':')[1])
        return Supporter.query.get(staff_id)
    return None

@staff_settings_bp.route('/daily-log', methods=['GET'])
@jwt_required()
def get_daily_log_settings():
    staff = get_current_staff()
    if not staff:
        return jsonify({"msg": "Forbidden"}), 403
        
    setting = UserDailyLogSetting.query.filter_by(office_id=staff.office_id).first()
    if not setting:
        # デフォルト設定
        return jsonify({
            "morning_fields": [
                {"id": "mood", "label": "今日の気分", "type": "score", "required": True}
            ],
            "evening_fields": [
                {"id": "review", "label": "今日頑張ったことや、明日の目標", "type": "text", "required": True}
            ]
        }), 200
        
    return jsonify(setting.config), 200

@staff_settings_bp.route('/daily-log', methods=['PUT'])
@jwt_required()
def update_daily_log_settings():
    staff = get_current_staff()
    if not staff:
        return jsonify({"msg": "Forbidden"}), 403
        
    data = request.get_json()
    if not data:
        return jsonify({"msg": "Invalid data"}), 400
        
    setting = UserDailyLogSetting.query.filter_by(office_id=staff.office_id).first()
    
    if not setting:
        setting = UserDailyLogSetting(office_id=staff.office_id)
        db.session.add(setting)
        
    # config フィールド全体を更新
    setting.config = {
        "morning_fields": data.get('morning_fields', []),
        "evening_fields": data.get('evening_fields', [])
    }
    db.session.commit()

    
    return jsonify({"msg": "Settings updated"}), 200
