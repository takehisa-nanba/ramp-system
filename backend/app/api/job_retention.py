# backend/app/api/job_retention.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
import datetime
from backend.app.services.job_retention_service import JobRetentionService
from backend.app.utils.tenant import extract_staff_id

job_retention_bp = Blueprint('job_retention', __name__, url_prefix='/api/job-retention')

def _parse_date(date_str):
    if not date_str:
        return None
    if isinstance(date_str, datetime.date):
        return date_str
    return datetime.datetime.strptime(date_str, '%Y-%m-%d').date()

# ====================================================================
# 契約管理
# ====================================================================
@job_retention_bp.route('/contracts', methods=['GET'])
@jwt_required()
def list_contracts():
    """定着支援契約の一覧取得"""
    claims = get_jwt()
    status = request.args.get('status')
    contracts = JobRetentionService.list_contracts(status=status)
    
    result = []
    for c in contracts:
        latest_ep = c.episodes[-1] if c.episodes else None
        result.append({
            "id": c.id,
            "user_id": c.user_id,
            "user_name": c.user.display_name if c.user else f"User#{c.user_id}",
            "contract_start_date": c.contract_start_date.isoformat(),
            "contract_end_date": c.contract_end_date.isoformat(),
            "status": c.status,
            "is_company_involved": c.is_company_involved,
            "latest_workplace": latest_ep.workplace_name if latest_ep else "未登録",
            "latest_job_title": latest_ep.job_title if latest_ep else None,
            "voice_count": len(c.voice_logs),
            "action_count": len(c.action_logs)
        })
    return jsonify(result), 200

@job_retention_bp.route('/contracts', methods=['POST'])
@jwt_required()
def create_contract():
    """新規定着支援契約の作成"""
    identity = get_jwt_identity()
    try:
        supporter_id = extract_staff_id(identity)
    except Exception:
        supporter_id = None

    data = request.get_json() or {}
    user_id = data.get('user_id')
    start_date_str = data.get('contract_start_date')
    end_date_str = data.get('contract_end_date')

    if not user_id or not start_date_str or not end_date_str:
        return jsonify({"msg": "user_id, contract_start_date, contract_end_date は必須です。"}), 400

    try:
        start_date = _parse_date(start_date_str)
        end_date = _parse_date(end_date_str)
        job_start_date = _parse_date(data.get('job_start_date'))

        contract = JobRetentionService.create_contract(
            user_id=int(user_id),
            office_service_configuration_id=data.get('office_service_configuration_id'),
            contract_start_date=start_date,
            contract_end_date=end_date,
            is_company_involved=bool(data.get('is_company_involved', False)),
            consent_status=data.get('consent_status', 'CONSENTED_ALL'),
            initial_workplace_name=data.get('workplace_name'),
            job_start_date=job_start_date,
            job_title=data.get('job_title'),
            work_conditions=data.get('work_conditions'),
            contract_details=data.get('contract_details'),
            actor_supporter_id=supporter_id
        )
        return jsonify({"msg": "契約を作成しました。", "id": contract.id}), 201
    except ValueError as e:
        return jsonify({"msg": str(e)}), 400
    except Exception as e:
        return jsonify({"msg": f"エラーが発生しました: {str(e)}"}), 500

@job_retention_bp.route('/contracts/<int:contract_id>', methods=['GET'])
@jwt_required()
def get_contract(contract_id: int):
    """契約詳細の取得"""
    contract = JobRetentionService.get_contract(contract_id)
    if not contract:
        return jsonify({"msg": "契約が見つかりません。"}), 404

    episodes = []
    for ep in contract.episodes:
        episodes.append({
            "id": ep.id,
            "episode_number": ep.episode_number,
            "workplace_name": ep.workplace_name,
            "job_title": ep.job_title,
            "department_name": ep.department_name,
            "job_start_date": ep.job_start_date.isoformat(),
            "job_end_date": ep.job_end_date.isoformat() if ep.job_end_date else None,
            "work_conditions": ep.work_conditions,
            "resignation_reason": ep.resignation_reason
        })

    return jsonify({
        "id": contract.id,
        "user_id": contract.user_id,
        "user_name": contract.user.display_name if contract.user else f"User#{contract.user_id}",
        "contract_start_date": contract.contract_start_date.isoformat(),
        "contract_end_date": contract.contract_end_date.isoformat(),
        "status": contract.status,
        "is_company_involved": contract.is_company_involved,
        "consent_status": contract.consent_status,
        "contract_details": contract.contract_details,
        "episodes": episodes
    }), 200

@job_retention_bp.route('/my-contract', methods=['GET'])
@jwt_required()
def get_my_contract():
    """本人用: ログイン中利用者の定着契約を取得"""
    identity = get_jwt_identity()
    # identity は 'user:5' 形式
    if not identity or not identity.startswith('user:'):
        return jsonify({"msg": "利用者アカウントでログインしてください。"}), 403
    try:
        user_id = int(identity.split(':')[1])
    except Exception:
        return jsonify({"msg": "無効なユーザー識別子です。"}), 400

    contract = JobRetentionService.get_contract_by_user(user_id)
    if not contract:
        # アクティブな契約がなければ最新の契約を探す
        contracts = JobRetentionContract.query.filter_by(user_id=user_id).order_by(JobRetentionContract.created_at.desc()).all()
        if not contracts:
            return jsonify({"msg": "定着支援の利用情報が見つかりません。"}), 404
        contract = contracts[0]

    latest_ep = contract.episodes[-1] if contract.episodes else None
    return jsonify({
        "id": contract.id,
        "user_id": contract.user_id,
        "user_name": contract.user.display_name if contract.user else "",
        "contract_start_date": contract.contract_start_date.isoformat(),
        "contract_end_date": contract.contract_end_date.isoformat(),
        "status": contract.status,
        "workplace_name": latest_ep.workplace_name if latest_ep else ""
    }), 200

# ====================================================================
# 就労エピソード（転職・退職）
# ====================================================================
@job_retention_bp.route('/contracts/<int:contract_id>/episodes', methods=['POST'])
@jwt_required()
def add_episode(contract_id: int):
    """新しい就労エピソード（転職先）を追加"""
    identity = get_jwt_identity()
    try:
        supporter_id = extract_staff_id(identity)
    except Exception:
        supporter_id = None

    data = request.get_json() or {}
    workplace_name = data.get('workplace_name')
    start_date_str = data.get('job_start_date')
    if not workplace_name or not start_date_str:
        return jsonify({"msg": "workplace_name, job_start_date は必須です。"}), 400

    try:
        episode = JobRetentionService.add_employment_episode(
            contract_id=contract_id,
            workplace_name=workplace_name,
            job_start_date=_parse_date(start_date_str),
            job_title=data.get('job_title'),
            department_name=data.get('department_name'),
            work_conditions=data.get('work_conditions'),
            previous_episode_id=data.get('previous_episode_id'),
            actor_supporter_id=supporter_id
        )
        return jsonify({"msg": "就労エピソードを追加しました。", "id": episode.id}), 201
    except ValueError as e:
        return jsonify({"msg": str(e)}), 400

@job_retention_bp.route('/episodes/<int:episode_id>/end', methods=['POST'])
@jwt_required()
def end_episode(episode_id: int):
    """退職の記録（契約ステータスは自動終了せず TRANSITION_PENDING へ）"""
    identity = get_jwt_identity()
    try:
        supporter_id = extract_staff_id(identity)
    except Exception:
        supporter_id = None

    data = request.get_json() or {}
    end_date_str = data.get('job_end_date')
    if not end_date_str:
        return jsonify({"msg": "job_end_date は必須です。"}), 400

    try:
        episode = JobRetentionService.end_employment_episode(
            episode_id=episode_id,
            job_end_date=_parse_date(end_date_str),
            resignation_reason=data.get('resignation_reason'),
            actor_supporter_id=supporter_id
        )
        return jsonify({"msg": "退職情報を記録しました（転職移行期間へ移行）。", "id": episode.id}), 200
    except ValueError as e:
        return jsonify({"msg": str(e)}), 400

# ====================================================================
# 本人の声（できごとを残す）
# ====================================================================
@job_retention_bp.route('/contracts/<int:contract_id>/voices', methods=['POST'])
@jwt_required()
def record_voice(contract_id: int):
    """本人の一次情報（最近のできごと・困りごと・対処）を登録"""
    data = request.get_json() or {}
    try:
        log = JobRetentionService.record_user_voice(
            contract_id=contract_id,
            raw_voice=data.get('raw_voice'),
            trouble_point=data.get('trouble_point'),
            success_point=data.get('success_point'),
            self_coping_action=data.get('self_coping_action'),
            self_coping_result=data.get('self_coping_result'),
            needs_help=bool(data.get('needs_help', False)),
            help_topic=data.get('help_topic')
        )
        return jsonify({"msg": "できごとを記録しました。", "id": log.id}), 201
    except ValueError as e:
        return jsonify({"msg": str(e)}), 400

@job_retention_bp.route('/contracts/<int:contract_id>/voices', methods=['GET'])
@jwt_required()
def list_voices(contract_id: int):
    """本人の声一覧を取得"""
    logs = JobRetentionService.list_user_voices(contract_id)
    result = []
    for l in logs:
        result.append({
            "id": l.id,
            "logged_at": l.logged_at.isoformat(),
            "raw_voice": l.raw_voice,
            "trouble_point": l.trouble_point,
            "success_point": l.success_point,
            "self_coping_action": l.self_coping_action,
            "self_coping_result": l.self_coping_result,
            "needs_help": l.needs_help,
            "help_topic": l.help_topic
        })
    return jsonify(result), 200

# ====================================================================
# 支援員の支援実施記録 (面談＋訪問＋調整など複数種別)
# ====================================================================
@job_retention_bp.route('/contracts/<int:contract_id>/actions', methods=['POST'])
@jwt_required()
def record_action(contract_id: int):
    """支援員の支援実施記録を登録"""
    identity = get_jwt_identity()
    try:
        supporter_id = extract_staff_id(identity)
    except Exception:
        # 職員IDが明示指定されている場合（管理者等）
        supporter_id = request.get_json().get('supporter_id', 1)

    data = request.get_json() or {}
    action_date_str = data.get('action_date')
    confirmed_situation = data.get('confirmed_situation')
    provided_support = data.get('provided_support')

    if not action_date_str or not confirmed_situation or not provided_support:
        return jsonify({"msg": "action_date, confirmed_situation, provided_support は必須です。"}), 400

    try:
        action_log = JobRetentionService.record_support_action(
            contract_id=contract_id,
            supporter_id=supporter_id,
            action_date=_parse_date(action_date_str),
            confirmed_situation=confirmed_situation,
            provided_support=provided_support,
            has_user_interview=bool(data.get('has_user_interview', False)),
            interview_method=data.get('interview_method'),
            has_company_visit=bool(data.get('has_company_visit', False)),
            has_coordination=bool(data.get('has_coordination', False)),
            has_other_support=bool(data.get('has_other_support', False)),
            user_action_observed=data.get('user_action_observed'),
            staff_intervention_boundary=data.get('staff_intervention_boundary'),
            next_step=data.get('next_step')
        )
        return jsonify({"msg": "支援記録を登録しました。", "id": action_log.id}), 201
    except ValueError as e:
        return jsonify({"msg": str(e)}), 400

@job_retention_bp.route('/contracts/<int:contract_id>/actions', methods=['GET'])
@jwt_required()
def list_actions(contract_id: int):
    """支援実施記録一覧を取得"""
    actions = JobRetentionService.list_support_actions(contract_id)
    result = []
    for a in actions:
        result.append({
            "id": a.id,
            "action_date": a.action_date.isoformat(),
            "supporter_name": f"{a.supporter.last_name} {a.supporter.first_name}" if a.supporter else "",
            "has_user_interview": a.has_user_interview,
            "interview_method": a.interview_method,
            "has_company_visit": a.has_company_visit,
            "has_coordination": a.has_coordination,
            "has_other_support": a.has_other_support,
            "confirmed_situation": a.confirmed_situation,
            "provided_support": a.provided_support,
            "user_action_observed": a.user_action_observed,
            "staff_intervention_boundary": a.staff_intervention_boundary,
            "next_step": a.next_step
        })
    return jsonify(result), 200

# ====================================================================
# 支援レポート (ルールベース自動マッピング & 保存)
# ====================================================================
@job_retention_bp.route('/contracts/<int:contract_id>/monthly-reports/<year_month>/preview', methods=['GET'])
@jwt_required()
def preview_monthly_report(contract_id: int, year_month: str):
    """一次情報から公式項目へマッピングした初期プレビューを生成"""
    try:
        preview = JobRetentionService.build_monthly_report_preview(contract_id, year_month)
        # 既存の下書きまたは確定済みがあればそれを優先して返す
        existing = JobRetentionService.get_monthly_report(contract_id, year_month)
        if existing:
            return jsonify({
                "contract_id": contract_id,
                "report_year_month": year_month,
                "interview_records": existing.interview_records,
                "company_visit_records": existing.company_visit_records,
                "work_status_summary": existing.work_status_summary,
                "life_status_summary": existing.life_status_summary,
                "user_coping_summary": existing.user_coping_summary,
                "employer_feedback_summary": existing.employer_feedback_summary,
                "support_details": existing.support_details,
                "future_support_policy": existing.future_support_policy,
                "status": existing.status,
                "is_existing": True
            }), 200
        preview["is_existing"] = False
        return jsonify(preview), 200
    except ValueError as e:
        return jsonify({"msg": str(e)}), 400

@job_retention_bp.route('/contracts/<int:contract_id>/monthly-reports/<year_month>', methods=['POST'])
@jwt_required()
def save_monthly_report(contract_id: int, year_month: str):
    """月次支援レポートを保存または確定"""
    identity = get_jwt_identity()
    try:
        supporter_id = extract_staff_id(identity)
    except Exception:
        supporter_id = 1

    data = request.get_json() or {}
    finalize = bool(data.get('finalize', False))

    try:
        report = JobRetentionService.save_monthly_report(
            contract_id=contract_id,
            supporter_id=supporter_id,
            year_month=year_month,
            report_data=data,
            finalize=finalize
        )
        return jsonify({
            "msg": "レポートを確定しました。" if finalize else "レポートを下書き保存しました。",
            "id": report.id,
            "status": report.status
        }), 200
    except ValueError as e:
        return jsonify({"msg": str(e)}), 400
