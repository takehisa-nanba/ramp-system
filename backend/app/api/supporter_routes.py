# app/api/supporter_routes.py

from flask import Blueprint, request, jsonify
from app.extensions import db
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from app.api.auth_routes import role_required # 認証デコレーター

# --- V1.1 モデルのインポート ---
from app.models.core import Supporter
from app.models.master import RoleMaster, JobTitleMaster # ★ JobTitleMasterを追加
from app.models.hr import SupporterJobAssignment # ★ SupporterJobAssignmentを追加
from app.models.office_admin import OfficeSetting # ★ OfficeSettingを追加

# Blueprintを作成
supporter_bp = Blueprint('supporter', __name__)

# ======================================================
# 1. 職員新規登録 API (POST /api/supporters)
# ======================================================
@supporter_bp.route('/supporters', methods=['POST'])
# ★ 修正: 権限を「システム管理者」に限定
@role_required(['SystemAdmin'])
def create_supporter():
    """
    [SystemAdmin用] 新しい職員アカウントを登録します。
    3つのロール（システム・組織・職務）も同時に設定します。
    """
    data = request.get_json()
    
    # 1. 必須フィールドの検証
    # ★ 修正: 3ロールの指定を必須にする
    required_fields = [
        'last_name', 'first_name', 'email', 'password', # 基本情報
        'system_role_name',  # ① システムロール (例: 'Staff')
        'office_id',         # ③ 組織ロール（所属事業所ID）
        'job_title_name'     # ② 法令上の職務 (例: '生活支援員')
    ]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "必須フィールド（氏名, email, password, 3ロール指定）が不足しています。"}), 400

    try:
        # 2. ロールIDのルックアップ (3ロール)
        # ① システム・ロール
        role = RoleMaster.query.filter_by(name=data['system_role_name']).first()
        if not role:
            return jsonify({"error": f"無効なシステムロール名です: {data['system_role_name']}"}), 400

        # ③ 組織ロール（所属事業所）
        office = db.session.get(OfficeSetting, data['office_id'])
        if not office:
             return jsonify({"error": f"無効な事業所IDです: {data['office_id']}"}), 400

        # ② 法令上の職務
        job_title = JobTitleMaster.query.filter_by(name=data['job_title_name']).first()
        if not job_title:
             return jsonify({"error": f"無効な職務名です: {data['job_title_name']}"}), 400

        # 3. メールアドレスの重複チェック
        if Supporter.query.filter_by(email=data['email']).first():
            return jsonify({"error": "このメールアドレスは既に使用されています。"}), 409

        # 4. 新しい Supporter オブジェクトを作成
        new_supporter = Supporter(
            last_name=data['last_name'],
            first_name=data['first_name'],
            email=data['email'],
            
            # ★ 3ロールの紐付け
            role_id=role.id,       # ① システム・ロール
            office_id=office.id,   # ③ 組織ロール
            
            # (任意項目)
            last_name_kana=data.get('last_name_kana'),
            first_name_kana=data.get('first_name_kana'),
            hire_date=datetime.strptime(data['hire_date'], '%Y-%m-%d').date() if data.get('hire_date') else datetime.utcnow().date(),
            seal_image_url=data.get('seal_image_url'),
            is_full_time=data.get('is_full_time', False),
            scheduled_work_hours=data.get('scheduled_work_hours', 40),
            employment_type=data.get('employment_type', '正社員'),
            remarks=data.get('remarks')
        )
        
        # 5. パスワードのハッシュ化と設定
        new_supporter.set_password(data['password'])
        
        db.session.add(new_supporter)
        db.session.flush() # ★ SupporterのIDを確定させる

        # 6. ★ 新規追加: 法令上の職務（JobAssignment）の履歴を作成
        new_assignment = SupporterJobAssignment(
            supporter_id=new_supporter.id,
            job_title_id=job_title.id,
            start_date=new_supporter.hire_date, # 雇用日を開始日とする
            end_date=None # 終了日未定
        )
        db.session.add(new_assignment)
        
        # 7. データベースに保存
        db.session.commit()
        
        return jsonify({
            "message": f"{new_supporter.last_name} 様を職員として登録しました。",
            "supporter_id": new_supporter.id,
            "system_role": role.name,
            "office_name": office.office_name,
            "job_title": job_title.name
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
    # (★ このAPIは変更なし ★)
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
