# app/api/record_routes.py

from flask import Blueprint, request, jsonify
from app.extensions import db
from datetime import datetime, time, date # ★ dateも必要
from sqlalchemy.exc import IntegrityError
from app.api.auth_routes import role_required 
from flask_jwt_extended import get_jwt_identity # ★ 削除ログのために追加
from sqlalchemy import select # ★ select をインポート

# --- V1.1 モデルのインポート ---
from app.models.core import User, Supporter
from app.models.master import ServiceLocationMaster
from app.models.records import ServiceRecord, BreakRecord, RecordSupporter
from app.models.schedule import Schedule
from app.models.audit_log import SystemLog # ★ 削除ログのために追加

# Blueprintを作成
record_bp = Blueprint('record', __name__)

# ======================================================
# 1. 実績記録 新規作成 API (POST /api/records)
# ======================================================
@record_bp.route('/records', methods=['POST'])
@role_required(['SystemAdmin', 'OfficeAdmin', 'Sabikan', 'Staff']) # 職員なら誰でも記録可能
def create_service_record():
    """
    日々のサービス提供記録（施設内、在宅、施設外就労）を登録します。
    ServiceRecordモデルに統一されています。
    """
    data = request.get_json()
    supporter_id = int(get_jwt_identity()) # 記録者

    # 1. 必須フィールドの検証
    required_fields = [
        'user_id', 
        'service_location_id', # ★ どこで (施設内/在宅/施設外就労)
        'record_date',
        'start_time',
        'end_time',
        'service_type' # 例: '個別訓練', 'SST', '施設外就労'
    ]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "必須フィールドが不足しています。"}), 400

    try:
        # 2. 外部キー（ID）の存在チェック
        user = db.session.get(User, data['user_id'])
        if not user:
            return jsonify({"error": f"無効な利用者IDです: {data['user_id']}"}), 404
            
        location = db.session.get(ServiceLocationMaster, data['service_location_id'])
        if not location:
            return jsonify({"error": f"無効な場所IDです: {data['service_location_id']}"}), 404

        # 3. 時間のパースと総時間の計算
        start_time_obj = datetime.strptime(data['start_time'], '%H:%M').time()
        end_time_obj = datetime.strptime(data['end_time'], '%H:%M').time()
        record_date_obj = datetime.strptime(data['record_date'], '%Y-%m-%d').date()
        
        # 総時間（分）の計算
        start_dt = datetime.combine(record_date_obj, start_time_obj)
        end_dt = datetime.combine(record_date_obj, end_time_obj)
        if end_dt <= start_dt:
            return jsonify({"error": "終了時刻は開始時刻より後でなければなりません。"}), 400
            
        total_duration_minutes = (end_dt - start_dt).total_seconds() / 60

        # 4. ServiceRecordオブジェクトの作成
        new_record = ServiceRecord(
            user_id=data['user_id'],
            service_location_id=data['service_location_id'],
            record_date=record_date_obj,
            start_time=start_time_obj,
            end_time=end_time_obj,
            service_duration_minutes=total_duration_minutes, # ★ 総時間
            
            service_type=data['service_type'],
            service_content=data.get('service_content', ''), # 任意
            
            # 証憑 (デフォルト値)
            is_approved=data.get('is_approved', False), # 職員の承認
            is_billable=data.get('is_billable', True),  # 請求対象
            user_confirmed_at=None # 利用者確認はまだ
        )
        db.session.add(new_record)
        db.session.flush() # new_record.id を確定

        # 5. 休憩記録 (BreakRecord) の処理
        total_break_minutes = 0
        if 'breaks' in data and isinstance(data['breaks'], list):
            for break_data in data['breaks']:
                break_start = datetime.strptime(break_data['start_time'], '%H:%M').time()
                break_end = datetime.strptime(break_data['end_time'], '%H:%M').time()
                break_duration = (datetime.combine(date.today(), break_end) - datetime.combine(date.today(), break_start)).total_seconds() / 60
                
                if break_duration <= 0:
                    continue # 無効な休憩データは無視

                total_break_minutes += break_duration
                new_break = BreakRecord(
                    service_record_id=new_record.id, # ★ 作成した実績に紐づく
                    break_type=break_data.get('break_type', '休憩'),
                    start_time=break_start,
                    end_time=break_end,
                    duration_minutes=int(break_duration),
                    supporter_id=supporter_id # 承認した職員
                )
                db.session.add(new_break)
        
        # 6. 担当職員 (RecordSupporter) の処理 (記録者自身を登録)
        new_record_supporter = RecordSupporter(
            service_record_id=new_record.id,
            supporter_id=supporter_id,
            is_primary=True # 記録者が主担当
        )
        db.session.add(new_record_supporter)

        # 7. (オプション) 総時間から休憩時間を引いて実働時間を計算
        # new_record.service_duration_minutes = total_duration_minutes - total_break_minutes
        # db.session.add(new_record)
        
        db.session.commit()
        
        return jsonify({
            "message": f"{user.display_name}様の {location.location_name} での実績を登録しました。",
            "record_id": new_record.id
        }), 201

    except IntegrityError as e:
        db.session.rollback()
        return jsonify({"error": "データベース制約違反が発生しました。", "details": str(e)}), 409
    except ValueError:
        db.session.rollback()
        return jsonify({"error": "日付または時刻の形式が正しくありません (日付: YYYY-MM-DD, 時刻: HH:MM)。"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "サーバー内部エラーが発生しました。", "details": str(e)}), 500

# ======================================================
# 2. 利用者別・実績記録一覧 API (GET /api/users/<int:user_id>/records)
# ======================================================
@record_bp.route('/users/<int:user_id>/records', methods=['GET'])
@role_required(['SystemAdmin', 'OfficeAdmin', 'Sabikan', 'Staff'])
def get_records_for_user(user_id):
    """
    特定の利用者のサービス提供記録（ServiceRecord）の一覧を取得します。
    """
    # 0. 期間指定 (オプション)
    # (例: /api/users/1/records?start_date=2025-11-01&end_date=2025-11-30)
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    try:
        # 1. データベースクエリの構築
        stmt = (
            db.select(
                ServiceRecord,
                ServiceLocationMaster.location_name
            )
            .join(ServiceLocationMaster, ServiceRecord.service_location_id == ServiceLocationMaster.id)
            .where(ServiceRecord.user_id == user_id)
            .order_by(ServiceRecord.record_date.desc(), ServiceRecord.start_time.desc())
        )

        # 2. 期間指定があれば絞り込み
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            stmt = stmt.where(ServiceRecord.record_date >= start_date)
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            stmt = stmt.where(ServiceRecord.record_date <= end_date)

        records_result = db.session.execute(stmt).all()

        # 3. JSONレスポンスに整形
        record_list = []
        for row in records_result:
            record = row.ServiceRecord
            record_list.append({
                "record_id": record.id,
                "record_date": record.record_date.isoformat(),
                "start_time": record.start_time.strftime('%H:%M'),
                "end_time": record.end_time.strftime('%H:%M'),
                "service_duration_minutes": record.service_duration_minutes,
                "location_name": row.location_name,
                "service_type": record.service_type,
                "is_approved": record.is_approved,
                "user_confirmed_at": record.user_confirmed_at.isoformat() if record.user_confirmed_at else None
            })

        return jsonify(record_list), 200

    except ValueError:
        return jsonify({"error": "日付の形式が正しくありません (YYYY-MM-DD)。"}), 400
    except Exception as e:
        return jsonify({"error": "サーバー内部エラーが発生しました。", "details": str(e)}), 500

# ======================================================
# 3. 実績記録詳細 API (GET /api/records/<int:record_id>)
# ======================================================
@record_bp.route('/records/<int:record_id>', methods=['GET'])
@role_required(['SystemAdmin', 'OfficeAdmin', 'Sabikan', 'Staff'])
def get_record_detail(record_id):
    """
    単一のサービス提供記録（ServiceRecord）の詳細を取得します。
    休憩記録（BreakRecord）や担当職員（RecordSupporter）も結合します。
    """
    try:
        # 1. メインの実績記録を取得
        stmt = (
            db.select(
                ServiceRecord,
                ServiceLocationMaster.location_name
            )
            .join(ServiceLocationMaster, ServiceRecord.service_location_id == ServiceLocationMaster.id)
            .where(ServiceRecord.id == record_id)
        )
        record_result = db.session.execute(stmt).first()

        if not record_result:
            return jsonify({"error": "実績記録が見つかりません。"}), 404

        record = record_result.ServiceRecord
        
        response_data = {
            "record_id": record.id,
            "user_id": record.user_id,
            "record_date": record.record_date.isoformat(),
            "start_time": record.start_time.strftime('%H:%M'),
            "end_time": record.end_time.strftime('%H:%M'),
            "service_duration_minutes": record.service_duration_minutes,
            "location_name": record_result.location_name,
            "service_location_id": record.service_location_id,
            "service_type": record.service_type,
            "service_content": record.service_content,
            "is_approved": record.is_approved,
            "is_billable": record.is_billable,
            "user_confirmed_at": record.user_confirmed_at.isoformat() if record.user_confirmed_at else None
        }

        # 2. 紐づく「休憩記録」を取得
        breaks = db.session.execute(
            db.select(BreakRecord).where(BreakRecord.service_record_id == record_id)
        ).scalars().all()
        
        response_data['breaks'] = [
            {
                "break_id": br.id,
                "break_type": br.break_type,
                "start_time": br.start_time.strftime('%H:%M'),
                "end_time": br.end_time.strftime('%H:%M'),
                "duration_minutes": br.duration_minutes
            }
            for br in breaks
        ]

        # 3. 紐づく「担当職員」を取得
        supporters = db.session.execute(
            db.select(Supporter.last_name, Supporter.first_name, RecordSupporter.is_primary)
            .join(Supporter, RecordSupporter.supporter_id == Supporter.id)
            .where(RecordSupporter.service_record_id == record_id)
        ).all()
        
        response_data['supporters'] = [
            {
                "full_name": f"{s.last_name} {s.first_name}",
                "is_primary": s.is_primary
            }
            for s in supporters
        ]

        return jsonify(response_data), 200

    except Exception as e:
        return jsonify({"error": "サーバー内部エラーが発生しました。", "details": str(e)}), 500

# ======================================================
# 4. 実績記録 更新 API (PUT /api/records/<int:record_id>)
# ======================================================
@record_bp.route('/records/<int:record_id>', methods=['PUT'])
@role_required(['SystemAdmin', 'OfficeAdmin', 'Sabikan', 'Staff'])
def update_service_record(record_id):
    """
    既存のサービス提供記録を更新します。
    休憩記録（Breaks）も一度クリアし、再作成します。
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "更新データがありません。"}), 400

    supporter_id = int(get_jwt_identity()) # 編集者

    try:
        # 1. 更新対象の記録を検索
        record = db.session.get(ServiceRecord, record_id)
        if not record:
            return jsonify({"error": "実績記録が見つかりません。"}), 404
            
        # 2. 外部キー（ID）の存在チェック (変更がある場合のみ)
        if 'user_id' in data and data['user_id'] != record.user_id:
            if not db.session.get(User, data['user_id']):
                return jsonify({"error": f"無効な利用者IDです: {data['user_id']}"}), 404
            record.user_id = data['user_id']
            
        if 'service_location_id' in data and data['service_location_id'] != record.service_location_id:
            if not db.session.get(ServiceLocationMaster, data['service_location_id']):
                return jsonify({"error": f"無効な場所IDです: {data['service_location_id']}"}), 404
            record.service_location_id = data['service_location_id']

        # 3. 時間のパースと総時間の再計算
        record_date_obj = datetime.strptime(data.get('record_date', record.record_date.isoformat()), '%Y-%m-%d').date()
        start_time_obj = datetime.strptime(data.get('start_time', record.start_time.strftime('%H:%M')), '%H:%M').time()
        end_time_obj = datetime.strptime(data.get('end_time', record.end_time.strftime('%H:%M')), '%H:%M').time()
        
        start_dt = datetime.combine(record_date_obj, start_time_obj)
        end_dt = datetime.combine(record_date_obj, end_time_obj)
        if end_dt <= start_dt:
            return jsonify({"error": "終了時刻は開始時刻より後でなければなりません。"}), 400
            
        total_duration_minutes = (end_dt - start_dt).total_seconds() / 60

        # 4. ServiceRecordの基本情報を更新
        record.record_date = record_date_obj
        record.start_time = start_time_obj
        record.end_time = end_time_obj
        record.service_duration_minutes = total_duration_minutes
        record.service_type = data.get('service_type', record.service_type)
        record.service_content = data.get('service_content', record.service_content)
        record.is_approved = data.get('is_approved', record.is_approved)
        record.is_billable = data.get('is_billable', record.is_billable)
        # (user_confirmed_at は別の専用APIで更新するため、ここでは触らない)
        
        # 5. 休憩記録 (BreakRecord) の更新 (既存を全削除 -> 新規作成)
        # (モデルで cascade="all, delete-orphan" が設定されているため、 .clear() でDBから削除される)
        record.break_records.clear() 
        
        if 'breaks' in data and isinstance(data['breaks'], list):
            for break_data in data['breaks']:
                break_start = datetime.strptime(break_data['start_time'], '%H:%M').time()
                break_end = datetime.strptime(break_data['end_time'], '%H:%M').time()
                break_duration = (datetime.combine(date.today(), break_end) - datetime.combine(date.today(), break_start)).total_seconds() / 60
                
                if break_duration <= 0: continue

                new_break = BreakRecord(
                    service_record_id=record.id,
                    break_type=break_data.get('break_type', '休憩'),
                    start_time=break_start,
                    end_time=break_end,
                    duration_minutes=int(break_duration),
                    supporter_id=supporter_id
                )
                db.session.add(new_break)
        
        # 6. 担当職員 (RecordSupporter) の更新 (簡易的に、記録者を主担当として更新)
        # (※ 本来は RecordSupporter も専用APIで管理すべきだが、ここでは簡易化)
        existing_supporter_link = db.session.execute(
            db.select(RecordSupporter).where(RecordSupporter.service_record_id == record.id)
        ).scalar_one_or_none()
        
        if existing_supporter_link:
            existing_supporter_link.supporter_id = supporter_id # 編集者に上書き
            db.session.add(existing_supporter_link)
        
        db.session.commit()
        
        return jsonify({
            "message": f"実績記録 (ID: {record_id}) を更新しました。",
            "record_id": record.id
        }), 200

    except IntegrityError as e:
        db.session.rollback()
        return jsonify({"error": "データベース制約違反が発生しました。", "details": str(e)}), 409
    except ValueError:
        db.session.rollback()
        return jsonify({"error": "日付または時刻の形式が正しくありません (日付: YYYY-MM-DD, 時刻: HH:MM)。"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "サーバー内部エラーが発生しました。", "details": str(e)}), 500

# ======================================================
# 5. 実績記録 削除 API (DELETE /api/records/<int:record_id>)
# ======================================================
@record_bp.route('/records/<int:record_id>', methods=['DELETE'])
@role_required(['SystemAdmin', 'OfficeAdmin', 'Sabikan']) # ★ 削除はサビ管以上に制限
def delete_service_record(record_id):
    """
    [サビ管以上] サービス提供記録を削除します。
    関連する休憩、担当者、加算もすべて削除されます（カスケード削除）。
    削除の事実は監査ログ（SystemLog）に記録されます。
    """
    supporter_id = int(get_jwt_identity()) # 削除実行者

    try:
        record = db.session.get(ServiceRecord, record_id)
        if not record:
            return jsonify({"error": "実績記録が見つかりません。"}), 404

        # 1. 監査ログ（SystemLog）に「削除の事実」を先に記録する
        log_detail = (
            f"実績記録ID {record.id} (利用者ID: {record.user_id}, "
            f"日付: {record.record_date.isoformat()}, "
            f"内容: {record.service_type}) が職員ID {supporter_id} により削除されました。"
        )
        
        new_log = SystemLog(
            action="SERVICE_RECORD_DELETED",
            supporter_id=supporter_id,
            user_id=record.user_id, # 削除対象の利用者ID
            details=log_detail
        )
        db.session.add(new_log)

        # 2. 実績記録（ServiceRecord）を削除する
        # (関連する BreakRecord, RecordSupporter, ServiceRecordAdditive は、
        #  モデル定義の cascade="all, delete-orphan" により自動的に削除されます)
        db.session.delete(record)
        
        db.session.commit()
        
        return jsonify({"message": f"実績記録 (ID: {record_id}) を削除し、監査ログに記録しました。"}), 200

    except IntegrityError as e:
        db.session.rollback()
        # (通常、DELETEではIntegrityErrorは起きにくいが、念のため)
        return jsonify({"error": "データベース制約違反（他の記録がこの記録を参照している）が発生しました。", "details": str(e)}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "サーバー内部エラーが発生しました。", "details": str(e)}), 500
    
