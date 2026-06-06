# backend/app/api/action_items.py
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from datetime import date, datetime
from backend.app import db
from backend.app.models import (
    User, SupportPlan, DailyLog, CaseConferenceLog, StatusMaster
)

action_items_bp = Blueprint('action_items', __name__, url_prefix='/api/action-items')

@action_items_bp.route('', methods=['GET'])
@jwt_required()
def get_action_items():
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    items = []
    
    # 1. 未完了日報 (DRAFT)
    draft_logs = DailyLog.query.filter_by(log_status='DRAFT').all()
    for log in draft_logs:
        user_name = log.user.display_name if log.user else "不明"
        items.append({
            "type": "daily_log",
            "category_label": "日報",
            "severity": "medium",
            "user_id": log.user_id,
            "user_name": user_name,
            "title": f"{user_name}さんの日報が未完了（下書き）です",
            "description": f"{log.log_date}の日報が下書き状態のままになっています。完了させてください。"
        })
        
    # 2. 同意待ち計画 (PENDING_CONSENT)
    pending_plans = SupportPlan.query.filter_by(plan_status='PENDING_CONSENT').all()
    for plan in pending_plans:
        user_name = plan.user.display_name if plan.user else "不明"
        items.append({
            "type": "approval",
            "category_label": "承認待ち",
            "severity": "high",
            "user_id": plan.user_id,
            "user_name": user_name,
            "title": f"{user_name}さんの個別支援計画が同意待ちです",
            "description": f"{plan.plan_start_date}〜{plan.plan_end_date}の計画の署名・同意が得られていません。"
        })
        
    # 3. 未作成計画 (利用中だがACTIVEな計画がない)
    # TODO: replace hardcoded status_id with UserStatusMaster code lookup
    # 暫定で status.name = '利用中' のマスターIDを使用し、なければデフォルト 2 とする
    active_status = StatusMaster.query.filter_by(name='利用中').first()
    active_status_id = active_status.id if active_status else 2
    
    users = User.query.filter(User.status_id == active_status_id, User.deleted_at.is_(None)).all()
    for user in users:
        active_plan = SupportPlan.query.filter_by(user_id=user.id, plan_status='ACTIVE').first()
        if not active_plan:
            items.append({
                "type": "approval",
                "category_label": "承認待ち",
                "severity": "high",
                "user_id": user.id,
                "user_name": user.display_name,
                "title": f"{user.display_name}さんの個別支援計画が未作成です",
                "description": "サービス利用中ですが、有効な個別支援計画が登録されていません。早急に計画を作成してください。"
            })
            
    # 4. モニタリング期限超過 / 間近
    active_plans = SupportPlan.query.filter_by(plan_status='ACTIVE').all()
    for plan in active_plans:
        user_name = plan.user.display_name if plan.user else "不明"
        if plan.plan_end_date:
            # TODO: replace plan_end_date fallback with formal monitoring schedule
            if plan.plan_end_date < today:
                items.append({
                    "type": "monitoring",
                    "category_label": "モニタリング",
                    "severity": "high",
                    "user_id": plan.user_id,
                    "user_name": user_name,
                    "title": f"{user_name}さんのモニタリング期限が超過しています",
                    "description": f"計画終了日（{plan.plan_end_date}）を過ぎていますが、モニタリングが実施されていません。"
                })
            elif (plan.plan_end_date - today).days <= 30:
                items.append({
                    "type": "monitoring",
                    "category_label": "モニタリング",
                    "severity": "medium",
                    "user_id": plan.user_id,
                    "user_name": user_name,
                    "title": f"{user_name}さんのモニタリング期限が近づいています",
                    "description": f"計画終了日（{plan.plan_end_date}）まで残り{(plan.plan_end_date - today).days}日です。モニタリングの準備をしてください。"
                })
                
    # 5. 本日のケース会議
    conferences = CaseConferenceLog.query.filter(
        CaseConferenceLog.conference_datetime >= today_start,
        CaseConferenceLog.conference_datetime <= today_end,
        CaseConferenceLog.deleted_at.is_(None)
    ).all()
    for conf in conferences:
        user_name = conf.user.display_name if conf.user else "不明"
        items.append({
            "type": "case_conference",
            "category_label": "ケース会議",
            "severity": "low",
            "user_id": conf.user_id,
            "user_name": user_name,
            "title": f"{user_name}さんのケース会議が本日予定されています",
            "description": f"{conf.conference_datetime.strftime('%H:%M')}よりケース会議が開催されます。内容を確認してください。"
        })
        
    return jsonify({"items": items}), 200
