# app/api/prospect_routes.py

from flask import Blueprint, request, jsonify
from app.extensions import db
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from app.api.auth_routes import role_required # 認証デコレーター

# --- V1.1 モデルのインポート ---
from app.models.core import User
from app.models.master import StatusMaster

# Blueprintを作成
prospect_bp = Blueprint('prospect', __name__)

# ======================================================
# 1. [職員用] 新規問合せ（見学者）登録 API
# ======================================================
@prospect_bp.route('/prospects', methods=['POST'])
@role_required(['管理者', 'サービス管理責任者', '支援員']) # ★ 職員の認証が必須
def create_prospect_by_staff():
    """
    [職員用] 電話や対面での問合せを元に、職員が'新規問合せ'ユーザーを登録する。
    """
    data = request.get_json()

    # 1. 必須フィールドの検証 (氏名と、連絡先1つ)
    required_fields = ['last_name', 'first_name']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "必須フィールド（氏名）が不足しています。"}), 400

    if not (data.get('email') or data.get('phone_number') or data.get('line_id') or data.get('x_id') or data.get('meta_id')):
         return jsonify({"error": "連絡先（Email、電話番号、またはSNS ID）のどれか一つは入力してください。"}), 400

    try:
        # 2. ステータスIDを自動で検索
        guest_status = StatusMaster.query.filter_by(category='user', name='新規問合せ').first()
        if not guest_status:
            return jsonify({"error": "システムの初期設定（'新規問合せ'ステータス）がされていません。"}), 500
        
        # 3. 重複チェック
        if data.get('email') and User.query.filter_by(email=data['email']).first():
            return jsonify({"error": "このメールアドレスは既に使用されています。"}), 409
        if data.get('line_id') and User.query.filter_by(line_id=data['line_id']).first():
            return jsonify({"error": "このLINE IDは既に使用されています。"}), 409
        # (X, Metaも同様にチェック) ...

        # 4. Userオブジェクトの作成
        new_guest = User(
            last_name=data['last_name'],
            first_name=data['first_name'],
            status_id=guest_status.id,
            
            # 連絡先
            email=data.get('email'), 
            phone_number=data.get('phone_number'),
            
            # ソーシャルID
            line_id=data.get('line_id'),
            x_id=data.get('x_id'),
            meta_id=data.get('meta_id'),
            
            # ★ 職員が手動で登録した場合、流入経路(UTM)は 'offline' や 'phone' にする
            utm_source=data.get('utm_source', 'phone'), # 職員が入力 (デフォルト'phone')
            utm_medium=data.get('utm_medium', 'offline') # 職員が入力 (デフォルト'offline')
        )
        
        # (※職員が登録する場合、パスワードは設定しない。本人が後で設定する)

        db.session.add(new_guest)
        db.session.commit()
        
        return jsonify({
            "message": f"新規問合せ「{new_guest.last_name} 様」を登録しました。",
            "user_id": new_guest.id
        }), 201

    except IntegrityError as e:
        db.session.rollback()
        return jsonify({"error": "データベース制約違反です。", "details": str(e)}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "サーバー内部エラーが発生しました。", "details": str(e)}), 500
