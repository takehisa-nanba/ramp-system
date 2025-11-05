# app/api/support_plan_routes.py

from flask import Blueprint, request, jsonify
from app.extensions import db
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from flask_jwt_extended import get_jwt_identity, jwt_required 
from app.api.auth_routes import role_required

# ★ モデルの配置変更に対応したインポートに修正 ★
# plan.py に移動したモデル
from app.models.plan import SupportPlan, ShortTermGoal, SpecificGoal
# core.py にあるモデル
from app.models.core import User, Supporter, DailyLog
# master.py に残ったモデル
from app.models.master import StatusMaster, ServiceTemplate 
# audit_log.py に移動したモデル
# SystemLog は audit_log.py からインポート
from app.models.audit_log import SystemLog
# Blueprintを作成
support_plan_bp = Blueprint('support_plan', __name__)

# ======================================================
# 1. 個別支援計画作成 API (POST /api/support_plans)
# ======================================================
@support_plan_bp.route('/support_plans', methods=['POST'])
@role_required(['サービス管理責任者', '管理者']) 
def create_support_plan():
    data = request.get_json()
    
    # 認証トークンから現在のログインユーザーID（サビ管ID）を取得
    sabikan_id = int(get_jwt_identity()) # JWTから取得したIDはstrなのでintに変換

    # 必須フィールドチェック
    required_fields = ['user_id', 'main_goal', 'start_date', 'end_date', 'short_term_goals']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "必須フィールドが不足しています。"}), 400

    try:
        # 1. 利用者存在チェック
        if User.query.get(data['user_id']) is None:
            return jsonify({"error": f"利用者ID {data['user_id']} は存在しません。"}), 400
        
        # 2. StatusMaster から 'Draft' ステータスIDを取得
        draft_status = StatusMaster.query.filter_by(category='plan', name='Draft').first()
        if not draft_status:
            return jsonify({"error": "マスタデータ 'Draft' が不足しています。"}), 500

        # 3. SupportPlan (長期目標) オブジェクトの作成
        new_plan = SupportPlan(
            user_id=data['user_id'],
            sabikan_id=sabikan_id, # ログイン中のサビ管IDを責任者として記録
            status_id=draft_status.id,
            plan_date=datetime.utcnow().date(),
            start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date(),
            end_date=datetime.strptime(data['end_date'], '%Y-%m-%d').date(),
            main_goal=data['main_goal'],
            
            # 支援の質向上のための詳細
            comprehensive_policy=data.get('comprehensive_policy'),
            user_strengths=data.get('user_strengths'),
            user_challenges=data.get('user_challenges')
        )
        db.session.add(new_plan)
        db.session.flush() # IDを取得するための一時コミット

        # 4. ShortTermGoal と SpecificGoal (3階層) の処理
        for st_goal_data in data['short_term_goals']:
            # ShortTermGoal オブジェクトの作成
            new_st_goal = ShortTermGoal(
                support_plan_id=new_plan.id,
                short_goal=st_goal_data['short_goal'],
                # モデルのstart_date/end_dateにデータを格納
                start_date=datetime.strptime(st_goal_data['st_start_date'], '%Y-%m-%d').date(), 
                end_date=datetime.strptime(st_goal_data['st_end_date'], '%Y-%m-%d').date() 
            )
            db.session.add(new_st_goal)
            db.session.flush()

            # SpecificGoal (具体的タスク) の処理
            for specific_task_data in st_goal_data.get('specific_tasks', []):
                new_specific_goal = SpecificGoal(
                    short_term_goal_id=new_st_goal.id,
                    task_name=specific_task_data['task_name'],
                    priority=specific_task_data.get('priority'),
                    template_id=specific_task_data.get('template_id'),
                    responsible_supporter_id=specific_task_data.get('responsible_supporter_id')
                )
                db.session.add(new_specific_goal)

        # 5. 最終コミット
        db.session.commit()
        
        # 6. 成功レスポンスを返す
        return jsonify({
            "message": "個別支援計画（3階層）を Draft 状態で作成しました。",
            "plan_id": new_plan.id,
            "sabikan_id": sabikan_id
        }), 201

    except ValueError:
        db.session.rollback()
        return jsonify({"error": "日付の形式が正しくありません (YYYY-MM-DD を使用してください)。"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"サーバーエラーが発生しました: {str(e)}"}), 500
    
# ======================================================
# 2. 個別支援計画詳細取得 API (GET /api/support_plans/<id>)
# ======================================================
@support_plan_bp.route('/support_plans/<int:plan_id>', methods=['GET'])
@jwt_required() 
def get_support_plan_detail(plan_id):
    # 1. SupportPlan (長期目標) とメタデータの取得
    plan_query = db.session.execute(
        db.select(
            SupportPlan, 
            StatusMaster.name.label('status_name'),
            Supporter.last_name.label('sabikan_last_name')
        )
        .join(StatusMaster, SupportPlan.status_id == StatusMaster.id)
        .join(Supporter, SupportPlan.sabikan_id == Supporter.id)
        .where(SupportPlan.id == plan_id)
    ).first()

    if not plan_query:
        return jsonify({"error": f"計画ID {plan_id} のレコードは見つかりません。"}), 404

    plan_data = plan_query[0]
    
    # 2. ShortTermGoal (短期目標) と SpecificGoal (タスク) の階層データを取得
    st_goals_query = db.session.execute(
        db.select(ShortTermGoal)
        .where(ShortTermGoal.support_plan_id == plan_id)
        .order_by(ShortTermGoal.id.asc())
    ).scalars().all()

    st_goals_list = []
    for st_goal in st_goals_query:
        # ShortTermGoal に紐づく SpecificGoal を取得
        specific_goals_query = db.session.execute(
            db.select(
                SpecificGoal,
                Supporter.last_name.label('responsible_supporter_name')
            )
            .outerjoin(Supporter, SpecificGoal.responsible_supporter_id == Supporter.id)
            .where(SpecificGoal.short_term_goal_id == st_goal.id)
            .order_by(SpecificGoal.priority.asc())
        ).all()

        specific_goals_list = []
        for sg_row in specific_goals_query:
            sg = sg_row[0]
            specific_goals_list.append({
                "id": sg.id,
                "task_name": sg.task_name,
                "priority": sg.priority,
                "responsible_supporter": sg_row.responsible_supporter_name,
                "is_custom_task": sg.is_custom_task,
                "template_id": sg.template_id
            })

        st_goals_list.append({
            "id": st_goal.id,
            "short_goal": st_goal.short_goal,
            "start_date": st_goal.start_date.isoformat(),
            "end_date": st_goal.end_date.isoformat(),
            "specific_tasks": specific_goals_list
        })

    # 3. 最終結果の統合と整形
    response = {
        "id": plan_data.id,
        "user_id": plan_data.user_id,
        "status": plan_query.status_name,
        "sabikan_name": f"{plan_query.sabikan_last_name} 氏",
        "period": {
            "start": plan_data.start_date.isoformat(),
            "end": plan_data.end_date.isoformat()
        },
        "main_goal": plan_data.main_goal,
        "comprehensive_policy": plan_data.comprehensive_policy,
        "user_strengths": plan_data.user_strengths,
        "user_challenges": plan_data.user_challenges,
        "user_consent_date": plan_data.user_consent_date.isoformat() 
                             if plan_data.user_consent_date else None,         
        "short_term_goals": st_goals_list
    }

    return jsonify(response), 200

# ======================================================
# 3. 計画提出 API (POST /api/support_plans/<id>/submit)
# ======================================================
@support_plan_bp.route('/support_plans/<int:plan_id>/submit', methods=['POST'])
@jwt_required() 
def submit_support_plan(plan_id):
    current_supporter_id = get_jwt_identity()

    try:
        plan = db.session.get(SupportPlan, plan_id)
        if not plan:
            return jsonify({"error": f"計画ID {plan_id} のレコードは見つかりません。"}), 404
        
        # 1. 必要なステータスIDを取得
        draft_status = StatusMaster.query.filter_by(category='plan', name='Draft').first()
        pending_status = StatusMaster.query.filter_by(category='plan', name='Pending_Approval').first()
        
        if not draft_status or not pending_status:
            return jsonify({"error": "マスタデータ (Draft/Pending_Approval) が不足しています。"}), 500
        
        # 2. ステータスチェック: Draft 状態からのみ提出を許可
        if plan.status_id != draft_status.id:
            current_status_name = StatusMaster.query.get(plan.status_id).name
            return jsonify({"error": f"計画はすでに提出済みか、承認待ちではありません (現在のステータス: {current_status_name})。"}), 400

        # 3. ステータスの更新と監査ログの記録
        plan.status_id = pending_status.id
        
        # 監査ログ
        db.session.add(SystemLog(
            action='plan_submit',
            supporter_id=int(current_supporter_id),
            target_user_id=plan.user_id,
            target_plan_id=plan_id,
            details=f"計画ID {plan_id} が承認待ちとして提出されました。"
        ))
        
        db.session.commit()

        return jsonify({
            "message": "個別支援計画を提出しました。管理者/サビ管の承認待ちです。",
            "plan_id": plan_id,
            "new_status": pending_status.name
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"サーバーエラーが発生しました: {str(e)}"}), 500

# ======================================================
# 4. 計画承認 API (POST /api/support_plans/<id>/approve)
# ======================================================
@support_plan_bp.route('/support_plans/<int:plan_id>/approve', methods=['POST'])
@role_required(['サービス管理責任者', '管理者']) 
def approve_support_plan(plan_id):
    current_approver_id = int(get_jwt_identity())

    try:
        plan = db.session.get(SupportPlan, plan_id)
        if not plan:
            return jsonify({"error": f"計画ID {plan_id} のレコードは見つかりません。"}), 404

        # 1. 必要なステータスIDを取得
        pending_status = StatusMaster.query.filter_by(category='plan', name='Pending_Approval').first()
        approved_status = StatusMaster.query.filter_by(category='plan', name='Approved_Active').first()
        
        if not pending_status or not approved_status:
            return jsonify({"error": "マスタデータ (Pending_Approval/Approved_Active) が不足しています。"}), 500
        
        # 2. ステータスチェック: Pending_Approval 状態からのみ承認を許可
        if plan.status_id != pending_status.id:
            current_status_name = StatusMaster.query.get(plan.status_id).name
            return jsonify({"error": f"計画は承認待ち状態ではありません (現在のステータス: {current_status_name})。"}), 400

        # 3. ステータスの更新と監査ログの記録
        plan.status_id = approved_status.id
        # plan.approver_id = current_approver_id # ※ approver_id カラムがないためコメントアウト
        
        # 監査ログ
        db.session.add(SystemLog(
            action='plan_approved',
            supporter_id=current_approver_id,
            target_user_id=plan.user_id,
            target_plan_id=plan_id,
            details=f"計画ID {plan_id} が職員ID {current_approver_id} によって承認されました。"
        ))
        
        db.session.commit()

        return jsonify({
            "message": "個別支援計画を承認しました。本人同意ステップへ移行します。",
            "plan_id": plan_id,
            "new_status": approved_status.name
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"サーバーエラーが発生しました: {str(e)}"}), 500


# ======================================================
# 5. 計画差し戻し API (POST /api/support_plans/<id>/reject)
# ======================================================
@support_plan_bp.route('/support_plans/<int:plan_id>/reject', methods=['POST'])
@role_required(['サービス管理責任者', '管理者'])
def reject_support_plan(plan_id):
    data = request.get_json()
    rejection_reason = data.get('reason', '管理者による修正指示')
    current_supporter_id = int(get_jwt_identity())

    try:
        plan = db.session.get(SupportPlan, plan_id)
        if not plan:
            return jsonify({"error": f"計画ID {plan_id} のレコードは見つかりません。"}), 404

        # 1. 必要なステータスIDを取得
        pending_status = StatusMaster.query.filter_by(category='plan', name='Pending_Approval').first()
        draft_status = StatusMaster.query.filter_by(category='plan', name='Draft').first()
        
        if not pending_status or not draft_status:
            return jsonify({"error": "マスタデータ (Pending_Approval/Draft) が不足しています。"}), 500
        
        # 2. ステータスチェック: Pending_Approval 状態からのみ差し戻しを許可
        if plan.status_id != pending_status.id:
            current_status_name = StatusMaster.query.get(plan.status_id).name
            return jsonify({"error": f"計画は承認待ち状態ではありません (現在のステータス: {current_status_name})。"}), 400
        
        # 3. ステータスの更新と監査ログの記録
        plan.status_id = draft_status.id
        
        # 監査ログ
        db.session.add(SystemLog(
            action='plan_rejected',
            supporter_id=current_supporter_id,
            target_user_id=plan.user_id,
            target_plan_id=plan_id,
            details=f"計画ID {plan_id} が差し戻されました。理由: {rejection_reason[:100]}..."
        ))
        
        db.session.commit()

        return jsonify({
            "message": "個別支援計画を差し戻し（Draft状態に戻しました）。",
            "plan_id": plan_id,
            "new_status": draft_status.name,
            "reason": rejection_reason
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"サーバーエラーが発生しました: {str(e)}"}), 500
    
# ======================================================
# 6. 本人同意（電子サイン）API (POST /api/support_plans/<id>/consent)
# ======================================================
@support_plan_bp.route('/support_plans/<int:plan_id>/consent', methods=['POST'])
@jwt_required() 
@role_required(['サービス管理責任者', '管理者']) # 同席職員の権限チェック
def consent_support_plan(plan_id):
    data = request.get_json()
    user_id = data.get('user_id')
    pin_code = data.get('pin_code')

    if not user_id or not pin_code:
        return jsonify({"error": "利用者IDとPINコードを入力してください。"}), 400

    try:
        plan = db.session.get(SupportPlan, plan_id)
        user = db.session.get(User, user_id)
        
        if not plan or not user:
            return jsonify({"error": "計画または利用者が見つかりません。"}), 404
        
        # 1. 計画のステータスチェック（承認済み状態か）
        approved_status = StatusMaster.query.filter_by(category='plan', name='Approved_Active').first()
        if not approved_status:
             return jsonify({"error": "マスタデータ (Approved_Active) が不足しています。"}), 500
        
        if plan.status_id != approved_status.id:
            current_status_name = StatusMaster.query.get(plan.status_id).name
            return jsonify({"error": f"計画は管理者によって承認された状態ではありません (現在のステータス: {current_status_name})。"}), 400
        
        # 2. 計画の利用者IDと照合
        if plan.user_id != user_id:
            return jsonify({"error": "この計画は指定された利用者IDと紐づいていません。"}), 403
            
        # 3. PINコード認証（電子サイン）
        # ※ Userモデルに check_pin メソッドが必要だが、ここではロジックの意図を維持
        # if not user.check_pin(pin_code):
        #     return jsonify({"error": "PINコードが無効です。本人確認に失敗しました。"}), 401
        
        # 暫定的にPINコードが '1234' なら認証成功とする (check_pinがないため)
        if pin_code != '1234':
             return jsonify({"error": "PINコードが無効です。本人確認に失敗しました。"}), 401


        # 4. 同意と確定
        plan.user_consent_date = datetime.utcnow()
        # 計画は Approved_Active のまま実行フェーズへ

        # 5. 監査証跡の記録
        supporter_id = int(get_jwt_identity()) # 同席したサビ管のIDを取得

        consent_log = SystemLog(
        action='plan_consent',
        supporter_id=supporter_id,
        target_user_id=user_id,
        target_plan_id=plan_id,
        details=f"利用者ID {user_id} が計画ID {plan_id} に電子同意しました。"
        )
        db.session.add(consent_log)
        
        db.session.commit()

        return jsonify({
            "message": "個別支援計画に利用者が同意し、正式に実行が開始されました。",
            "plan_id": plan_id,
            "consent_date": plan.user_consent_date.isoformat()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"サーバーエラーが発生しました: {str(e)}"}), 500

