# app/api/daily_log_routes.py

from flask import Blueprint, request, jsonify
from app.extensions import db
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from flask_jwt_extended import get_jwt_identity # 必要に応じて get_jwt_identity は残す
from app.models.core import User, Supporter, DailyLog 
from app.models.master import AttendanceStatusMaster
from app.models.audit_log import SystemLog
from app.models.plan import SpecificGoal
from app.api.auth_routes import role_required # 必要に応じてインポート

# Blueprintを作成
daily_log_bp = Blueprint('daily_log', __name__)

# ======================================================
# 4. 日報登録 API (POST /api/daily_logs)
# ======================================================
@daily_log_bp.route('/daily_logs', methods=['POST'])
def create_daily_log():
    data = request.get_json()
    
    # 必須フィールドの簡易バリデーション (specific_goal_id は optional とする)
    required_fields = ['user_id', 'supporter_id', 'activity_date', 'attendance_status_name']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "必須フィールド (利用者ID, 職員ID, 日付, 勤怠ステータス) が不足しています。"}), 400

    try:
        # 1. 外部キーの存在確認
        user = User.query.get(data['user_id'])
        supporter = Supporter.query.get(data['supporter_id'])
        
        if not user or not supporter:
            return jsonify({"error": "利用者IDまたは職員IDが存在しません。"}), 400
        
        # 2. マスターデータのルックアップ
        attendance_status = AttendanceStatusMaster.query.filter_by(
            name=data['attendance_status_name']
        ).first()
        if not attendance_status:
            return jsonify({"error": f"無効な勤怠ステータス名です: {data['attendance_status_name']}"}), 400

        # ★ 3. SpecificGoal の存在チェック（連携強化） ★
        specific_goal_id = data.get('specific_goal_id')
        if specific_goal_id:
            if SpecificGoal.query.get(specific_goal_id) is None:
                return jsonify({"error": f"具体的な目標ID {specific_goal_id} は存在しません。"}), 400
            
        activity_date = datetime.strptime(data['activity_date'], '%Y-%m-%d').date()

        # 4. 新しい DailyLog オブジェクトを作成
        new_log = DailyLog(
            user_id=data['user_id'],
            supporter_id=data['supporter_id'],
            activity_date=activity_date,
            attendance_status_id=attendance_status.id,
            specific_goal_id=specific_goal_id, # ★ 新規追加 ★
            
            # ... (その他のフィールド) ...
            mood_hp=data.get('mood_hp'), 
            mood_mp=data.get('mood_mp'), 
            activity_summary=data.get('activity_summary'),
            user_voice=data.get('user_voice'),            
            supporter_insight=data.get('supporter_insight'),
            remarks=data.get('remarks')
        )
        
        # 5. データベースに保存
        db.session.add(new_log)
        db.session.commit()
        
        return jsonify({
            "message": "日報を正常に記録しました。",
            "log_id": new_log.id,
            "user_name": f"{user.last_name} {user.first_name}"
        }), 201

    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "データベース制約違反が発生しました。"}), 500
    except ValueError:
        db.session.rollback()
        return jsonify({"error": "日付または数値の形式が正しくありません。"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"サーバーエラーが発生しました: {str(e)}"}), 500

# ======================================================
# 3. 日報削除 API (DELETE /api/daily_logs/<log_id>)
# ======================================================
@daily_log_bp.route('/daily_logs/<int:log_id>', methods=['DELETE'])
@role_required(['支援員', 'サービス管理責任者', '管理者']) 
def delete_daily_log(log_id):
    # ログイン中の職員IDを取得
    supporter_id = get_jwt_identity()

    try:
        daily_log = DailyLog.query.get_or_404(log_id)
        
        # 1. SystemLog に削除の事実を記録
        db.session.add(SystemLog(
            supporter_id=supporter_id,
            target_user_id=daily_log.user_id,
            action="daily_log_deletion",
            details=f"日報ID {log_id} (利用者ID {daily_log.user_id} の {daily_log.activity_date.isoformat()} の記録) が削除されました。",
            target_plan_id=None # 日報は計画に直接紐づかないためNone
        ))
        
        # 2. DailyLog をデータベースから削除
        db.session.delete(daily_log)
        db.session.commit()
        
        return jsonify({"message": f"日報ID {log_id} を正常に削除しました。監査ログに記録されました。"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"日報の削除中にサーバーエラーが発生しました: {str(e)}"}), 500
