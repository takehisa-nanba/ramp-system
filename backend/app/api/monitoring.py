from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app import db
from backend.app.services.monitoring_service import MonitoringService
from backend.app.services.core_service import parse_jwt_identity
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
monitoring_bp = Blueprint('monitoring', __name__, url_prefix='/api/monitoring-reports')
monitoring_service = MonitoringService()

@monitoring_bp.route('', methods=['POST'])
@jwt_required()
def create_monitoring():
    _, supporter_id = parse_jwt_identity(get_jwt_identity())
    data = request.get_json()
    
    plan_id = data.get('support_plan_id')
    report_date_str = data.get('report_date')
    summary = data.get('monitoring_summary')
    
    if not plan_id or not report_date_str or not summary:
        return jsonify({"msg": "Missing required fields"}), 400
        
    try:
        report_date = datetime.fromisoformat(report_date_str).date()
        report = monitoring_service.create_monitoring_report(
            plan_id=plan_id,
            supporter_id=supporter_id,
            report_date=report_date,
            summary=summary,
            goal_notes=data.get('target_goal_progress_notes'),
            context=data.get('contextual_analysis')
        )
        db.session.commit()
        return jsonify({"msg": "Monitoring report created", "id": report.id}), 201
    except Exception as e:
        db.session.rollback()
        logger.exception(e)
        return jsonify({"msg": "Failed to create monitoring report"}), 500

@monitoring_bp.route('/<int:report_id>/complete', methods=['POST'])
@jwt_required()
def complete_monitoring(report_id):
    data = request.get_json() or {}
    try:
        monitoring_service.complete_monitoring(report_id, data.get('document_url'))
        db.session.commit()
        return jsonify({"msg": "Monitoring completed"}), 200
    except Exception as e:
        db.session.rollback()
        logger.exception(e)
        return jsonify({"msg": "Failed to complete monitoring"}), 500
