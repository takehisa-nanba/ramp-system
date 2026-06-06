from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app import db
from backend.app.services.case_conference_service import CaseConferenceService
from backend.app.services.core_service import parse_jwt_identity
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
case_conferences_bp = Blueprint('case_conferences', __name__, url_prefix='/api/case-conferences')
case_conference_service = CaseConferenceService()

@case_conferences_bp.route('', methods=['POST'])
@jwt_required()
def create_case_conference():
    _, supporter_id = parse_jwt_identity(get_jwt_identity())
    data = request.get_json()
    
    user_id = data.get('user_id')
    conference_type = data.get('conference_type', 'AD_HOC')
    concern_summary = data.get('concern_summary')
    agreed_action = data.get('agreed_action')
    participant_ids = data.get('participant_ids', [])
    support_plan_id = data.get('support_plan_id')
    
    # 監査用追加パラメータ
    user_participated = bool(data.get('user_participated', True))
    reason_for_user_absence = data.get('reason_for_user_absence')
    is_sabikan_digital_declaration = bool(data.get('is_sabikan_digital_declaration', False))
    absence_monitoring_summary = data.get('absence_monitoring_summary')

    if conference_type == 'PERSON_CENTERED_MEETING_EXCEPTION':
        user_participated = False

    if not user_id or not concern_summary or not agreed_action:
        return jsonify({"msg": "Missing required fields (user_id, concern_summary, agreed_action)"}), 400
        
    try:
        conf_datetime_str = data.get('conference_datetime')
        conf_datetime = datetime.fromisoformat(conf_datetime_str) if conf_datetime_str else datetime.now()
        
        # 期限内実施困難理由 (PERSON_CENTERED_MEETING_EXCEPTION) の場合、AbsenceResponseLog を正式作成
        if conference_type == 'PERSON_CENTERED_MEETING_EXCEPTION':
            if not reason_for_user_absence or not absence_monitoring_summary:
                return jsonify({"msg": "本人不在時の理由および状況モニタリング概要は必須です。"}), 400
            if len(absence_monitoring_summary.strip()) < 10:
                return jsonify({"msg": "状況モニタリング概要は10文字以上で入力してください。"}), 400
            if not is_sabikan_digital_declaration:
                return jsonify({"msg": "サービス管理責任者による宣誓同意が必要です。"}), 400
                
            from backend.app.models import AbsenceResponseLog
            from datetime import date
            
            absence_date = conf_datetime.date() if conf_datetime else date.today()
            
            absence_log = AbsenceResponseLog(
                user_id=user_id,
                absence_date=absence_date,
                response_supporter_id=supporter_id,
                response_method="FAMILY_CONTACT",
                response_summary=absence_monitoring_summary.strip(),
                linked_plan_id=support_plan_id
            )
            db.session.add(absence_log)
            db.session.flush()

        conference = case_conference_service.record_case_conference(
            initiator_id=supporter_id,
            user_id=user_id,
            conference_type=conference_type,
            concern_summary=concern_summary,
            agreed_action=agreed_action,
            participant_ids=participant_ids,
            conference_datetime=conf_datetime,
            triggering_log_reference=data.get('triggering_log_reference'),
            plan_direction_update=data.get('plan_direction_update'),
            external_collaboration_required=data.get('external_collaboration_required', False),
            issue_category_id=data.get('issue_category_id')
        )
        
        # 監査用追加カラムの保存
        conference.support_plan_id = support_plan_id
        conference.user_participated = user_participated
        conference.reason_for_user_absence = reason_for_user_absence
        conference.is_sabikan_digital_declaration = is_sabikan_digital_declaration
        conference.absence_monitoring_summary = absence_monitoring_summary
        
        db.session.commit()
        return jsonify({"msg": "Case conference recorded", "id": conference.id}), 201
    except Exception as e:
        db.session.rollback()
        logger.exception(e)
        return jsonify({"msg": "Failed to record case conference"}), 500


@case_conferences_bp.route('/supporters', methods=['GET'])
@jwt_required()
def list_active_supporters():
    """
    ログイン中のサポーターと同じ事業所の有効なサポーター一覧を取得する（一般職員も叩ける簡易版）。
    """
    from backend.app.models import Supporter
    _, supporter_id = parse_jwt_identity(get_jwt_identity())
    current = db.session.get(Supporter, supporter_id)
    if not current:
        return jsonify({"msg": "Unauthorized"}), 401
    
    supporters = Supporter.query.filter_by(office_id=current.office_id, is_active=True).all()
    return jsonify([{
        "id": s.id,
        "name": f"{s.last_name} {s.first_name}"
    } for s in supporters]), 200
