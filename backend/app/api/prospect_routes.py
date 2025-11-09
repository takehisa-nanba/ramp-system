# app/api/prospect_routes.py

from flask import Blueprint, request, jsonify
from app.extensions import db
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from app.api.auth_routes import role_required # 認証デコレーター

# --- V1.1 モデルのインポート ---
from app.models.core import User
from app.models.master import StatusMaster
from app.models.plan import PreEnrollmentLog 

# Blueprintを作成
prospect_bp = Blueprint('prospect', __name__)

# ======================================================
# 1. [職員用] 新規問合せ（見学者）登録 API (POST /api/prospects)
# ======================================================
@prospect_bp.route('/prospects', methods=['POST'])
# --- ★ 修正: V1.1の新しいロール名を使用 ★ ---
@role_required(['SystemAdmin', 'OfficeAdmin', 'Sabikan', 'Staff'])
def create_prospect_by_staff():
    """
    [職員用] 電話や対面での問合せを元に、職員が'新規問合せ'ユーザーを登録する。
    """
    data = request.get_json()

    # 1. 必須フィールドの検証 (表示名)
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
        
        # 3. 重複チェック (Email, SNS)
        if data.get('email') and User.query.filter_by(email=data['email']).first():
            return jsonify({"error": "このメールアドレスは既に使用されています。"}), 409
        if is_sns_contact and User.query.filter_by(sns_provider=data['sns_provider'], sns_account_id=data['sns_account_id']).first():
            return jsonify({"error": "このSNS IDは既に使用されています。"}), 409

        # 4. Userオブジェクトの作成
        new_guest = User(
            display_name=data['display_name'],
            status_id=guest_status.id,
            email=data.get('email'), 
            phone_number=data.get('phone_number'),
            sns_provider=data.get('sns_provider'),
            sns_account_id=data.get('sns_account_id'),
            utm_source=data.get('utm_source', 'phone'), 
            utm_medium=data.get('utm_medium', 'offline'),
            utm_campaign=data.get('utm_campaign'),
            last_name=data.get('last_name'),
            first_name=data.get('first_name')
        )
        
        db.session.add(new_guest)
        db.session.commit()
        
        return jsonify({
            "message": f"新規問合せ「{new_guest.display_name}」様を登録しました。",
            "user_id": new_guest.id
        }), 201

    except IntegrityError as e:
        db.session.rollback()
        return jsonify({"error": "データベース制約違反です。", "details": str(e)}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "サーバー内部エラーが発生しました。", "details": str(e)}), 500

# ======================================================
# 2. 新規問合せ（見学者）一覧取得 API (GET /api/prospects)
# ======================================================
@prospect_bp.route('/prospects', methods=['GET'])
# --- ★ 修正: V1.1の新しいロール名を使用 ★ ---
@role_required(['SystemAdmin', 'OfficeAdmin', 'Sabikan', 'Staff'])
def get_prospect_list():
    """
    ステータスが「新規問合せ」「体験利用」などの本利用前の利用者一覧を取得する。
    """
    try:
        # 'user'カテゴリの'新規問合せ'または'体験利用'のステータスIDを取得
        prospect_statuses = StatusMaster.query.filter(
            StatusMaster.category == 'user',
            StatusMaster.name.in_(['新規問合せ', '体験利用', '見学済み']) # 必要に応じて名前を追加
        ).all()
        
        if not prospect_statuses:
            return jsonify([]), 200 # 対象ステータスがなければ空を返す

        prospect_status_ids = [s.id for s in prospect_statuses]

        # 該当するステータスの利用者のみを検索
        stmt = (
            db.select(User)
            .where(User.status_id.in_(prospect_status_ids))
            .where(User.is_archivable == False)
            .order_by(User.created_at.desc()) # 新しい問合せから順
        )
        
        users = db.session.execute(stmt).scalars().all()

        prospect_list = [
            {
                "id": user.id,
                "display_name": user.display_name,
                "contact_info": user.email or user.phone_number or user.sns_provider,
                "status_id": user.status_id,
                "created_at": user.created_at.isoformat(),
                "utm_source": user.utm_source # 流入経路
            }
            for user in users
        ]

        return jsonify(prospect_list), 200

    except Exception as e:
        return jsonify({"error": "サーバー内部エラーが発生しました。", "details": str(e)}), 500

# ======================================================
# 3. 新規問合せ（見学者）詳細取得 API (GET /api/prospects/<int:user_id>)
# ======================================================
@prospect_bp.route('/prospects/<int:user_id>', methods=['GET'])
# --- ★ 修正: V1.1の新しいロール名を使用 ★ ---
@role_required(['SystemAdmin', 'OfficeAdmin', 'Sabikan', 'Staff'])
def get_prospect_detail(user_id):
    """
    特定の新規問合せ（見学者）の詳細情報を取得します。
    「利用前接触記録（PreEnrollmentLog）」も一緒に返します。
    """
    try:
        # 1. メインの利用者情報を取得
        user = db.session.get(User, user_id)
        if not user:
            return jsonify({"error": "利用者が見つかりません。"}), 404

        # 2. JSONレスポンスに整形
        response_data = {
            "id": user.id,
            "display_name": user.display_name,
            "last_name": user.last_name,
            "first_name": user.first_name,
            "status_id": user.status_id,
            
            # 連絡先
            "phone_number": user.phone_number,
            "email": user.email,
            
            # SNS
            "sns_provider": user.sns_provider,
            "sns_account_id": user.sns_account_id,
            
            # マーケティング
            "utm_source": user.utm_source,
            "utm_medium": user.utm_medium,
            "utm_campaign": user.utm_campaign
        }
        
        # 3. この利用者の「利用前接触記録」をすべて取得
        logs_query = (
            db.select(PreEnrollmentLog)
            .where(PreEnrollmentLog.user_id == user_id)
            .order_by(PreEnrollmentLog.contact_date.desc())
        )
        logs = db.session.execute(logs_query).scalars().all()
        
        response_data['pre_enrollment_logs'] = [
            {
                "log_id": log.id,
                "contact_date": log.contact_date.isoformat(),
                "log_type": log.log_type, # '事前アンケート', '見学', '体験'
                "supporter_id": log.supporter_id,
                "summary": log.summary,
                "initial_assessment_memo": log.initial_assessment_memo
            }
            for log in logs
        ]

        return jsonify(response_data), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "サーバー内部エラーが発生しました。", "details": str(e)}), 500
