# app/api/attendance_routes.py (新規ファイル)

from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models import AttendancePlan, User # AttendancePlan モデルは新たに作成が必要です
from app.api.auth_routes import role_required
from datetime import datetime
from sqlalchemy.exc import IntegrityError

attendance_bp = Blueprint('attendance', __name__)

@attendance_bp.route('/plans', methods=['POST'])
@role_required(['支援員', 'サービス管理責任者', '管理者'])
def create_attendance_plan():
    data = request.get_json()
    
    required_fields = ['user_id', 'planned_date', 'planned_check_in', 'planned_check_out']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "必須フィールドが不足しています。"}), 400

    try:
        # 利用者存在チェック
        if User.query.get(data['user_id']) is None:
            return jsonify({"error": f"利用者ID {data['user_id']} は存在しません。"}), 400
            
        # 日付と時刻の変換
        planned_date = datetime.strptime(data['planned_date'], '%Y-%m-%d').date()
        planned_in = datetime.strptime(data['planned_check_in'], '%H:%M').time()
        planned_out = datetime.strptime(data['planned_check_out'], '%H:%M').time()
        
        new_plan = AttendancePlan(
            user_id=data['user_id'],
            planned_date=planned_date,
            planned_check_in=planned_in,
            planned_check_out=planned_out,
            is_recurring=data.get('is_recurring', False),
            remarks=data.get('remarks')
        )
        
        db.session.add(new_plan)
        db.session.commit()
        
        return jsonify({
            "message": "通所予定を正常に登録しました。",
            "plan_id": new_plan.id
        }), 201

    except ValueError:
        return jsonify({"error": "日付または時刻の形式が正しくありません。 (YYYY-MM-DD / HH:MM)"}), 400
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "データベース制約違反（既に同じ日の予定が存在する可能性）が発生しました。"}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"サーバーエラーが発生しました: {str(e)}"}), 500
    
@attendance_bp.route('/plans/<int:plan_id>', methods=['GET'])
@role_required(['支援員', 'サービス管理責任者', '管理者'])   
def get_attendance_plan(plan_id):
    try:
        plan = AttendancePlan.query.get(plan_id)
        if not plan:
            return jsonify({"error": "指定された通所予定が存在しません。"}), 404
        
        plan_data = {
            "plan_id": plan.id,
            "user_id": plan.user_id,
            "planned_date": plan.planned_date.isoformat(),
            "planned_check_in": plan.planned_check_in.strftime('%H:%M'),
            "planned_check_out": plan.planned_check_out.strftime('%H:%M'),
            "is_recurring": plan.is_recurring,
            "remarks": plan.remarks
        }
        
        return jsonify(plan_data), 200

    except Exception as e:
        return jsonify({"error": f"サーバーエラーが発生しました: {str(e)}"}), 500