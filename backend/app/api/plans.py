# backend/app/api/plans.py

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app import db
from backend.app.models import SupportPlan, IndividualSupportGoal
from backend.app.services.support_plan_service import SupportPlanService
from backend.app.services.core_service import check_permission, parse_jwt_identity

plans_bp = Blueprint('plans', __name__, url_prefix='/api/plans')
support_plan_service = SupportPlanService()

# -------------------------------------------------------------------
# 1. 計画作成 (DRAFT)
# -------------------------------------------------------------------

@plans_bp.route('/', methods=['POST'])
@jwt_required()
def create_plan():
    """
    新しい個別支援計画の原案 (DRAFT) を作成する。
    """
    role_type, supporter_id = parse_jwt_identity(get_jwt_identity())
    data = request.get_json()
    user_id = data.get('user_id')
    policy_id = data.get('holistic_support_policy_id')
    
    # 新規作成フォーム用パラメータ
    plan_start_date = data.get('plan_start_date')
    plan_end_date = data.get('plan_end_date')
    user_intention_content = data.get('user_intention_content')
    support_policy_content = data.get('support_policy_content')

    if role_type != 'staff':
        return jsonify({"msg": "Permission denied: Requires 'staff' role"}), 403

    if not user_id:
        return jsonify({"msg": "Missing user_id"}), 400

    from backend.app.models import HolisticSupportPolicy
    from datetime import date, datetime
    
    policy = None
    if user_intention_content or support_policy_content:
        # フォームから方針が入力された場合は新規作成
        policy = HolisticSupportPolicy(
            user_id=user_id,
            effective_date=date.today(),
            user_intention_content=user_intention_content or "本人の意向未記入",
            support_policy_content=support_policy_content or "支援の方針未記入"
        )
        db.session.add(policy)
        db.session.flush()
    elif policy_id:
        policy = db.session.get(HolisticSupportPolicy, policy_id)
        
    if not policy:
        # 最新の有効な方針を探す
        policy = HolisticSupportPolicy.query.filter_by(user_id=user_id).order_by(HolisticSupportPolicy.effective_date.desc()).first()
        
    if not policy:
        # なければ暫定支援方針を自動生成して保存
        policy = HolisticSupportPolicy(
            user_id=user_id,
            effective_date=date.today(),
            user_intention_content="【暫定本人の意向】アセスメント未実施のため、初期原案作成用の暫定意向として自動生成",
            support_policy_content="【暫定支援方針】アセスメント未実施のため、初期原案作成用の暫定方針として自動生成"
        )
        db.session.add(policy)
        db.session.flush()

    try:
        new_plan = support_plan_service.create_plan_draft(
            user_id=user_id,
            created_by_id=supporter_id,
            based_on_policy_id=policy.id
        )
        
        # 明示的な原案作成日を設定
        new_plan.draft_created_at = date.today()
        
        # 期間パラメータがあれば上書き
        if plan_start_date:
            new_plan.plan_start_date = datetime.strptime(plan_start_date, "%Y-%m-%d").date()
        if plan_end_date:
            new_plan.plan_end_date = datetime.strptime(plan_end_date, "%Y-%m-%d").date()
            
        db.session.commit()
        return jsonify({
            "msg": "Plan draft created successfully",
            "plan_id": new_plan.id,
            "user_id": new_plan.user_id,
            "status": new_plan.plan_status
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Plan creation failed: {e}"}), 500

# -------------------------------------------------------------------
# 2. 目標の追加 (IndividualSupportGoal)
# -------------------------------------------------------------------

@plans_bp.route('/<int:plan_id>/goal', methods=['POST'])
@jwt_required()
def add_individual_goal(plan_id):
    """
    既存の計画に具体的な個別支援目標を追加する。
    """
    _, supporter_id = parse_jwt_identity(get_jwt_identity())
    data = request.get_json()
    short_term_goal_id = data.get('short_term_goal_id')
    
    # 権限は CREATE_PLAN でカバーされると仮定

    if not short_term_goal_id or not data.get('concrete_goal'):
        return jsonify({"msg": "Missing required goal data"}), 400
        
    try:
        # ここでは、簡略化のため、LongTermGoal -> ShortTermGoal の階層構造は
        # フロントエンドが既に持っているものとし、直接 ShortTermGoal ID を使います。
        
        new_goal = IndividualSupportGoal(
            short_term_goal_id=short_term_goal_id,
            concrete_goal=data['concrete_goal'],
            user_commitment=data.get('user_commitment', '未記入'),
            support_actions=data.get('support_actions', '未記入'),
            service_type=data.get('service_type', 'TRAINING'),
            is_facility_in_deemed=data.get('is_facility_in_deemed', False),
            is_work_preparation_positioning=data.get('is_work_preparation_positioning', False)
        )
        
        db.session.add(new_goal)
        db.session.commit()
        
        return jsonify({
            "msg": "Individual goal added",
            "goal_id": new_goal.id,
            "plan_id": plan_id
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Goal creation failed: {e}"}), 500

# -------------------------------------------------------------------
# 3. 同意の記録 API
# -------------------------------------------------------------------

@plans_bp.route('/<int:plan_id>/consent', methods=['POST'])
@jwt_required()
def record_consent(plan_id):
    """
    計画案に対する利用者の説明・同意を記録し、DocumentConsentLogを生成する。
    """
    _, supporter_id = parse_jwt_identity(get_jwt_identity())
    data = request.get_json()
    user_id = data.get('user_id')
    consent_proof = data.get('consent_proof', 'DIGITAL_SIGNATURE')
    generated_document_url = data.get('generated_document_url')

    if not user_id:
        return jsonify({"msg": "Missing user_id"}), 400

    plan = SupportPlan.query.get(plan_id)
    if not plan:
        return jsonify({"msg": "SupportPlan not found"}), 404

    if plan.plan_status != 'PENDING_CONSENT':
        return jsonify({"msg": "Plan status is not PENDING_CONSENT"}), 400

    try:
        from backend.app.models import DocumentConsentLog
        from datetime import date
        
        # 説明同意日を設定
        plan.consented_at = date.today()
        plan.explained_at = date.today() # 同意日と同日に設定
        
        consent_log = DocumentConsentLog(
            user_id=user_id,
            document_type='SUPPORT_PLAN',
            document_id=plan_id,
            consent_proof=consent_proof,
            generated_document_url=generated_document_url
        )
        db.session.add(consent_log)
        db.session.commit()

        return jsonify({
            "msg": "Consent recorded successfully",
            "consent_log_id": consent_log.id
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Failed to record consent: {e}"}), 500

# -------------------------------------------------------------------
# 4. 計画の承認・有効化 API
# -------------------------------------------------------------------

@plans_bp.route('/<int:plan_id>/activate', methods=['POST'])
@jwt_required()
def activate_plan(plan_id):
    """
    サビ管承認と利用者同意が完了した計画を ACTIVE にする。
    """
    _, supporter_id = parse_jwt_identity(get_jwt_identity())
    data = request.get_json()
    consent_log_id = data.get('consent_log_id')
    
    # 承認者はサビ管である必要があり、supporter_id がサビ管であることを検証する
    from backend.app.models import Supporter
    supporter = Supporter.query.get(supporter_id)
    if not supporter:
        return jsonify({"msg": "Supporter not found"}), 404
        
    is_sabi_kan = False
    for assignment in supporter.job_assignments:
        if assignment.job_title and (assignment.job_title.title_name == 'サービス管理責任者' or assignment.job_title.is_qualified_role):
            is_sabi_kan = True
            break
            
    if not is_sabi_kan:
        return jsonify({"msg": "Permission denied: サービス管理責任者 (Service Manager) role is required to activate a plan."}), 403
    
    if not consent_log_id:
        return jsonify({"msg": "Missing consent_log_id"}), 400
        
    try:
        from datetime import date
        final_plan = support_plan_service.finalize_and_activate_plan(
            plan_id=plan_id,
            consent_log_id=consent_log_id
        )
        final_plan.activated_at = date.today()
        db.session.commit()
        
        return jsonify({
            "msg": "Plan activated successfully",
            "plan_id": final_plan.id,
            "status": final_plan.plan_status
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Activation failed: {e}"}), 500


# -------------------------------------------------------------------
# 5. 目標の一括保存 API
# -------------------------------------------------------------------

@plans_bp.route('/<int:plan_id>/goals', methods=['PUT'])
@jwt_required()
def record_goals(plan_id):
    """
    計画の目標ツリー（長期・短期・個別）を一括で保存・更新する。
    DRAFT 状態の計画のみ編集可能（ガードレール）。
    """
    plan = db.session.get(SupportPlan, plan_id)
    if not plan:
        return jsonify({"msg": "SupportPlan not found"}), 404
        
    if plan.plan_status != 'DRAFT':
        return jsonify({"msg": "Only DRAFT plans can be edited"}), 400

    data = request.get_json()
    long_term_goals_data = data.get('long_term_goals', [])

    try:
        from backend.app.models import LongTermGoal, ShortTermGoal, IndividualSupportGoal
        # MVP方針: 既存の目標ツリーを一旦クリアして再構築する
        # 将来的には差分更新や変更履歴（監査ログ）に対応することを想定したプレイスホルダー
        for ltg in plan.long_term_goals:
            db.session.delete(ltg)
        db.session.flush()

        for ltg_item in long_term_goals_data:
            new_ltg = LongTermGoal(
                plan_id=plan_id,
                description=ltg_item.get('description', ''),
                challenges=ltg_item.get('challenges'),
                target_period_start=plan.plan_start_date,
                target_period_end=plan.plan_end_date
            )
            db.session.add(new_ltg)
            db.session.flush()

            for stg_item in ltg_item.get('short_term_goals', []):
                new_stg = ShortTermGoal(
                    long_term_goal_id=new_ltg.id,
                    description=stg_item.get('description', ''),
                    target_period_start=plan.plan_start_date,
                    target_period_end=plan.plan_end_date
                )
                db.session.add(new_stg)
                db.session.flush()

                for ig_item in stg_item.get('individual_goals', []):
                    new_ig = IndividualSupportGoal(
                        short_term_goal_id=new_stg.id,
                        concrete_goal=ig_item.get('concrete_goal', ''),
                        user_commitment=ig_item.get('user_commitment', '未記入'),
                        support_actions=ig_item.get('support_actions', '未記入'),
                        service_type=ig_item.get('service_type', 'TRAINING'),
                        is_facility_in_deemed=ig_item.get('is_facility_in_deemed', False),
                        is_work_preparation_positioning=ig_item.get('is_work_preparation_positioning', False)
                    )
                    db.session.add(new_ig)
        
        db.session.commit()
        return jsonify({"msg": "Goals updated successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Failed to update goals: {e}"}), 500


# -------------------------------------------------------------------
# 6. 現行成案から次期原案を作成するクローン API
# -------------------------------------------------------------------

@plans_bp.route('/<int:plan_id>/create-next-draft', methods=['POST'])
@jwt_required()
def create_next_draft(plan_id):
    """
    有効な計画から、目標ツリーをコピーして次期 DRAFT 計画を作成する。
    """
    from datetime import date, timedelta
    
    old_plan = db.session.get(SupportPlan, plan_id)
    if not old_plan:
        return jsonify({"msg": "Plan not found"}), 404

    try:
        from backend.app.models import LongTermGoal, ShortTermGoal, IndividualSupportGoal
        
        # 次期計画の期間設定
        start_date = date.today()
        if old_plan.plan_end_date:
            start_date = old_plan.plan_end_date + timedelta(days=1)
        end_date = start_date + timedelta(days=90)

        # 新規 DRAFT 計画の作成
        new_plan = SupportPlan(
            user_id=old_plan.user_id,
            plan_version=old_plan.plan_version + 1,
            plan_status='DRAFT',
            plan_start_date=start_date,
            plan_end_date=end_date,
            based_on_plan_id=old_plan.id,
            holistic_support_policy_id=old_plan.holistic_support_policy_id
        )
        db.session.add(new_plan)
        db.session.flush()

        # 目標の複製
        for old_ltg in old_plan.long_term_goals:
            new_ltg = LongTermGoal(
                plan_id=new_plan.id,
                description=old_ltg.description,
                challenges=old_ltg.challenges,
                target_period_start=start_date,
                target_period_end=end_date
            )
            db.session.add(new_ltg)
            db.session.flush()

            for old_stg in old_ltg.short_term_goals:
                new_stg = ShortTermGoal(
                    long_term_goal_id=new_ltg.id,
                    description=old_stg.description,
                    target_period_start=start_date,
                    target_period_end=end_date
                )
                db.session.add(new_stg)
                db.session.flush()

                for old_ig in old_stg.individual_goals:
                    new_ig = IndividualSupportGoal(
                        short_term_goal_id=new_stg.id,
                        concrete_goal=old_ig.concrete_goal,
                        user_commitment=old_ig.user_commitment,
                        support_actions=old_ig.support_actions,
                        service_type=old_ig.service_type,
                        is_facility_in_deemed=old_ig.is_facility_in_deemed,
                        is_work_preparation_positioning=old_ig.is_work_preparation_positioning
                    )
                    db.session.add(new_ig)

        db.session.commit()
        return jsonify({
            "msg": "Next draft plan created successfully from active plan",
            "plan_id": new_plan.id,
            "status": new_plan.plan_status
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Cloning plan failed: {e}"}), 500


# -------------------------------------------------------------------
# 7. 計画詳細取得 API
# -------------------------------------------------------------------

@plans_bp.route('/<int:plan_id>', methods=['GET'])
@jwt_required()
def get_plan_details(plan_id):
    """
    特定の個別支援計画の詳細（目標ツリー、方針等を含む）を取得する。
    """
    plan = db.session.get(SupportPlan, plan_id)
    if not plan:
        return jsonify({"msg": "SupportPlan not found"}), 404
        
    from backend.app.api.users.user_plans_api import _serialize_active_plan
    try:
        data = _serialize_active_plan(plan)
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"msg": f"Failed to serialize plan: {e}"}), 500


# -------------------------------------------------------------------
# 8. 計画本体の更新 API
# -------------------------------------------------------------------

@plans_bp.route('/<int:plan_id>', methods=['PUT'])
@jwt_required()
def update_plan(plan_id):
    """
    計画の基本情報（期間・方針）を更新する。
    DRAFT 状態の計画のみ編集可能（ガードレール）。
    """
    plan = db.session.get(SupportPlan, plan_id)
    if not plan:
        return jsonify({"msg": "SupportPlan not found"}), 404
        
    if plan.plan_status != 'DRAFT':
        return jsonify({"msg": "Only DRAFT plans can be edited"}), 400

    data = request.get_json()
    plan_start_date = data.get('plan_start_date')
    plan_end_date = data.get('plan_end_date')
    user_intention_content = data.get('user_intention_content')
    support_policy_content = data.get('support_policy_content')

    from datetime import datetime, date
    from backend.app.models import HolisticSupportPolicy
    
    try:
        if plan_start_date:
            plan.plan_start_date = datetime.strptime(plan_start_date, "%Y-%m-%d").date()
        if plan_end_date:
            plan.plan_end_date = datetime.strptime(plan_end_date, "%Y-%m-%d").date()
            
        if user_intention_content or support_policy_content:
            if plan.holistic_policy:
                plan.holistic_policy.user_intention_content = user_intention_content or plan.holistic_policy.user_intention_content
                plan.holistic_policy.support_policy_content = support_policy_content or plan.holistic_policy.support_policy_content
            else:
                policy = HolisticSupportPolicy(
                    user_id=plan.user_id,
                    effective_date=date.today(),
                    user_intention_content=user_intention_content or "本人の意向未記入",
                    support_policy_content=support_policy_content or "支援の方針未記入"
                )
                db.session.add(policy)
                db.session.flush()
                plan.holistic_support_policy_id = policy.id
                
        db.session.commit()
        return jsonify({"msg": "Plan updated successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Failed to update plan: {e}"}), 500


@plans_bp.route('/<int:plan_id>/approve', methods=['POST'])
@jwt_required()
def approve_plan(plan_id):
    """
    本人同席の会議（PERSON_CENTERED_MEETING）が実施されていることを確認した上で、
    計画原案を承認し、説明・同意待ち（PENDING_CONSENT）ステータスへ移行する。
    """
    _, supporter_id = parse_jwt_identity(get_jwt_identity())
    
    # 承認者はサビ管である必要があり、supporter_id がサビ管であることを検証する
    from backend.app.models import Supporter
    supporter = db.session.get(Supporter, supporter_id)
    if not supporter:
        return jsonify({"msg": "Supporter not found"}), 404
        
    is_sabi_kan = False
    for assignment in supporter.job_assignments:
        if assignment.job_title and (assignment.job_title.title_name == 'サービス管理責任者' or assignment.job_title.is_qualified_role):
            is_sabi_kan = True
            break
            
    if not is_sabi_kan:
        return jsonify({"msg": "Permission denied: サービス管理責任者 (Service Manager) role is required to approve a plan."}), 403

    plan = db.session.get(SupportPlan, plan_id)
    if not plan:
        return jsonify({"msg": "SupportPlan not found"}), 404
        
    if plan.plan_status != 'DRAFT':
        return jsonify({"msg": "Only DRAFT plans can be approved"}), 400

    try:
        from backend.app.models import CaseConferenceLog
        
        # すべての長期目標で「課題・相談内容」が入力されているか検証（承認時ガードレール）
        if not plan.long_term_goals:
            return jsonify({"msg": "長期目標が設定されていません。計画の承認には目標の設定が必須です。"}), 400

        for ltg in plan.long_term_goals:
            if not ltg.challenges or not ltg.challenges.strip():
                return jsonify({"msg": "すべての長期目標において「課題・相談内容」の入力が必要です。課題が未入力の目標があります。"}), 400

        # 計画に紐づく本人同席の会議（PERSON_CENTERED_MEETING）が実施されていることを確認
        meeting = CaseConferenceLog.query.filter_by(
            support_plan_id=plan_id,
            conference_type='PERSON_CENTERED_MEETING',
            user_participated=True
        ).first()
        
        if not meeting:
            return jsonify({"msg": "本人同席会議（PERSON_CENTERED_MEETING）が実施されていません。計画の承認には本人同席の会議が必須条件です。"}), 400

        # 会議記録から決定事項や日時を引き継ぐ
        conference_log = support_plan_service.log_support_conference_and_approve(
            plan_id=plan_id,
            sabikan_id=supporter_id,
            conference_date=meeting.conference_datetime,
            content=meeting.concern_summary + "\n\n決定事項:\n" + meeting.agreed_action,
            user_participated=True
        )
        db.session.commit()
        
        return jsonify({
            "msg": "Plan approved successfully",
            "plan_id": plan_id,
            "conference_log_id": conference_log.id
        }), 200

    except ValidationError as e:
        db.session.rollback()
        return jsonify({"msg": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        import logging
        logging.getLogger(__name__).exception(e)
        return jsonify({"msg": f"Failed to approve plan: {e}"}), 500


@plans_bp.route('/<int:plan_id>/deviation-reason', methods=['PUT'])
@jwt_required()
def update_deviation_reason(plan_id):
    """
    計画のタイムライン逸脱（遡及作成など）に対する理由を登録・更新する。
    """
    plan = db.session.get(SupportPlan, plan_id)
    if not plan:
        return jsonify({"msg": "SupportPlan not found"}), 404

    data = request.get_json()
    reason = data.get('timeline_deviation_reason')
    
    if not reason or len(reason.strip()) < 10:
        return jsonify({"msg": "逸脱理由は10文字以上で入力してください。"}), 400

    try:
        plan.timeline_deviation_reason = reason.strip()
        db.session.commit()
        return jsonify({"msg": "Timeline deviation reason updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Failed to update deviation reason: {e}"}), 500