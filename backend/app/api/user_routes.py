from flask import Blueprint, request, jsonify
from app.extensions import db
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from app.api.auth_routes import role_required # 認証デコレーター

# --- V1.0 モデルのインポート ---
from app.models.core import User, Supporter
from app.models.master import StatusMaster, DisabilityTypeMaster

# Blueprintを作成 (名前は 'user' のまま)
user_bp = Blueprint('user', __name__)

# ======================================================
# 1. 利用者新規登録 API (POST /api/users)
# ======================================================
@user_bp.route('/users', methods=['POST'])
@role_required(['管理者', 'サービス管理責任者', '支援員']) # 登録権限
def create_user():
    """
    新しい利用者をデータベースに登録します。
    V1.0モデルに基づき、障害種別やステータスIDも必須とします。
    """
    data = request.get_json()

    # 1. 必須フィールドの検証
    required_fields = [
        'last_name', 'first_name', 
        'last_name_kana', 'first_name_kana',
        'birth_date', 'gender',
        'status_id', # '利用中' '体験利用' などのID
        'disability_type_id' # '身体障害' '精神障害' などのID
    ]
    
    if not all(field in data for field in required_fields):
        return jsonify({"error": "必須フィールドが不足しています。"}), 400

    try:
        # 2. 外部キー（ID）の存在チェック
        status = db.session.get(StatusMaster, data['status_id'])
        if not status or status.category != 'user':
            return jsonify({"error": f"無効なステータスIDです: {data['status_id']}"}), 400
            
        disability_type = db.session.get(DisabilityTypeMaster, data['disability_type_id'])
        if not disability_type:
            return jsonify({"error": f"無効な障害種別IDです: {data['disability_type_id']}"}), 400

        # 担当職員（任意）
        primary_supporter_id = data.get('primary_supporter_id')
        if primary_supporter_id and not db.session.get(Supporter, primary_supporter_id):
             return jsonify({"error": f"無効な担当職員IDです: {primary_supporter_id}"}), 400

        # 3. Userオブジェクトの作成 (V1.0モデル定義に基づく)
        new_user = User(
            last_name=data['last_name'],
            first_name=data['first_name'],
            last_name_kana=data['last_name_kana'],
            first_name_kana=data['first_name_kana'],
            birth_date=datetime.strptime(data['birth_date'], '%Y-%m-%d').date(),
            gender=data['gender'],
            
            # 外部キー
            status_id=data['status_id'],
            disability_type_id=data['disability_type_id'],
            primary_supporter_id=primary_supporter_id,
            
            # 連絡先 (任意)
            postal_code=data.get('postal_code'),
            address=data.get('address'),
            phone_number=data.get('phone_number'),
            email=data.get('email'),
            
            # 契約・障害情報 (任意)
            service_start_date=datetime.strptime(data.get('service_start_date'), '%Y-%m-%d').date() if data.get('service_start_date') else None,
            plan_consultation_office=data.get('plan_consultation_office'),
            handbook_level=data.get('handbook_level'),
            
            # --- V1.0モデルのデフォルト値 (モデル側で設定済みだが、明示しても良い) ---
            # is_active=True,
            # is_archivable=False,
            # remote_service_allowed=False,
            # is_currently_working=False,
            # is_handbook_certified=data.get('is_handbook_certified', False)
        )

        # 4. データベースへの保存
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({
            "message": f"利用者「{new_user.last_name} {new_user.first_name}」様を登録しました。",
            "user_id": new_user.id
        }), 201

    except IntegrityError as e:
        db.session.rollback()
        # email の UniqueConstraint 違反など
        return jsonify({"error": "データベース制約違反です。Emailが重複している可能性があります。", "details": str(e)}), 409
    except ValueError:
        db.session.rollback()
        return jsonify({"error": "日付の形式が正しくありません (YYYY-MM-DD)。"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "サーバー内部エラーが発生しました。", "details": str(e)}), 500

# ======================================================
# 2. 利用者一覧取得 API (GET /api/users)
# ======================================================
@user_bp.route('/users', methods=['GET'])
@role_required(['管理者', 'サービス管理責任者', '支援員'])
def get_user_list():
    """
    登録されている利用者の一覧を取得します。
    ステータス名、担当職員名も結合して返します。
    """
    try:
        # 1. データベースクエリ (SQLAlchemy 2.0 style)
        # User, StatusMaster, Supporter(primary) を join
        stmt = (
            db.select(
                User,
                StatusMaster.name.label('status_name'),
                Supporter.last_name.label('supporter_last_name'),
                Supporter.first_name.label('supporter_first_name')
            )
            .join(StatusMaster, User.status_id == StatusMaster.id)
            .outerjoin(Supporter, User.primary_supporter_id == Supporter.id)
            .where(User.is_archivable == False) # ★ アーカイブ済みの利用者は除外
            .order_by(User.last_name_kana, User.first_name_kana) # カナ順でソート
        )
        
        users_result = db.session.execute(stmt).all()

        # 2. JSONレスポンスに整形
        user_list = []
        for row in users_result:
            user = row.User
            supporter_name = (
                f"{row.supporter_last_name} {row.supporter_first_name}"
                if row.supporter_last_name
                else None
            )
            
            user_list.append({
                "id": user.id,
                "full_name": f"{user.last_name} {user.first_name}",
                "full_name_kana": f"{user.last_name_kana} {user.first_name_kana}",
                "status_name": row.status_name,
                "is_active": user.is_active,
                "primary_supporter_name": supporter_name,
                "service_start_date": user.service_start_date.isoformat() if user.service_start_date else None
            })

        return jsonify(user_list), 200

    except Exception as e:
        return jsonify({"error": "サーバー内部エラーが発生しました。", "details": str(e)}), 500

# ======================================================
# 3. 利用者詳細取得 API (GET /api/users/<int:user_id>)
# ======================================================
@user_bp.route('/users/<int:user_id>', methods=['GET'])
@role_required(['管理者', 'サービス管理責任者', '支援員'])
def get_user_detail(user_id):
    """
    特定の利用者の詳細情報を取得します。
    V1.0モデルのすべての関連情報を結合します。
    """
    try:
        # 1. メインの利用者情報を取得 (V1.0モデルに合わせて関連マスタを全て結合)
        stmt = (
            db.select(
                User,
                StatusMaster.name.label('status_name'),
                DisabilityTypeMaster.name.label('disability_type_name'),
                Supporter.last_name.label('supporter_last_name'),
                Supporter.first_name.label('supporter_first_name')
            )
            .join(StatusMaster, User.status_id == StatusMaster.id)
            .outerjoin(DisabilityTypeMaster, User.disability_type_id == DisabilityTypeMaster.id)
            .outerjoin(Supporter, User.primary_supporter_id == Supporter.id)
            .where(User.id == user_id)
        )
        
        user_result = db.session.execute(stmt).first()

        if not user_result:
            return jsonify({"error": "利用者が見つかりません。"}), 404

        user = user_result.User
        supporter_name = (
            f"{user_result.supporter_last_name} {user_result.supporter_first_name}"
            if user_result.supporter_last_name
            else None
        )

        # 2. JSONレスポンスに整形
        response_data = {
            "id": user.id,
            "last_name": user.last_name,
            "first_name": user.first_name,
            "last_name_kana": user.last_name_kana,
            "first_name_kana": user.first_name_kana,
            "birth_date": user.birth_date.isoformat() if user.birth_date else None,
            "gender": user.gender,
            
            # ステータスと担当
            "status_name": user_result.status_name,
            "primary_supporter_name": supporter_name,
            "primary_supporter_id": user.primary_supporter_id,

            # 連絡先
            "postal_code": user.postal_code,
            "address": user.address,
            "phone_number": user.phone_number,
            "email": user.email,
            
            # 障害情報 (V1.0)
            "disability_type_name": user_result.disability_type_name,
            "disability_type_id": user.disability_type_id,
            "handbook_level": user.handbook_level,
            "is_handbook_certified": user.is_handbook_certified,

            # 契約情報 (V1.0)
            "service_start_date": user.service_start_date.isoformat() if user.service_start_date else None,
            "service_end_date": user.service_end_date.isoformat() if user.service_end_date else None,
            "plan_consultation_office": user.plan_consultation_office,
            "is_active": user.is_active,
            "remote_service_allowed": user.remote_service_allowed,
            
            # 就労・アーカイブ情報 (V1.0)
            "is_currently_working": user.is_currently_working,
            "employment_start_date": user.employment_start_date.isoformat() if user.employment_start_date else None,
            "employment_status": user.employment_status,
            "is_archivable": user.is_archivable,
        }
        
        # 3. (将来) ここに受給者証や緊急連絡先の情報を追加するロジック
        # (例: emergency_contacts = user.emergency_contacts)
        # ...

        return jsonify(response_data), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "サーバー内部エラーが発生しました。", "details": str(e)}), 500

# ======================================================
# 4. 利用者情報更新 API (PUT /api/users/<int:user_id>)
# ======================================================
@user_bp.route('/users/<int:user_id>', methods=['PUT'])
@role_required(['管理者', 'サービス管理責任者', '支援員'])
def update_user_detail(user_id):
    """
    特定の利用者の詳細情報を更新します。
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "更新データがありません。"}), 400

    try:
        # 1. 更新対象の利用者を検索
        user = db.session.get(User, user_id)
        if not user:
            return jsonify({"error": "利用者が見つかりません。"}), 404

        # 2. 外部キー（ID）の存在チェック (変更がある場合のみ)
        if 'status_id' in data:
            status = db.session.get(StatusMaster, data['status_id'])
            if not status or status.category != 'user':
                return jsonify({"error": f"無効なステータスIDです: {data['status_id']}"}), 400
            user.status_id = data['status_id']

        if 'disability_type_id' in data:
            disability_type = db.session.get(DisabilityTypeMaster, data['disability_type_id'])
            if not disability_type:
                return jsonify({"error": f"無効な障害種別IDです: {data['disability_type_id']}"}), 400
            user.disability_type_id = data['disability_type_id']

        if 'primary_supporter_id' in data:
            supporter_id = data['primary_supporter_id']
            if supporter_id and not db.session.get(Supporter, supporter_id):
                 return jsonify({"error": f"無効な担当職員IDです: {supporter_id}"}), 400
            user.primary_supporter_id = supporter_id

        # 3. 基本情報の更新 (data.get を使い、項目が存在する場合のみ更新)
        user.last_name = data.get('last_name', user.last_name)
        user.first_name = data.get('first_name', user.first_name)
        user.last_name_kana = data.get('last_name_kana', user.last_name_kana)
        user.first_name_kana = data.get('first_name_kana', user.first_name_kana)
        user.gender = data.get('gender', user.gender)
        
        # 連絡先
        user.postal_code = data.get('postal_code', user.postal_code)
        user.address = data.get('address', user.address)
        user.phone_number = data.get('phone_number', user.phone_number)
        user.email = data.get('email', user.email) # (Email変更時は重複チェック注意)
        
        # 障害情報
        user.handbook_level = data.get('handbook_level', user.handbook_level)
        user.is_handbook_certified = data.get('is_handbook_certified', user.is_handbook_certified)

        # 契約情報
        user.plan_consultation_office = data.get('plan_consultation_office', user.plan_consultation_office)
        user.is_active = data.get('is_active', user.is_active)
        user.remote_service_allowed = data.get('remote_service_allowed', user.remote_service_allowed)

        # 就労・アーカイブ
        user.is_currently_working = data.get('is_currently_working', user.is_currently_working)
        user.employment_status = data.get('employment_status', user.employment_status)
        user.is_archivable = data.get('is_archivable', user.is_archivable)

        # 4. 日付の更新 (日付はフォーマット変換が必要なため個別に処理)
        if 'birth_date' in data and data['birth_date']:
            user.birth_date = datetime.strptime(data['birth_date'], '%Y-%m-%d').date()
        
        if 'service_start_date' in data:
            user.service_start_date = datetime.strptime(data['service_start_date'], '%Y-%m-%d').date() if data['service_start_date'] else None

        if 'service_end_date' in data:
            user.service_end_date = datetime.strptime(data['service_end_date'], '%Y-%m-%d').date() if data['service_end_date'] else None
            
        if 'employment_start_date' in data:
            user.employment_start_date = datetime.strptime(data['employment_start_date'], '%Y-%m-%d').date() if data['employment_start_date'] else None

        # 5. データベースへコミット
        db.session.commit()

        return jsonify({
            "message": f"利用者「{user.last_name} {user.first_name}」様の情報を更新しました。",
            "user_id": user.id
        }), 200

    except IntegrityError as e:
        db.session.rollback()
        return jsonify({"error": "データベース制約違反です。Emailが重複している可能性があります。", "details": str(e)}), 409
    except ValueError:
        db.session.rollback()
        return jsonify({"error": "日付の形式が正しくありません (YYYY-MM-DD)。"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "サーバー内部エラーが発生しました。", "details": str(e)}), 500
