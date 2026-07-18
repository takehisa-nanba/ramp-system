from flask import Blueprint, request, jsonify
from backend.app.extensions import db
from backend.app.models.support.daily_log import SupportRecord
from backend.app.models.core.user import User
from backend.app.models.core.supporter import Supporter
from datetime import datetime

bp = Blueprint('support_records', __name__, url_prefix='/api/records')

@bp.route('', methods=['GET'])
def get_records():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    supporter_id = request.args.get('supporter_id')
    user_id = request.args.get('user_id')

    query = db.session.query(SupportRecord, User, Supporter).join(
        User, SupportRecord.user_id == User.id
    ).join(
        Supporter, SupportRecord.supporter_id == Supporter.id
    )

    if start_date:
        query = query.filter(SupportRecord.log_date >= start_date)
    if end_date:
        query = query.filter(SupportRecord.log_date <= end_date)
    if supporter_id:
        query = query.filter(SupportRecord.supporter_id == supporter_id)
    if user_id:
        query = query.filter(SupportRecord.user_id == user_id)

    # Sort by date desc, then by start time desc
    query = query.order_by(SupportRecord.log_date.desc(), SupportRecord.support_start_time.desc().nullslast())
    
    results = query.all()

    data = []
    for record, user, supporter in results:
        data.append({
            'id': record.id,
            'user_id': record.user_id,
            'user_name': user.display_name,
            'supporter_id': record.supporter_id,
            'supporter_name': f"{supporter.last_name} {supporter.first_name}",
            'log_date': record.log_date.isoformat() if record.log_date else None,
            'support_start_time': record.support_start_time.isoformat() if record.support_start_time else None,
            'support_end_time': record.support_end_time.isoformat() if record.support_end_time else None,
            'support_duration_seconds': record.support_duration_seconds,
            'support_record_type': record.support_record_type,
            'location_type': record.location_type,
            'location_detail': record.location_detail,
            'support_content': record.support_content,
            'decision_reason': record.decision_reason,
            'observation_note': record.observation_note
        })

    return jsonify({'items': data})

@bp.route('', methods=['POST'])
def create_record():
    data = request.json
    if not data:
        return jsonify({'msg': 'No data provided'}), 400

    try:
        new_record = SupportRecord(
            user_id=data.get('user_id'),
            log_date=data.get('log_date'),
            supporter_id=data.get('supporter_id'),
            support_start_time=datetime.fromisoformat(data['support_start_time']) if data.get('support_start_time') else None,
            support_end_time=datetime.fromisoformat(data['support_end_time']) if data.get('support_end_time') else None,
            support_duration_seconds=data.get('support_duration_seconds'),
            support_record_type=data.get('support_record_type', 'DIRECT_SUPPORT'),
            location_type=data.get('location_type'),
            location_detail=data.get('location_detail'),
            support_content=data.get('support_content'),
            observation_note=data.get('observation_note')
        )
        db.session.add(new_record)
        db.session.commit()
        return jsonify({'msg': 'Success', 'id': new_record.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'msg': str(e)}), 500
