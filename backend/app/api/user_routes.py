from flask import Blueprint, request, jsonify
from app.extensions import db
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from app.api.auth_routes import role_required # 認証デコレーター

# --- V1.1 モデルのインポート ---
from app.models.core import User, Supporter
from app.models.master import StatusMaster, DisabilityTypeMaster

# Blueprintを作成
user_bp = Blueprint('user', __name__)

# ======================================================
# 1. [職員用] 利用者新規登録 API (POST /api/users)
# ======================================================
@user_bp.route('/users', methods=['POST'])
@role_required(['管理者', 'サービス管理責任者', '支援員']) 
def create_user():
    """
    [職員用] 新しい利用者をデータベースに登録します。
    実名(last/first_name)が必須です。
    display_name は実名から自動生成されます。
    """
    data = request.get_json()

    # 1. 必須フィールドの検証 (職員が登録する場合、実名は必須)
    required_fields = [
        'last_name', 'first_name', 
        'last_name_kana', 'first_name_kana',
        'birth_date', 'gender',
        'status_id', 
        'disability_type_id'
    ]
    
    if not all(field in data for field in required_fields):
        return jsonify({"error": "必須フィールド（実名、生年月日、ステータス等）が不足しています。"}), 400

    try:
        # 2. 外部キー（ID）の存在チェック
        status = db.session.get(StatusMaster, data['status_id'])
        if not status or status.category != 'user':
             return jsonify({"error": f"無効なステータスIDです: {data['status_id']}"}), 400
        disability_type = db.session.get(DisabilityTypeMaster, data['disability_type_id'])
        if not disability_type:
             return jsonify({"error": f"無効な障害種別IDです: {data['disability_type_id']}"}), 400

        # 3. Userオブジェクトの作成
        
        # ★ 修正: display_name（必須）を実名から自動生成
        display_name = f"{data['last_name']} {data['first_name']}"
        
        new_user = User(
            last_name=data['last_name'],
            first_name=data['first_name'],
            display_name=display_name, # ★ 追加
            
            last_name_kana=data['last_name_kana'],
            first_name_kana=data['first_name_kana'],
            birth_date=datetime.strptime(data['birth_date'], '%Y-%m-%d').date(),
            gender=data['gender'],
            status_id=data['status_id'],
            disability_type_id=data['disability_type_id'],
            primary_supporter_id=data.get('primary_supporter_id'),
            
            # 連絡先 (任意)
            postal_code=data.get('postal_code'),
            address=data.get('address'),
            phone_number=data.get('phone_number'),
            email=data.get('email'),
            
            # SNS (任意)
            sns_provider=data.get('sns_provider'),
            sns_account_id=data.get('sns_account_id'),

            # マーケティング (任意)
            utm_source=data.get('utm_source'),
            utm_medium=data.get('utm_medium'),
            utm_campaign=data.get('utm_campaign'),
            
            # ( ... 他のフィールド ...)
            service_start_date=datetime.strptime(data.get('service_start_date'), '%Y-%m-%d').date() if data.get('service_start_date') else None,
            plan_consultation_office=data.get('plan_consultation_office'),
            handbook_level=data.get('handbook_level'),
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({
            "message": f"利用者「{new_user.display_name}」様を登録しました。",
            "user_id": new_user.id
        }), 201

    except IntegrityError as e:
        db.session.rollback()
        return jsonify({"error": "データベース制約違反です。EmailまたはSNS IDが重複している可能性があります。", "details": str(e)}), 409
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
    try:
        stmt = (
            db.select(
                User,
                StatusMaster.name.label('status_name'),
                Supporter.last_name.label('supporter_last_name'),
                Supporter.first_name.label('supporter_first_name')
            )
            .join(StatusMaster, User.status_id == StatusMaster.id)
            .outerjoin(Supporter, User.primary_supporter_id == Supporter.id)
            .where(User.is_archivable == False)
            .order_by(User.last_name_kana, User.first_name_kana) # ★ 実名が登録されていればカナ順
        )
        users_result = db.session.execute(stmt).all()

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
                "display_name": user.display_name, # ★ 表示名
                "full_name": f"{user.last_name} {user.first_name}" if user.last_name else None, # ★ 実名
                "full_name_kana": f"{user.last_name_kana} {user.first_name_kana}" if user.last_name_kana else None,
                "status_name": row.status_name,
                "is_active": user.is_active,
                "primary_supporter_name": supporter_name,
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
    try:
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

        response_data = {
            "id": user.id,
            "display_name": user.display_name, # ★ 表示名
            "last_name": user.last_name,       # ★ 実名
            "first_name": user.first_name,     # ★ 実名
            "last_name_kana": user.last_name_kana,
            "first_name_kana": user.first_name_kana,
            "birth_date": user.birth_date.isoformat() if user.birth_date else None,
            "gender": user.gender,
            
            "status_name": user_result.status_name,
            "primary_supporter_name": supporter_name,
            "primary_supporter_id": user.primary_supporter_id,

            # 連絡先
            "postal_code": user.postal_code,
            "address": user.address,
            "phone_number": user.phone_number,
            "email": user.email,
            "seal_image_url": user.seal_image_url,
            
            "sns_provider": user.sns_provider,
            "sns_account_id": user.sns_account_id,
            
            # ( ... 障害情報, 契約情報, 就労情報 ...)
            
            # マーケティング
            "utm_source": user.utm_source,
            "utm_medium": user.utm_medium,
            "utm_campaign": user.utm_campaign
        }
        
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
    data = request.get_json()
    if not data:
        return jsonify({"error": "更新データがありません。"}), 400

    try:
        user = db.session.get(User, user_id)
        if not user:
            return jsonify({"error": "利用者が見つかりません。"}), 404

        # ( ... 外部キーのチェック: status_id, disability_type_id, ... )

        # ★ 修正: display_name と 実名(last/first_name) の更新
        user.display_name = data.get('display_name', user.display_name)
        user.last_name = data.get('last_name', user.last_name)
        user.first_name = data.get('first_name', user.first_name)
        user.last_name_kana = data.get('last_name_kana', user.last_name_kana)
        user.first_name_kana = data.get('first_name_kana', user.first_name_kana)
        
        # 連絡先
        user.phone_number = data.get('phone_number', user.phone_number)
        user.email = data.get('email', user.email)
        user.seal_image_url = data.get('seal_image_url', user.seal_image_url)

        # SNS
        user.sns_provider = data.get('sns_provider', user.sns_provider)
        user.sns_account_id = data.get('sns_account_id', user.sns_account_id)
        
        # ... (障害情報, 契約情報, 就労情報) ...

        # マーケティング
        user.utm_source = data.get('utm_source', user.utm_source)
        user.utm_medium = data.get('utm_medium', user.utm_medium)
        user.utm_campaign = data.get('utm_campaign', user.utm_campaign)
        
        # ( ... 日付の更新 ... )

        db.session.commit()

        return jsonify({
            "message": f"利用者「{user.display_name}」様の情報を更新しました。",
            "user_id": user.id
        }), 200

    # ( ... エラーハンドリング ... )
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({"error": "データベース制約違反です。Email/SNS ID等が重複している可能性があります。", "details": str(e)}), 409
    except ValueError:
        db.session.rollback()
        return jsonify({"error": "日付の形式が正しくありません (YYYY-MM-DD)。"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "サーバー内部エラーが発生しました。", "details": str(e)}), 500


# ======================================================
# 5. 見学者登録API (POST /api/register_guest) - ★認証不要★
# ======================================================
@user_bp.route('/register_guest', methods=['POST'])
def register_guest():
    """
    LP(ランディングページ)から見学者が自身で登録するためのAPI。
    'display_name'が必須。
    """
    data = request.get_json()

    # 1. 必須フィールドの検証 (★ 'display_name' が必須 ★)
    required_fields = ['display_name']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "必須フィールド（表示名）が不足しています。"}), 400

    # 連絡先(Email, 電話番号, またはSNS経由)のどれか1つは必須
    is_sns_contact = data.get('sns_provider') and data.get('sns_account_id')
    if not data.get('email') and not data.get('phone_number') and not is_sns_contact:
         return jsonify({"error": "連絡先（Email、電話番号、またはSNS ID）のどれか一つは入力してください。"}), 400

    try:
        # 2. ステータスIDを自動で検索
        guest_status = StatusMaster.query.filter_by(category='user', name='新規問合せ').first()
        if not guest_status:
            return jsonify({"error": "システムの初期設定（'新規問合せ'ステータス）がされていません。"}), 500
        
        # 3. 重複チェック
        if data.get('email') and User.query.filter_by(email=data['email']).first():
            return jsonify({"error": "このメールアドレスは既に使用されています。"}), 409
        
        if is_sns_contact:
            if User.query.filter_by(
                sns_provider=data['sns_provider'], 
                sns_account_id=data['sns_account_id']
            ).first():
                return jsonify({"error": "このSNS IDは既に使用されています。"}), 409

        # 4. Userオブジェクトの作成
        new_guest = User(
            display_name=data['display_name'], # ★ 必須
            status_id=guest_status.id,
            
            # (last_name, first_name は NULL)
            
            # 連絡先 (任意)
            email=data.get('email'), 
            phone_number=data.get('phone_number'),
            
            # SNS (任意)
            sns_provider=data.get('sns_provider'),
            sns_account_id=data.get('sns_account_id'),
            
            # マーケティング
            utm_source=data.get('utm_source'),
            utm_medium=data.get('utm_medium'),
            utm_campaign=data.get('utm_campaign')
        )
        
        # パスワードが入力されていれば設定 (任意)
        if data.get('password'):
            new_guest.set_password(data['password']) 

        db.session.add(new_guest)
        db.session.commit()
        
        return jsonify({
            "message": f"{new_guest.display_name} 様、ご登録ありがとうございます。担当者からの連絡をお待ちください。",
            "user_id": new_guest.id
        }), 201

    # ( ... エラーハンドリング ... )
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({"error": "データベース制約違反です。", "details": str(e)}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "サーバー内部エラーが発生しました。", "details": str(e)}), 500
