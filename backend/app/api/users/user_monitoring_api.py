"""
GET /api/users/<user_id>/monitoring-reports
利用者のモニタリング情報（次回期限、対象計画、過去の記録）を返す。
"""
from flask import jsonify
from flask_jwt_extended import jwt_required
from datetime import date
from backend.app import db
from backend.app.models import User, SupportPlan, MonitoringReport, Supporter
from . import users_bp


@users_bp.route('/<int:user_id>/monitoring-reports', methods=['GET'])
@jwt_required()
def get_user_monitoring_reports(user_id: int):
    """
    利用者のモニタリング情報を取得する。
    - next_monitoring_due: 次回モニタリング期限（暫定: plan_end_date）
    - active_plan_summary: モニタリング対象の計画概要
    - history: 過去のモニタリングレポート一覧
    """
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({
            "success": False,
            "error": {
                "code": "NOT_FOUND",
                "message": "利用者が見つかりません。"
            }
        }), 404

    active_plan = user.support_plans.filter_by(plan_status='ACTIVE').first()

    # TODO: replace plan_end_date fallback with formal monitoring schedule field
    # 正式な monitoring_schedule テーブルが実装されたら、そちらを参照する。
    # 現時点では ACTIVE計画の plan_end_date を next_monitoring_due として暫定表示する。
    next_monitoring_due = None
    active_plan_summary = None
    if active_plan:
        next_monitoring_due = active_plan.plan_end_date.isoformat() if active_plan.plan_end_date else None
        active_plan_summary = {
            "id": active_plan.id,
            "plan_version": active_plan.plan_version,
            "start_date": active_plan.plan_start_date.isoformat() if active_plan.plan_start_date else None,
            "end_date": active_plan.plan_end_date.isoformat() if active_plan.plan_end_date else None,
            # 長期目標のタイトル（最初の1件）を計画の代表タイトルとして使用
            "primary_goal": active_plan.long_term_goals[0].description if active_plan.long_term_goals else None,
        }

    # 過去のモニタリングレポートを取得（有効計画に紐づくものを含む）
    # 利用者の全計画IDを取得してから、それに紐づくMonitoringReportを取得する
    all_plan_ids = [p.id for p in user.support_plans.all()]
    history = []
    if all_plan_ids:
        reports = MonitoringReport.query\
            .filter(MonitoringReport.support_plan_id.in_(all_plan_ids))\
            .filter(MonitoringReport.deleted_at.is_(None))\
            .order_by(MonitoringReport.report_date.desc())\
            .all()

        for r in reports:
            supporter = db.session.get(Supporter, r.supporter_id)
            supporter_name = supporter.display_name if supporter and hasattr(supporter, 'display_name') else f"ID:{r.supporter_id}"
            history.append({
                "id": r.id,
                "report_date": r.report_date.isoformat(),
                "monitoring_summary": r.monitoring_summary,
                "target_goal_progress_notes": r.target_goal_progress_notes,
                "support_plan_id": r.support_plan_id,
                "supporter_name": supporter_name,
            })

    return jsonify({
        "next_monitoring_due": next_monitoring_due,
        "active_plan_summary": active_plan_summary,
        "history": history,
    }), 200
