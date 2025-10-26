from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models import (
    # 利用者関連に必要なモデルのみリストアップ
    Prospect, StatusMaster, ReferralSourceMaster, User, Supporter, 
    DailyLog, AttendanceStatusMaster, RoleMaster 
)
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from app.api.auth_routes import role_required

# Blueprintを作成
user_bp = Blueprint('user', __name__)

# ======================================================
# 1. 見込客登録 API (POST /api/prospects)
# ======================================================
@user_bp.route('/prospects', methods=['POST'])
def create_prospect():
    data = request.get_json()
    
    required_fields = ['last_name', 'first_name', 'status_name', 'referral_source_name']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "必須フィールドが不足しています。"}), 400

    try:
        # ステータスIDの取得
        status = StatusMaster.query.filter_by(
            name=data['status_name'], 
            category='prospect'
        ).first()
        if not status:
            return jsonify({"error": f"無効なステータス名です: {data['status_name']}"}), 400
            
        # 紹介元IDの取得
        referral_source = ReferralSourceMaster.query.filter_by(
            name=data['referral_source_name']
        ).first()
        if not referral_source:
            return jsonify({"error": f"無効な紹介元名です: {data['referral_source_name']}"}), 400
            
        new_prospect = Prospect(
            status_id=status.id,
            last_name=data['last_name'],
            first_name=data['first_name'],
            last_name_kana=data.get('last_name_kana'),
            first_name_kana=data.get('first_name_kana'),
            phone_number=data.get('phone_number'),
            email=data.get('email'),
            inquiry_date=datetime.strptime(data.get('inquiry_date'), '%Y-%m-%d').date() if data.get('inquiry_date') else datetime.utcnow().date(),
            referral_source_id=referral_source.id,
            referral_source_other=data.get('referral_source_other'),
            notes=data.get('notes'),
            remarks=data.get('remarks')
        )
        
        db.session.add(new_prospect)
        db.session.commit()
        
        return jsonify({
            "message": "見込み客を登録しました。",
            "id": new_prospect.id,
            "full_name": f"{new_prospect.last_name} {new_prospect.first_name}"
        }), 201

    except IntegrityError as e:
        db.session.rollback()
        return jsonify({"error": "データベース制約違反が発生しました。"}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"サーバーエラーが発生しました: {str(e)}"}), 500


# ======================================================
# 2. 利用者一覧取得 API (GET /api/users)
# ======================================================
@user_bp.route('/users', methods=['GET'])
def get_users():
    users = db.session.execute(
        db.select(
            User, 
            StatusMaster.name.label('status_name'), 
            Supporter.last_name.label('supporter_last_name'),
            Supporter.first_name.label('supporter_first_name')
        )
        .join(StatusMaster, User.status_id == StatusMaster.id)
        .outerjoin(Supporter, User.primary_supporter_id == Supporter.id)
        .order_by(User.id.asc())
    ).all()
    
    user_list = []
    for user_row in users:
        user = user_row[0]
        
        supporter_full_name = f"{user_row.supporter_last_name} {user_row.supporter_first_name}" if user_row.supporter_last_name else None

        user_list.append({
            "id": user.id,
            "full_name": f"{user.last_name} {user.first_name}",
            "full_name_kana": f"{user.last_name_kana or ''} {user.first_name_kana or ''}".strip(),
            "status": user_row.status_name,
            "primary_supporter": supporter_full_name,
            "created_at": user.created_at.isoformat() if user.created_at else None
        })
        
    return jsonify(user_list), 200

# ======================================================
# 3. 利用者詳細取得 API (GET /api/users/<id>)
# ======================================================
@user_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user_detail(user_id):
    # 1. 利用者基本情報の取得
    # SQLAlchemy 2.0 の SELECT 文で、User, StatusMaster, Supporter の情報を結合
    user = db.session.execute(
        db.select(
            User, 
            StatusMaster.name.label('status_name'),
            Supporter.last_name.label('supporter_last_name'),
            Supporter.first_name.label('supporter_first_name')
        )
        .join(StatusMaster, User.status_id == StatusMaster.id)
        .outerjoin(Supporter, User.primary_supporter_id == Supporter.id)
        .where(User.id == user_id)
    ).first()

    if not user:
        return jsonify({"error": f"利用者ID {user_id} のレコードは見つかりません。"}), 404

    user_data = user[0]
    
    # 2. 関連する日報履歴の取得 (直近10件)
    daily_logs = db.session.execute(
        db.select(DailyLog, Supporter.last_name.label('supporter_last_name'))
        .join(Supporter, DailyLog.supporter_id == Supporter.id)
        .where(DailyLog.user_id == user_id)
        .order_by(DailyLog.activity_date.desc())
        .limit(10)
    ).all()
    
    log_list = []
    for log_row in daily_logs:
        log = log_row[0]
        # AttendanceStatusMaster から名前を取得するためにクエリが必要
        attendance_status_name = AttendanceStatusMaster.query.get(log.attendance_status_id).name

        log_list.append({
            "log_id": log.id,
            "activity_date": log.activity_date.isoformat(),
            "attendance": attendance_status_name,
            "supporter_name": log_row.supporter_last_name,
            "summary": log.activity_summary[:50] + "..." if log.activity_summary and len(log.activity_summary) > 50 else log.activity_summary
        })

    # 3. 結果の統合と整形
    response = {
        "id": user_data.id,
        "full_name": f"{user_data.last_name} {user_data.first_name}",
        "status": user.status_name,
        "primary_supporter": f"{user.supporter_last_name} {user.supporter_first_name}" if user.supporter_last_name else None,
        "email": user_data.email,
        "primary_disorder": user_data.primary_disorder,
        "recent_logs": log_list
    }
    
    return jsonify(response), 200

# ======================================================
# 4. 利用者 PINコード設定 API (POST /api/users/<id>/set_pin)
# ======================================================
@user_bp.route('/users/<int:user_id>/set_pin', methods=['POST']) # ★ user_bp を使用 ★
@role_required(['サービス管理責任者', '管理者', '支援員']) 
def set_user_pin(user_id):
    data = request.get_json()
    pin_code = data.get('pin_code')
    
    if not pin_code:
        return jsonify({"error": "PINコードを入力してください。"}), 400

    if not pin_code.isdigit() or len(pin_code) < 4:
        return jsonify({"error": "PINコードは4桁以上の数字で入力してください。"}), 400

    try:
        user = db.session.get(User, user_id)
        if not user:
            return jsonify({"error": f"利用者ID {user_id} のレコードは見つかりません。"}), 404

        # PINコードをハッシュ化して保存 
        user.set_pin(pin_code) # User モデルのメソッドを使用
        db.session.commit()

        return jsonify({
            "message": f"利用者ID {user_id} のPINコードを安全に設定しました。",
            "user_id": user_id
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"サーバーエラーが発生しました: {str(e)}"}), 500
    

# ======================================================
# 5. 職員マスタ登録 API (POST /api/supporters)
# ======================================================
@user_bp.route('/supporters', methods=['POST'])
def create_supporter():
    data = request.get_json()
    
    required_fields = ['last_name', 'first_name', 'email', 'password', 'role_name']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "必須フィールドが不足しています。"}), 400

    try:
        # 1. ロールIDのルックアップ
        role = RoleMaster.query.filter_by(name=data['role_name']).first()
        if not role:
            return jsonify({"error": f"無効なロール名です: {data['role_name']}"}), 400

        # 2. メールアドレスの重複チェック
        if Supporter.query.filter_by(email=data['email']).first():
            return jsonify({"error": "このメールアドレスは既に使用されています。"}), 409

        # 3. 新しい Supporter オブジェクトを作成
        new_supporter = Supporter(
            last_name=data['last_name'],
            first_name=data['first_name'],
            email=data['email'],
            role_id=role.id,
            last_name_kana=data.get('last_name_kana'),
            first_name_kana=data.get('first_name_kana'),
            hire_date=datetime.strptime(data['hire_date'], '%Y-%m-%d').date() if data.get('hire_date') else None,
            remarks=data.get('remarks')
        )
        
        # 4. パスワードのハッシュ化と設定
        new_supporter.set_password(data['password'])
        
        # 5. データベースに保存
        db.session.add(new_supporter)
        db.session.commit()
        
        return jsonify({
            "message": f"{data['role_name']} 職員 {new_supporter.last_name} を登録しました。",
            "supporter_id": new_supporter.id,
            "role_id": role.id
        }), 201

    except ValueError:
        db.session.rollback()
        return jsonify({"error": "日付の形式が正しくありません (YYYY-MM-DD を使用してください)。"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"サーバーエラーが発生しました: {str(e)}"}), 500
    
