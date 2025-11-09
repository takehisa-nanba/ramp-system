# app/api/supporter_routes.py

from flask import Blueprint, request, jsonify
from app.extensions import db
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from app.api.auth_routes import role_required # 認証デコレーター

# --- V1.1 モデルのインポート ---
from app.models.core import Supporter
from app.models.master import RoleMaster

# Blueprintを作成
supporter_bp = Blueprint('supporter', __name__)

# ======================================================
# 1. 職員新規登録 API (POST /api/supporters)
# ======================================================
@supporter_bp.route('/supporters', methods=['POST'])
@role_required(['管理者']) # ★ 職員の登録は「管理者」のみに制限
def create_supporter():
    """
    [管理者用] 新しい職員アカウントを登録します。
    """
    data = request.get_json()
    
    # 1. 必須フィールドの検証
    required_fields = ['last_name', 'first_name', 'email', 'password', 'role_name']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "必須フィールド（氏名, email, password, role_name）が不足しています。"}), 400

    try:
        # 2. ロールIDのルックアップ
        role = RoleMaster.query.filter_by(name=data['role_name']).first()
        if not role:
            return jsonify({"error": f"無効なロール名です: {data['role_name']}"}), 400

        # 3. メールアドレスの重複チェック
        if Supporter.query.filter_by(email=data['email']).first():
            return jsonify({"error": "このメールアドレスは既に使用されています。"}), 409

        # 4. 新しい Supporter オブジェクトを作成
        new_supporter = Supporter(
            last_name=data['last_name'],
            first_name=data['first_name'],
            email=data['email'],
            role_id=role.id,
            
            # V1.1モデルの追加カラム (任意)
            last_name_kana=data.get('last_name_kana'),
            first_name_kana=data.get('first_name_kana'),
            hire_date=datetime.strptime(data['hire_date'], '%Y-%m-%d').date() if data.get('hire_date') else None,
            seal_image_url=data.get('seal_image_url'),
            
            # 常勤換算 (任意、デフォルト値がモデルで設定されている)
            is_full_time=data.get('is_full_time', False),
            scheduled_work_hours=data.get('scheduled_work_hours', 40),
            employment_type=data.get('employment_type', '正社員'),
            
            remarks=data.get('remarks')
        )
        
        # 5. パスワードのハッシュ化と設定
        new_supporter.set_password(data['password'])
        
        # 6. データベースに保存
        db.session.add(new_supporter)
        db.session.commit()
        
        return jsonify({
            "message": f"{new_supporter.last_name} {new_supporter.first_name} 様を職員として登録しました。",
            "supporter_id": new_supporter.id,
            "role_id": role.id
        }), 201

    except IntegrityError as e:
        db.session.rollback()
        return jsonify({"error": "データベース制約違反（Email重複など）が発生しました。", "details": str(e)}), 409
    except ValueError:
        db.session.rollback()
        return jsonify({"error": "日付の形式が正しくありません (YYYY-MM-DD)。"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"サーバーエラーが発生しました: {str(e)}"}), 500

# ======================================================
# 2. 職員一覧取得 API (GET /api/supporters)
# ======================================================
@supporter_bp.route('/supporters', methods=['GET'])
@role_required(['管理者', 'サービス管理責任者', '支援員']) # 全職員が閲覧可能
def get_supporter_list():
    """
    全職員の一覧（ID, 氏名, ロール）を取得します。
    """
    try:
        stmt = (
            db.select(
                Supporter.id,
                Supporter.last_name,
                Supporter.first_name,
                Supporter.is_active,
                RoleMaster.name.label('role_name')
            )
            .join(RoleMaster, Supporter.role_id == RoleMaster.id)
            .order_by(Supporter.last_name_kana)
        )
        
        supporters_result = db.session.execute(stmt).all()

        supporter_list = [
            {
                "id": row.id,
                "full_name": f"{row.last_name} {row.first_name}",
                "role_name": row.role_name,
                "is_active": row.is_active
            }
            for row in supporters_result
        ]

        return jsonify(supporter_list), 200

    except Exception as e:
        return jsonify({"error": "サーバー内部エラーが発生しました。", "details": str(e)}), 500
