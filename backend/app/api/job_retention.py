# backend/app/api/job_retention.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
import datetime
from typing import List
from sqlalchemy.exc import IntegrityError
from backend.app.services.job_retention_service import JobRetentionService, JobRetentionConflictError
from backend.app.services.core_service import check_permission
from backend.app.utils.tenant import extract_staff_id, resolve_tenant_scope
from backend.app.domain.attendance.exceptions import AttendanceForbiddenError
from backend.app.models import (
    Supporter, User, OfficeSetting, OfficeServiceConfiguration,
    ServiceCertificate, JobRetentionContract, calculate_max_review_deadline
)
from backend.app.extensions import db

job_retention_bp = Blueprint('job_retention', __name__, url_prefix='/api/job-retention')

def _parse_date(date_str):
    if not date_str:
        return None
    if isinstance(date_str, datetime.date):
        return date_str
    return datetime.datetime.strptime(date_str, '%Y-%m-%d').date()

# ====================================================================
# 認可・アクター制御ヘルパー (Fail Closed)
# ====================================================================
def extract_actor_info(identity: str) -> tuple[str, int]:
    """
    JWTのidentity文字列（例: 'staff:1', 'user:5'）を厳格にパースする。
    """
    if not identity or not isinstance(identity, str):
        raise AttendanceForbiddenError("無効なセッション識別子です。")
    parts = identity.split(":")
    if len(parts) != 2:
        raise AttendanceForbiddenError("無効なセッション識別子形式です。")
    actor_type, id_str = parts[0], parts[1]
    if actor_type not in ('staff', 'user', 'company'):
        raise AttendanceForbiddenError("未知のアクター種別です。")
    if not id_str.isascii() or not id_str.isdecimal() or id_str.startswith('0'):
        raise AttendanceForbiddenError("無効なID形式です。")
    try:
        actor_id = int(id_str)
        if actor_id <= 0:
            raise AttendanceForbiddenError("無効なIDです。")
        return actor_type, actor_id
    except ValueError:
        raise AttendanceForbiddenError("無効なIDです。")

def require_staff_actor(identity: str) -> int:
    """支援員（職員）専用ガード。職員でなければ即座に403"""
    actor_type, actor_id = extract_actor_info(identity)
    if actor_type != 'staff':
        raise AttendanceForbiddenError("支援員アカウントでのみアクセス可能です。")
    return actor_id

def require_user_actor(identity: str) -> int:
    """本人（利用者）専用ガード。本人でなければ即座に403"""
    actor_type, actor_id = extract_actor_info(identity)
    if actor_type != 'user':
        raise AttendanceForbiddenError("本人（利用者）アカウントでのみアクセス可能です。")
    return actor_id

def require_staff_permission(supporter_id: int, permission_name: str):
    """
    支援員が指定の定着支援RBACパーミッションを持っているかを検証 (Fail Closed)。
    権限未定義・不足時は即座に403。
    """
    if not check_permission(f"staff:{supporter_id}", permission_name):
        raise AttendanceForbiddenError(f"必要な定着支援権限 ({permission_name}) を保持していません。")

def validate_supporter_access_to_contract(supporter_id: int, contract: JobRetentionContract):
    """
    支援員が定着支援契約にアクセス可能かを検証。
    認可判定の中心は JobRetentionContract.office_service_configuration_id。
    利用者が同じ事業所の別サービスを利用しているだけではアクセス不可。
    """
    supporter = db.session.get(Supporter, supporter_id)
    if not supporter or not supporter.office_id:
        raise AttendanceForbiddenError("支援員の所属事業所が確認できません。")

    if not contract.office_service_configuration_id:
        raise AttendanceForbiddenError("契約の所属事業所サービス設定が確認できません。")

    service_config = db.session.get(OfficeServiceConfiguration, contract.office_service_configuration_id)
    if not service_config or not service_config.office_id:
        raise AttendanceForbiddenError("契約の所属事業所サービス設定が存在しないか無効です。")

    contract_office_id = service_config.office_id

    # 1. 支援員の所属事業所と契約事業所が一致する場合
    if supporter.office_id == contract_office_id:
        return True

    # 2. 支援員が CORPORATE スコープの場合
    claims = get_jwt()
    scopes = claims.get('role_scopes', [])
    scope_info = resolve_tenant_scope(supporter_id, scopes)

    if scope_info.get('level') == 'CORPORATE':
        contract_office = db.session.get(OfficeSetting, contract_office_id)
        supp_office = db.session.get(OfficeSetting, supporter.office_id)
        if not contract_office or not supp_office:
            raise AttendanceForbiddenError("事業所の法人情報を確認できません。")

        # 支援員の所属法人と、対象契約側の事業所が同一法人に属することを確認
        if (
            contract_office.corporation_id and 
            supp_office.corporation_id and 
            contract_office.corporation_id == supp_office.corporation_id
        ):
            return True
        else:
            raise AttendanceForbiddenError("対象契約の事業所は同一法人に属していません。")

    if scope_info.get('level') == 'SYSTEM':
        return True

    raise AttendanceForbiddenError("対象定着支援契約に対するアクセス権限がありません。")

def validate_supporter_access_to_service_config(supporter_id: int, service_config_id: int):
    """支援員が指定の OfficeServiceConfiguration を管轄しているか検証"""
    supporter = db.session.get(Supporter, supporter_id)
    if not supporter or not supporter.office_id:
        raise AttendanceForbiddenError("支援員の所属事業所が確認できません。")

    service_config = db.session.get(OfficeServiceConfiguration, service_config_id)
    if not service_config or not service_config.office_id:
        raise AttendanceForbiddenError("事業所サービス設定が存在しません。")

    if supporter.office_id == service_config.office_id:
        return True

    claims = get_jwt()
    scopes = claims.get('role_scopes', [])
    scope_info = resolve_tenant_scope(supporter_id, scopes)
    if scope_info.get('level') == 'CORPORATE':
        target_office = db.session.get(OfficeSetting, service_config.office_id)
        supp_office = db.session.get(OfficeSetting, supporter.office_id)
        if target_office and supp_office and target_office.corporation_id == supp_office.corporation_id:
            return True

    if scope_info.get('level') == 'SYSTEM':
        return True

    raise AttendanceForbiddenError("指定された事業所サービス設定に対する操作権限がありません。")

def validate_user_access_to_contract(user_id: int, contract: JobRetentionContract):
    """本人が自分の契約にアクセスしているかを厳格に検証（他者アクセスは即座に403）"""
    if contract.user_id != user_id:
        raise AttendanceForbiddenError("他利用者の定着支援データにはアクセスできません。")
    return True

# エラーハンドラー
@job_retention_bp.errorhandler(AttendanceForbiddenError)
def handle_forbidden(e):
    return jsonify({"msg": str(e)}), 403

# ====================================================================
# 契約管理 (支援員専用)
# ====================================================================
@job_retention_bp.route('/contracts', methods=['GET'])
@jwt_required()
def list_contracts():
    """定着支援契約の一覧取得（支援員専用・テナント分離・JOB_RETENTION_VIEW必須）"""
    identity = get_jwt_identity()
    supporter_id = require_staff_actor(identity)
    require_staff_permission(supporter_id, 'JOB_RETENTION_VIEW')

    supporter = db.session.get(Supporter, supporter_id)
    if not supporter or not supporter.office_id:
        return jsonify({"msg": "所属事業所が不明です。"}), 403

    status = request.args.get('status')
    contracts = JobRetentionService.list_contracts(status=status)

    result = []
    for c in contracts:
        # アクセス権のある契約のみに絞り込み (Fail Closed)
        try:
            validate_supporter_access_to_contract(supporter_id, c)
        except AttendanceForbiddenError:
            continue

        latest_ep = c.episodes[-1] if c.episodes else None
        active_plan = JobRetentionService.get_active_support_plan(c.id)
        plan_summary = None
        if active_plan:
            status_info = active_plan.compute_deadline_status()
            plan_summary = {
                "id": active_plan.id,
                "version": active_plan.version,
                "overall_support_goal": active_plan.overall_support_goal,
                "start_date": active_plan.start_date.isoformat(),
                "review_date": active_plan.review_date.isoformat() if active_plan.review_date else None,
                "review_reason": active_plan.review_reason,
                "plan_end_date": active_plan.plan_end_date.isoformat(),
                "next_plan_start_date": active_plan.next_plan_start_date.isoformat(),
                "next_review_deadline": active_plan.plan_end_date.isoformat(),
                "deadline_status": status_info["status_code"],
                "days_diff": status_info["days_diff"],
                "is_overdue": status_info["is_overdue"]
            }

        result.append({
            "id": c.id,
            "user_id": c.user_id,
            "user_name": c.user.display_name if c.user else f"User#{c.user_id}",
            "office_service_configuration_id": c.office_service_configuration_id,
            "contract_start_date": c.contract_start_date.isoformat(),
            "contract_end_date": c.contract_end_date.isoformat(),
            "status": c.status,
            "is_company_involved": c.is_company_involved,
            "consent_status": c.consent_status,
            "latest_workplace": latest_ep.workplace_name if latest_ep else "未登録",
            "latest_job_title": latest_ep.job_title if latest_ep else None,
            "voice_count": len(c.voice_logs),
            "action_count": len(c.action_logs),
            "active_plan": plan_summary
        })
    return jsonify(result), 200

@job_retention_bp.route('/contracts', methods=['POST'])
@jwt_required()
def create_contract():
    """新規定着支援契約の作成（支援員専用・JOB_RETENTION_EDIT必須）"""
    identity = get_jwt_identity()
    supporter_id = require_staff_actor(identity)
    require_staff_permission(supporter_id, 'JOB_RETENTION_EDIT')

    data = request.get_json() or {}
    user_id = data.get('user_id')
    office_service_config_id = data.get('office_service_configuration_id')
    start_date_str = data.get('contract_start_date')
    end_date_str = data.get('contract_end_date')

    if not user_id or not office_service_config_id or not start_date_str or not end_date_str:
        return jsonify({"msg": "user_id, office_service_configuration_id, contract_start_date, contract_end_date は必須です。"}), 400

    user = db.session.get(User, int(user_id))
    if not user:
        return jsonify({"msg": "利用者が存在しません。"}), 404

    # 支援員が指定の office_service_configuration_id にアクセス可能か検証
    validate_supporter_access_to_service_config(supporter_id, int(office_service_config_id))

    try:
        start_date = _parse_date(start_date_str)
        end_date = _parse_date(end_date_str)
        job_start_date = _parse_date(data.get('job_start_date'))

        # 情報共有同意の初期値は Fail Closed (NOT_SET), is_company_involved初期値はFalse
        contract = JobRetentionService.create_contract(
            user_id=int(user_id),
            office_service_configuration_id=int(office_service_config_id),
            contract_start_date=start_date,
            contract_end_date=end_date,
            is_company_involved=bool(data.get('is_company_involved', False)),
            consent_status=data.get('consent_status', 'NOT_SET'),
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
    """契約詳細の取得（支援員または本人）"""
    identity = get_jwt_identity()
    actor_type, actor_id = extract_actor_info(identity)

    contract = JobRetentionService.get_contract(contract_id)
    if not contract:
        return jsonify({"msg": "契約が見つかりません。"}), 404

    # 認可チェック
    if actor_type == 'staff':
        require_staff_permission(actor_id, 'JOB_RETENTION_VIEW')
        validate_supporter_access_to_contract(actor_id, contract)
    elif actor_type == 'user':
        validate_user_access_to_contract(actor_id, contract)
    else:
        return jsonify({"msg": "権限がありません。"}), 403

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

    active_plan = JobRetentionService.get_active_support_plan(contract.id)
    plan_summary = None
    if active_plan:
        status_info = active_plan.compute_deadline_status()
        plan_summary = {
            "id": active_plan.id,
            "version": active_plan.version,
            "overall_support_goal": active_plan.overall_support_goal,
            "start_date": active_plan.start_date.isoformat(),
            "review_date": active_plan.review_date.isoformat() if active_plan.review_date else None,
            "review_reason": active_plan.review_reason,
            "plan_end_date": active_plan.plan_end_date.isoformat(),
            "next_plan_start_date": active_plan.next_plan_start_date.isoformat(),
            "next_review_deadline": active_plan.plan_end_date.isoformat(),
            "deadline_status": status_info["status_code"],
            "days_diff": status_info["days_diff"],
            "is_overdue": status_info["is_overdue"]
        }

    return jsonify({
        "id": contract.id,
        "user_id": contract.user_id,
        "user_name": contract.user.display_name if contract.user else f"User#{contract.user_id}",
        "office_service_configuration_id": contract.office_service_configuration_id,
        "contract_start_date": contract.contract_start_date.isoformat(),
        "contract_end_date": contract.contract_end_date.isoformat(),
        "status": contract.status,
        "is_company_involved": contract.is_company_involved,
        "consent_status": contract.consent_status,
        "contract_details": contract.contract_details,
        "episodes": episodes,
        "active_plan": plan_summary
    }), 200

# ====================================================================
# 本人専用エンドポイント (My Contract)
# ====================================================================
@job_retention_bp.route('/my-contract', methods=['GET'])
@jwt_required()
def get_my_contract():
    """本人用: ログイン中利用者の定着契約を取得"""
    identity = get_jwt_identity()
    user_id = require_user_actor(identity)

    contract = JobRetentionService.get_contract_by_user(user_id)
    if not contract:
        contracts = JobRetentionContract.query.filter_by(user_id=user_id).order_by(JobRetentionContract.created_at.desc()).all()
        if not contracts:
            return jsonify({"msg": "定着支援の利用情報が見つかりません。"}), 404
        contract = contracts[0]

    latest_ep = contract.episodes[-1] if contract.episodes else None
    return jsonify({
        "id": contract.id,
        "user_id": contract.user_id,
        "user_name": contract.user.display_name if contract.user else "",
        "office_service_configuration_id": contract.office_service_configuration_id,
        "contract_start_date": contract.contract_start_date.isoformat(),
        "contract_end_date": contract.contract_end_date.isoformat(),
        "status": contract.status,
        "is_company_involved": contract.is_company_involved,
        "consent_status": contract.consent_status,
        "workplace_name": latest_ep.workplace_name if latest_ep else "",
        "job_title": latest_ep.job_title if latest_ep else None,
        "work_conditions": latest_ep.work_conditions if latest_ep else None
    }), 200

# ====================================================================
# 就労エピソード（転職・退職） (支援員専用)
# ====================================================================
@job_retention_bp.route('/contracts/<int:contract_id>/episodes', methods=['POST'])
@jwt_required()
def add_episode(contract_id: int):
    """新しい就労エピソード（転職先）を追加（支援員専用・JOB_RETENTION_EDIT必須）"""
    identity = get_jwt_identity()
    supporter_id = require_staff_actor(identity)
    require_staff_permission(supporter_id, 'JOB_RETENTION_EDIT')

    contract = JobRetentionService.get_contract(contract_id)
    if not contract:
        return jsonify({"msg": "契約が見つかりません。"}), 404
    validate_supporter_access_to_contract(supporter_id, contract)

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
    """退職の記録（支援員専用・JOB_RETENTION_EDIT必須）"""
    identity = get_jwt_identity()
    supporter_id = require_staff_actor(identity)
    require_staff_permission(supporter_id, 'JOB_RETENTION_EDIT')

    from backend.app.models import RetentionEmploymentEpisode
    episode = db.session.get(RetentionEmploymentEpisode, episode_id)
    if not episode or not episode.contract:
        return jsonify({"msg": "就労エピソードが見つかりません。"}), 404
    validate_supporter_access_to_contract(supporter_id, episode.contract)

    data = request.get_json() or {}
    end_date_str = data.get('job_end_date')
    if not end_date_str:
        return jsonify({"msg": "job_end_date は必須です。"}), 400

    try:
        end_ep = JobRetentionService.end_employment_episode(
            episode_id=episode_id,
            job_end_date=_parse_date(end_date_str),
            resignation_reason=data.get('resignation_reason'),
            actor_supporter_id=supporter_id
        )
        return jsonify({"msg": "退職情報を記録しました（転職移行期間へ移行）。", "id": end_ep.id}), 200
    except ValueError as e:
        return jsonify({"msg": str(e)}), 400

# ====================================================================
# 本人の声（できごとを残す）
# ====================================================================
@job_retention_bp.route('/contracts/<int:contract_id>/voices', methods=['POST'])
@jwt_required()
def record_voice(contract_id: int):
    """
    本人の一次情報（最近のできごと・困りごと・対処）を登録。
    ★ 本人の生の声という一次情報のため、本人アクターのみ作成可能（支援員は403）。
    """
    identity = get_jwt_identity()
    user_id = require_user_actor(identity)

    contract = JobRetentionService.get_contract(contract_id)
    if not contract:
        return jsonify({"msg": "契約が見つかりません。"}), 404

    # 本人が自身の契約にアクセスしているか検証 (他利用者の契約は403)
    validate_user_access_to_contract(user_id, contract)

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
            help_topic=data.get('help_topic'),
            input_channel='USER_DIRECT'
        )
        return jsonify({"msg": "できごとを記録しました。", "id": log.id}), 201
    except ValueError as e:
        return jsonify({"msg": str(e)}), 400

@job_retention_bp.route('/contracts/<int:contract_id>/voices', methods=['GET'])
@jwt_required()
def list_voices(contract_id: int):
    """本人の声一覧を取得（本人または閲覧権限を持つ支援員）"""
    identity = get_jwt_identity()
    actor_type, actor_id = extract_actor_info(identity)

    contract = JobRetentionService.get_contract(contract_id)
    if not contract:
        return jsonify({"msg": "契約が見つかりません。"}), 404

    if actor_type == 'user':
        validate_user_access_to_contract(actor_id, contract)
    elif actor_type == 'staff':
        require_staff_permission(actor_id, 'JOB_RETENTION_VIEW')
        validate_supporter_access_to_contract(actor_id, contract)
    else:
        return jsonify({"msg": "権限がありません。"}), 403

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
            "help_topic": l.help_topic,
            "input_channel": getattr(l, 'input_channel', 'USER_DIRECT')
        })
    return jsonify(result), 200

# ====================================================================
# 支援員の支援実施記録 (支援員専用)
# ====================================================================
@job_retention_bp.route('/contracts/<int:contract_id>/actions', methods=['POST'])
@jwt_required()
def record_action(contract_id: int):
    """支援員の支援実施記録を登録（支援員専用・JOB_RETENTION_EDIT必須・フォールバック禁止）"""
    identity = get_jwt_identity()
    supporter_id = require_staff_actor(identity)
    require_staff_permission(supporter_id, 'JOB_RETENTION_EDIT')

    contract = JobRetentionService.get_contract(contract_id)
    if not contract:
        return jsonify({"msg": "契約が見つかりません。"}), 404
    validate_supporter_access_to_contract(supporter_id, contract)

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
    """支援実施記録一覧を取得（支援員専用・JOB_RETENTION_VIEW必須）"""
    identity = get_jwt_identity()
    supporter_id = require_staff_actor(identity)
    require_staff_permission(supporter_id, 'JOB_RETENTION_VIEW')

    contract = JobRetentionService.get_contract(contract_id)
    if not contract:
        return jsonify({"msg": "契約が見つかりません。"}), 404
    validate_supporter_access_to_contract(supporter_id, contract)

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
# 支援レポート (支援員専用)
# ====================================================================
@job_retention_bp.route('/contracts/<int:contract_id>/monthly-reports/<year_month>/preview', methods=['GET'])
@jwt_required()
def preview_monthly_report(contract_id: int, year_month: str):
    """一次情報から公式項目へマッピングした初期プレビューを生成（支援員専用・JOB_RETENTION_VIEW必須）"""
    identity = get_jwt_identity()
    supporter_id = require_staff_actor(identity)
    require_staff_permission(supporter_id, 'JOB_RETENTION_VIEW')

    contract = JobRetentionService.get_contract(contract_id)
    if not contract:
        return jsonify({"msg": "契約が見つかりません。"}), 404
    validate_supporter_access_to_contract(supporter_id, contract)

    try:
        preview = JobRetentionService.build_monthly_report_preview(contract_id, year_month)
        existing = JobRetentionService.get_monthly_report(contract_id, year_month)
        if existing:
            return jsonify({
                "contract_id": contract_id,
                "report_year_month": year_month,
                # 内部整理項目
                "interview_records": existing.interview_records,
                "company_visit_records": existing.company_visit_records,
                "work_status_summary": existing.work_status_summary,
                "life_status_summary": existing.life_status_summary,
                "user_coping_summary": existing.user_coping_summary,
                "employer_feedback_summary": existing.employer_feedback_summary,
                "support_details": existing.support_details,
                "future_support_policy": existing.future_support_policy,
                # 公式帳票項目
                "support_goal": getattr(existing, 'support_goal', None),
                "support_content": getattr(existing, 'support_content', None),
                "support_result": getattr(existing, 'support_result', None),
                "future_support_plan": getattr(existing, 'future_support_plan', None),
                "stakeholder_efforts": getattr(existing, 'stakeholder_efforts', None),
                "sharing_notes": getattr(existing, 'sharing_notes', None),
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
    """
    月次支援レポートを保存または確定。
    - 下書き保存 (finalize=False): JOB_RETENTION_EDIT 必須
    - 確定 (finalize=True): JOB_RETENTION_APPROVE 必須
    """
    identity = get_jwt_identity()
    supporter_id = require_staff_actor(identity)

    data = request.get_json() or {}
    finalize = bool(data.get('finalize', False))

    if finalize:
        require_staff_permission(supporter_id, 'JOB_RETENTION_APPROVE')
    else:
        require_staff_permission(supporter_id, 'JOB_RETENTION_EDIT')

    contract = JobRetentionService.get_contract(contract_id)
    if not contract:
        return jsonify({"msg": "契約が見つかりません。"}), 404
    validate_supporter_access_to_contract(supporter_id, contract)

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
    except JobRetentionConflictError as e:
        return jsonify({"msg": str(e)}), 409
    except IntegrityError:
        db.session.rollback()
        return jsonify({"msg": "同一契約・同一年月のレポートが既に存在するか、同時に作成されたため競合しました。"}), 409
    except ValueError as e:
        return jsonify({"msg": str(e)}), 400
    except Exception as e:
        return jsonify({"msg": f"エラーが発生しました: {str(e)}"}), 500


# ====================================================================
# 支援計画 (随時見直し & 6か月上限ガード & 版管理)
# ====================================================================
@job_retention_bp.route('/contracts/<int:contract_id>/support-plan/active', methods=['GET'])
@jwt_required()
def get_active_support_plan(contract_id: int):
    """現在有効な支援計画の取得（支援員または本人）"""
    identity = get_jwt_identity()
    actor_type, actor_id = extract_actor_info(identity)

    contract = JobRetentionService.get_contract(contract_id)
    if not contract:
        return jsonify({"msg": "契約が見つかりません。"}), 404

    if actor_type == 'staff':
        require_staff_permission(actor_id, 'JOB_RETENTION_VIEW')
        validate_supporter_access_to_contract(actor_id, contract)
    elif actor_type == 'user':
        validate_user_access_to_contract(actor_id, contract)
    else:
        return jsonify({"msg": "権限がありません。"}), 403

    active_plan = JobRetentionService.get_active_support_plan(contract_id)
    if not active_plan:
        return jsonify({"has_plan": False, "plan": None}), 200

    status_info = active_plan.compute_deadline_status()
    base_d = active_plan.start_date or active_plan.review_date
    max_deadline = calculate_max_review_deadline(base_d)

    return jsonify({
        "has_plan": True,
        "plan": {
            "id": active_plan.id,
            "version": active_plan.version,
            "overall_support_goal": active_plan.overall_support_goal,
            "start_date": active_plan.start_date.isoformat(),
            "review_date": active_plan.review_date.isoformat() if active_plan.review_date else None,
            "review_reason": active_plan.review_reason,
            "plan_end_date": active_plan.plan_end_date.isoformat(),
            "next_plan_start_date": active_plan.next_plan_start_date.isoformat(),
            "next_review_deadline": active_plan.plan_end_date.isoformat(),
            "status": active_plan.status,
            "deadline_status": status_info["status_code"],
            "days_diff": status_info["days_diff"],
            "is_overdue": status_info["is_overdue"],
            "max_allowed_deadline": max_deadline.isoformat()
        }
    }), 200


@job_retention_bp.route('/contracts/<int:contract_id>/support-plans', methods=['GET'])
@jwt_required()
def list_support_plans(contract_id: int):
    """支援計画の全版履歴の取得（支援員または本人）"""
    identity = get_jwt_identity()
    actor_type, actor_id = extract_actor_info(identity)

    contract = JobRetentionService.get_contract(contract_id)
    if not contract:
        return jsonify({"msg": "契約が見つかりません。"}), 404

    if actor_type == 'staff':
        require_staff_permission(actor_id, 'JOB_RETENTION_VIEW')
        validate_supporter_access_to_contract(actor_id, contract)
    elif actor_type == 'user':
        validate_user_access_to_contract(actor_id, contract)
    else:
        return jsonify({"msg": "権限がありません。"}), 403

    plans = JobRetentionService.list_support_plans(contract_id)
    items = []
    for p in plans:
        status_info = p.compute_deadline_status()
        items.append({
            "id": p.id,
            "version": p.version,
            "overall_support_goal": p.overall_support_goal,
            "start_date": p.start_date.isoformat(),
            "review_date": p.review_date.isoformat() if p.review_date else None,
            "review_reason": p.review_reason,
            "plan_end_date": p.plan_end_date.isoformat(),
            "next_plan_start_date": p.next_plan_start_date.isoformat(),
            "next_review_deadline": p.plan_end_date.isoformat(),
            "status": p.status,
            "deadline_status": status_info["status_code"],
            "days_diff": status_info["days_diff"],
            "is_overdue": status_info["is_overdue"],
            "created_at": p.created_at.isoformat() if p.created_at else None
        })
    return jsonify(items), 200


@job_retention_bp.route('/contracts/<int:contract_id>/support-plan/assistance-data', methods=['GET'])
@jwt_required()
def get_support_plan_assistance_data(contract_id: int):
    """就労定着支援計画（別紙様式2）作成のための入力支援データ取得（支援員専用・JOB_RETENTION_VIEW必須）"""
    identity = get_jwt_identity()
    supporter_id = require_staff_actor(identity)
    require_staff_permission(supporter_id, 'JOB_RETENTION_VIEW')

    contract = JobRetentionService.get_contract(contract_id)
    if not contract:
        return jsonify({"msg": "契約が見つかりません。"}), 404
    validate_supporter_access_to_contract(supporter_id, contract)

    try:
        data = JobRetentionService.get_plan_input_assistance_data(contract_id)
        return jsonify(data), 200
    except ValueError as e:
        return jsonify({"msg": str(e)}), 400
    except Exception as e:
        return jsonify({"msg": f"エラーが発生しました: {str(e)}"}), 500


@job_retention_bp.route('/contracts/<int:contract_id>/support-plans/<int:plan_id>/detail', methods=['GET'])
@jwt_required()
def get_support_plan_detail(contract_id: int, plan_id: int):
    """厚労省様式2の全項目（基本情報スナップショット・支援内容①〜③・出所リンク等）を取得（支援員または本人）"""
    identity = get_jwt_identity()
    actor_type, actor_id = extract_actor_info(identity)

    contract = JobRetentionService.get_contract(contract_id)
    if not contract:
        return jsonify({"msg": "契約が見つかりません。"}), 404

    if actor_type == 'staff':
        require_staff_permission(actor_id, 'JOB_RETENTION_VIEW')
        validate_supporter_access_to_contract(actor_id, contract)
    elif actor_type == 'user':
        validate_user_access_to_contract(actor_id, contract)
    else:
        return jsonify({"msg": "権限がありません。"}), 403

    detail = JobRetentionService.get_support_plan_detail(contract_id, plan_id)
    if not detail:
        return jsonify({"msg": "指定された支援計画が見つかりません。"}), 404

    return jsonify(detail), 200


@job_retention_bp.route('/contracts/<int:contract_id>/support-plans', methods=['POST'])
@jwt_required()
def create_or_review_support_plan(contract_id: int):
    """支援計画の新規作成または随時見直し（支援員専用・JOB_RETENTION_EDIT必須）"""
    identity = get_jwt_identity()
    supporter_id = require_staff_actor(identity)
    require_staff_permission(supporter_id, 'JOB_RETENTION_EDIT')

    contract = JobRetentionService.get_contract(contract_id)
    if not contract:
        return jsonify({"msg": "契約が見つかりません。"}), 404
    validate_supporter_access_to_contract(supporter_id, contract)

    data = request.get_json() or {}
    overall_support_goal = data.get('overall_support_goal')
    plan_end_date_str = data.get('plan_end_date') or data.get('next_review_deadline')

    if not overall_support_goal:
        return jsonify({"msg": "overall_support_goal は必須です。"}), 400

    try:
        plan_end_date = _parse_date(plan_end_date_str)
        review_date = _parse_date(data.get('review_date'))
        start_date = _parse_date(data.get('start_date'))
        review_reason = data.get('review_reason')

        # 様式2固有の拡張データ (Items, SourceLinks, Detail fields, Goals)
        items_data = data.get('items_data')
        source_links_data = data.get('source_links_data')
        detail_fields = data.get('detail_fields')
        long_term_goal_data = data.get('long_term_goal_data')
        short_term_goal_data = data.get('short_term_goal_data')

        plan = JobRetentionService.create_or_review_support_plan(
            contract_id=contract_id,
            overall_support_goal=overall_support_goal,
            plan_end_date=plan_end_date,
            review_date=review_date,
            review_reason=review_reason,
            start_date=start_date,
            supporter_id=supporter_id,
            items_data=items_data,
            source_links_data=source_links_data,
            detail_fields=detail_fields,
            long_term_goal_data=long_term_goal_data,
            short_term_goal_data=short_term_goal_data
        )
        status_info = plan.compute_deadline_status()
        return jsonify({
            "msg": f"支援計画（Version {plan.version}）を確定しました。",
            "plan": {
                "id": plan.id,
                "version": plan.version,
                "overall_support_goal": plan.overall_support_goal,
                "start_date": plan.start_date.isoformat() if plan.start_date else None,
                "review_date": plan.review_date.isoformat() if plan.review_date else None,
                "review_reason": plan.review_reason,
                "plan_end_date": plan.plan_end_date.isoformat() if plan.plan_end_date else None,
                "next_plan_start_date": plan.next_plan_start_date.isoformat() if plan.next_plan_start_date else None,
                "next_review_deadline": plan.plan_end_date.isoformat() if plan.plan_end_date else None,
                "status": plan.status,
                "deadline_status": status_info["status_code"],
                "days_diff": status_info["days_diff"],
                "is_overdue": status_info["is_overdue"]
            }
        }), 201
    except ValueError as e:
        return jsonify({"msg": str(e)}), 400
    except Exception as e:
        return jsonify({"msg": f"エラーが発生しました: {str(e)}"}), 500
