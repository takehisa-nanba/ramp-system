# app/api/attendance_routes.py (全文)

from flask import Blueprint, request, jsonify # ★ 必須のインポート ★
from app.extensions import db
from app.models import AttendancePlan, User, DailyLog
from app.api.auth_routes import role_required # RBACデコレーター
from datetime import datetime
from sqlalchemy.exc import IntegrityError

# Blueprintを作成
attendance_bp = Blueprint('attendance', __name__)

# ======================================================
# 1. 通所予定登録 API (POST /api/attendance/plans)
# ======================================================
@attendance_bp.route('attendance/plans', methods=['POST']) # ★ '/attendance/plans' -> '/plans' に修正 ★
@role_required(['支援員', 'サービス管理責任者', '管理者'])
def create_attendance_plan():
    data = request.get_json()
    
    # 必須フィールドのチェック
    required_fields = ['user_id', 'planned_date', 'planned_check_in']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "必須フィールド（user_id, planned_date, planned_check_in）が不足しています。"}), 400

    try:
        # ロジック（省略）
        user = User.query.get(data['user_id'])
        if not user:
            return jsonify({"error": f"利用者ID {data['user_id']} のレコードは見つかりません。"}), 404
        
        planned_date = datetime.strptime(data['planned_date'], '%Y-%m-%d').date()
        
        # 重複チェック (UniqueConstraintに頼ることも可能だが、明示的なチェックが親切)
        existing_plan = AttendancePlan.query.filter(
            AttendancePlan.user_id == data['user_id'],
            AttendancePlan.planned_date == planned_date
        ).first()
        if existing_plan:
            return jsonify({"error": f"利用者 {data['user_id']} は、{data['planned_date']} に既に予定が登録されています。"}), 409

        new_plan = AttendancePlan(
            user_id=data['user_id'],
            planned_date=planned_date,
            planned_check_in=data['planned_check_in'],
            planned_check_out=data.get('planned_check_out'),
            is_recurring=data.get('is_recurring', False),
            remarks=data.get('notes')
        )
        
        db.session.add(new_plan)
        db.session.commit()
        
        return jsonify({
            "message": f"利用者 {user.last_name} の {data['planned_date']} の通所予定を登録しました。",
            "plan_id": new_plan.id
        }), 201

    except ValueError:
        db.session.rollback()
        return jsonify({"error": "日付または時刻の形式が正しくありません (日付: YYYY-MM-DD, 時刻: HH:MM)。"}), 400
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "データベース制約違反が発生しました (例: 必須フィールドのNULL許容違反)。"}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"サーバーエラーが発生しました: {str(e)}"}), 500

# ======================================================
# 3. 利用者チェックイン API (POST /api/attendance/check_in)
# ======================================================
@attendance_bp.route('attendance/check_in', methods=['POST'])
# ※ 利用者専用認証が必要だが、ここでは職員トークンで user_id を渡す運用とする
@role_required(['支援員', 'サービス管理責任者', '管理者']) 
def check_in():
    data = request.get_json()
    user_id = data.get('user_id')
    current_time = datetime.utcnow()
    
    if not user_id:
        return jsonify({"error": "利用者IDが不足しています。"}), 400

    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": f"利用者ID {user_id} は存在しません。"}), 404

        today_date = current_time.date()
        
        # 1. 既に今日の打刻済み DailyLog が存在するかチェック
        existing_log = DailyLog.query.filter(
            DailyLog.user_id == user_id,
            DailyLog.activity_date == today_date
        ).first()

        if existing_log and existing_log.check_in_time:
            # 既にチェックイン済み
            return jsonify({"message": "既に本日の通所が記録されています。", "log_id": existing_log.id}), 200
        
        # 2. 新しい DailyLog レコードを作成 (または既存レコードを更新)
        if existing_log is None:
            new_log = DailyLog(
                user_id=user_id,
                activity_date=today_date,
                check_in_time=current_time,
                # 職員IDは後に別途記録されるか、ここでは暫定的にNULL
                attendance_status_id=1 # 暫定: '通所' ステータスIDを1と仮定
            )
            db.session.add(new_log)
            log_id = new_log.id
        else:
            # 既に欠席などのレコードがある場合、check_in_time を更新
            existing_log.check_in_time = current_time
            log_id = existing_log.id

        db.session.commit()
        
        return jsonify({
            "message": f"利用者 {user.last_name} の通所を記録しました。",
            "check_in_time": current_time.isoformat(),
            "log_id": log_id
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"サーバーエラーが発生しました: {str(e)}"}), 500

# ======================================================
# 4. 利用者チェックアウト API (POST /api/attendance/check_out)
# ======================================================
@attendance_bp.route('attendance/check_out', methods=['POST'])
@role_required(['支援員', 'サービス管理責任者', '管理者']) 
def check_out():
    data = request.get_json()
    user_id = data.get('user_id')
    current_time = datetime.utcnow()

    if not user_id:
        return jsonify({"error": "利用者IDが不足しています。"}), 400

    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": f"利用者ID {user_id} は存在しません。"}), 404

        today_date = current_time.date()
        
        # 1. 今日の DailyLog レコードを検索
        existing_log = DailyLog.query.filter(
            DailyLog.user_id == user_id,
            DailyLog.activity_date == today_date
        ).first()

        if existing_log is None or existing_log.check_in_time is None:
            # チェックイン記録がない場合、先にチェックインを促す
            return jsonify({"error": "先にチェックインを行ってください。"}), 400
        
        if existing_log.check_out_time:
             # 既にチェックアウト済み
            return jsonify({"message": "既に本日の退所が記録されています。", "log_id": existing_log.id}), 200

        # 2. check_out_time を更新
        existing_log.check_out_time = current_time
        db.session.commit()
        
        return jsonify({
            "message": f"利用者 {user.last_name} の退所を記録しました。",
            "check_out_time": current_time.isoformat(),
            "log_id": existing_log.id
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"サーバーエラーが発生しました: {str(e)}"}), 500

# ======================================================
# 5. 通所予定一覧取得 API (GET /api/attendance/plans)
# ======================================================
@attendance_bp.route('/plans', methods=['GET']) # ★ GET API の追加 ★
@role_required(['支援員', 'サービス管理責任者', '管理者'])
def get_attendance_plans():
    # ロジックは省略 - データベースから予定を取得し、JSONで返す
    # UserモデルとAttendancePlanモデルを結合するクエリが必要
    return jsonify({"plans": []}), 200 # 暫定レスポンス