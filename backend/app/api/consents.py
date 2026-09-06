# backend/app/api/consents.py

import os
import datetime
from flask import Blueprint, request, jsonify, current_app, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity

from backend.app.extensions import db
from backend.app.services.core_service import parse_jwt_identity
from backend.app.services.document_consent_service import DocumentConsentService
from backend.app.models import (
    SupportPlan, MonthlyRetentionReport, DocumentConsentLog, DocumentDeliveryLog,
    OfficeSetting, User, JobRetentionContract
)


consents_bp = Blueprint('consents', __name__, url_prefix='/api/consents')
user_documents_bp = Blueprint('user_mypage_documents', __name__, url_prefix='/api/user-mypage/documents')


def get_upload_folder():
    folder = os.path.join(current_app.root_path, 'uploads', 'evidence')
    os.makedirs(folder, exist_ok=True)
    return folder


# ====================================================================
# 1. 職員向け文書確定 API
# ====================================================================

@consents_bp.route('/documents/<doc_type>/<int:doc_id>/finalize', methods=['POST'])
@jwt_required()
def finalize_document_api(doc_type: str, doc_id: int):
    """職員による文書確定処理。確定版スナップショットを固定する。"""
    role, supporter_id = parse_jwt_identity(get_jwt_identity())
    if role != 'staff':
        return jsonify({"msg": "Forbidden: 職員のみ文書確定が可能です。"}), 403

    try:
        res = DocumentConsentService.finalize_document(doc_type, doc_id, supporter_id)
        return jsonify({
            "msg": "文書を確定し、確定版スナップショットを固定しました。",
            "data": res
        }), 200
    except ValueError as e:
        return jsonify({"msg": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"文書確定に失敗しました: {e}"}), 500


# ====================================================================
# 2. 交付 API (電子配信 / 紙交付)
# ====================================================================

@consents_bp.route('/documents/<doc_type>/<int:doc_id>/deliver-digital', methods=['POST'])
@jwt_required()
def deliver_digital_api(doc_type: str, doc_id: int):
    """確定文書を本人アカウントへ電子交付（配信）する。"""
    role, supporter_id = parse_jwt_identity(get_jwt_identity())
    if role != 'staff':
        return jsonify({"msg": "Forbidden: 職員のみ交付操作が可能です。"}), 403

    try:
        delivery_log = DocumentConsentService.deliver_digital(doc_type, doc_id, supporter_id)
        return jsonify({
            "msg": "本人アカウントへ電子交付しました。",
            "delivery_log_id": delivery_log.id,
            "delivered_at": delivery_log.delivered_at.isoformat()
        }), 201
    except ValueError as e:
        return jsonify({"msg": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"電子交付に失敗しました: {e}"}), 500


@consents_bp.route('/documents/<doc_type>/<int:doc_id>/deliver-paper', methods=['POST'])
@jwt_required()
def deliver_paper_api(doc_type: str, doc_id: int):
    """確定文書を本人へ紙交付した事実を記録する。"""
    role, supporter_id = parse_jwt_identity(get_jwt_identity())
    if role != 'staff':
        return jsonify({"msg": "Forbidden: 職員のみ交付操作が可能です。"}), 403

    data = request.get_json() or {}
    delivered_at_str = data.get('delivered_at')
    delivered_at = None
    if delivered_at_str:
        try:
            delivered_at = datetime.date.fromisoformat(delivered_at_str)
        except ValueError:
            return jsonify({"msg": "交付日は YYYY-MM-DD 形式で指定してください。"}), 400

    try:
        delivery_log = DocumentConsentService.deliver_paper(doc_type, doc_id, supporter_id, delivered_at)
        return jsonify({
            "msg": "紙交付の記録を登録しました。",
            "delivery_log_id": delivery_log.id,
            "delivered_at": delivery_log.delivered_at.isoformat()
        }), 201
    except ValueError as e:
        return jsonify({"msg": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"紙交付の記録に失敗しました: {e}"}), 500


# ====================================================================
# 3. 署名・同意証跡 API (本人電子署名 / 紙署名アップロード)
# ====================================================================

@consents_bp.route('/digital-sign', methods=['POST'])
@jwt_required()
def digital_sign_api():
    """本人による電子署名 (USER_DIGITAL)。本人JWT認証(auth_user_id)で厳格検証。"""
    role, auth_user_id = parse_jwt_identity(get_jwt_identity())
    if role != 'user' or not auth_user_id:
        return jsonify({"msg": "Forbidden: 本人アカウントのみ電子署名可能です。"}), 403

    data = request.get_json() or {}
    doc_type = data.get('document_type')
    doc_id = data.get('document_id')

    if not doc_type or not doc_id:
        return jsonify({"msg": "document_type および document_id は必須です。"}), 400

    try:
        consent_log = DocumentConsentService.sign_digitally(doc_type, doc_id, auth_user_id)
        return jsonify({
            "msg": "電子署名・同意が完了しました。",
            "consent_log_id": consent_log.id,
            "signature_method": consent_log.signature_method,
            "signed_at": consent_log.consent_timestamp.isoformat()
        }), 200
    except PermissionError as e:
        return jsonify({"msg": str(e)}), 403
    except ValueError as e:
        return jsonify({"msg": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"電子署名に失敗しました: {e}"}), 500


@consents_bp.route('/paper-upload', methods=['POST'])
@jwt_required()
def paper_upload_api():
    """紙署名＋職員アップロード (PAPER_UPLOAD)。署名済み画像/PDFが必須。"""
    role, supporter_id = parse_jwt_identity(get_jwt_identity())
    if role != 'staff':
        return jsonify({"msg": "Forbidden: 職員のみ紙署名証憑を登録可能です。"}), 403

    doc_type = request.form.get('document_type')
    doc_id_str = request.form.get('document_id')
    signed_at_str = request.form.get('signed_at')
    file = request.files.get('evidence_file')

    if not doc_type or not doc_id_str:
        return jsonify({"msg": "document_type および document_id は必須です。"}), 400

    try:
        doc_id = int(doc_id_str)
    except ValueError:
        return jsonify({"msg": "document_id は整数である必要があります。"}), 400

    if not signed_at_str:
        return jsonify({"msg": "署名日 (signed_at) は必須です。"}), 400

    try:
        signed_at = datetime.date.fromisoformat(signed_at_str)
    except ValueError:
        return jsonify({"msg": "署名日は YYYY-MM-DD 形式で指定してください。"}), 400

    if not file or not file.filename:
        return jsonify({"msg": "署名済みの証拠ファイル（画像またはPDF）は必須です。"}), 400

    try:
        upload_folder = get_upload_folder()
        consent_log = DocumentConsentService.upload_paper_signature(
            document_type=doc_type,
            document_id=doc_id,
            supporter_id=supporter_id,
            signed_at=signed_at,
            file_storage=file,
            upload_folder=upload_folder
        )
        return jsonify({
            "msg": "紙署名証憑を登録し、署名完了として処理しました。",
            "consent_log_id": consent_log.id,
            "signature_method": consent_log.signature_method,
            "evidence_file_url": consent_log.evidence_file_url,
            "signed_at": consent_log.consent_timestamp.isoformat()
        }), 201
    except ValueError as e:
        return jsonify({"msg": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"紙署名証憑の登録に失敗しました: {e}"}), 500


# ====================================================================
# 4. 文書状態・交付・署名情報取得 API
# ====================================================================

@consents_bp.route('/documents/<doc_type>/<int:doc_id>/status', methods=['GET'])
@jwt_required()
def get_document_status_api(doc_type: str, doc_id: int):
    """文書の現在の確定状態、交付履歴、同意証跡、電子署名可否判定を取得する。"""
    office_id = DocumentConsentService.get_office_id_for_document(doc_type, doc_id)
    target_user_id = None
    doc_status = None
    doc_version = 1
    has_snapshot = False

    if doc_type == 'SUPPORT_PLAN':
        plan = db.session.get(SupportPlan, doc_id)
        if not plan:
            return jsonify({"msg": "個別支援計画が見つかりません。"}), 404
        target_user_id = plan.user_id
        doc_status = plan.plan_status
        doc_version = plan.plan_version
        has_snapshot = plan.document_snapshot is not None

    elif doc_type == 'RETENTION_SUPPORT_REPORT':
        report = db.session.get(MonthlyRetentionReport, doc_id)
        if not report:
            return jsonify({"msg": "支援レポートが見つかりません。"}), 404
        target_user_id = report.contract.user_id
        doc_status = report.status
        doc_version = 1
        has_snapshot = report.document_snapshot is not None

    # can_user_sign_digitally 判定
    can_sign_digitally = False
    if target_user_id and office_id:
        can_sign_digitally = DocumentConsentService.can_user_sign_digitally(target_user_id, office_id)

    # 交付履歴
    deliveries = DocumentDeliveryLog.query.filter_by(
        document_type=doc_type,
        document_id=doc_id,
        document_version=doc_version
    ).order_by(DocumentDeliveryLog.delivered_at.asc()).all()

    delivery_list = [
        {
            "id": d.id,
            "delivery_method": d.delivery_method,
            "delivered_at": d.delivered_at.isoformat() if d.delivered_at else None,
            "viewed_at": d.viewed_at.isoformat() if d.viewed_at else None,
            "delivered_by_name": d.delivered_by.name if d.delivered_by else None
        }
        for d in deliveries
    ]

    # 同意証跡
    consents = DocumentConsentLog.query.filter_by(
        document_type=doc_type,
        document_id=doc_id,
        document_version=doc_version
    ).order_by(DocumentConsentLog.recorded_at.desc()).all()

    consent_list = [
        {
            "id": c.id,
            "action": c.action,
            "signature_method": c.signature_method,
            "consent_timestamp": c.consent_timestamp.isoformat() if c.consent_timestamp else None,
            "evidence_file_url": c.evidence_file_url,
            "recorded_by_name": c.recorded_by_supporter.name if c.recorded_by_supporter else None,
            "recorded_at": c.recorded_at.isoformat() if c.recorded_at else None
        }
        for c in consents
    ]

    return jsonify({
        "document_type": doc_type,
        "document_id": doc_id,
        "document_version": doc_version,
        "status": doc_status,
        "has_snapshot": has_snapshot,
        "can_sign_digitally": can_sign_digitally,
        "deliveries": delivery_list,
        "consents": consent_list,
        "is_delivered": len(delivery_list) > 0,
        "is_signed": len(consent_list) > 0
    }), 200


@consents_bp.route('/evidence/<filename>', methods=['GET'])
@jwt_required()
def get_evidence_file(filename: str):
    """紙署名証拠ファイルの安全な配信"""
    upload_folder = get_upload_folder()
    return send_from_directory(upload_folder, filename)


# ====================================================================
# 5. 利用者マイページ文書 API
# ====================================================================

@user_documents_bp.route('/pending', methods=['GET'])
@jwt_required()
def get_user_pending_documents():
    """本人アカウント宛の未署名・未確認文書一覧"""
    role, auth_user_id = parse_jwt_identity(get_jwt_identity())
    if role != 'user' or not auth_user_id:
        return jsonify({"msg": "Forbidden: 本人アカウントのみアクセス可能です。"}), 403

    # 1. 署名待ち計画 (PENDING_CONSENT で本人がまだ署名していないもの)
    pending_plans = SupportPlan.query.filter_by(
        user_id=auth_user_id,
        plan_status='PENDING_CONSENT'
    ).all()

    plan_items = []
    for p in pending_plans:
        # すでに本人の同意ログが存在しないか確認
        has_consent = DocumentConsentLog.query.filter_by(
            document_type='SUPPORT_PLAN',
            document_id=p.id,
            document_version=p.plan_version,
            user_id=auth_user_id
        ).first() is not None

        if not has_consent:
            # 電子交付ログがあるか確認
            delivery = DocumentDeliveryLog.query.filter_by(
                document_type='SUPPORT_PLAN',
                document_id=p.id,
                document_version=p.plan_version,
                recipient_user_id=auth_user_id,
                delivery_method='DIGITAL'
            ).first()

            plan_items.append({
                "document_type": "SUPPORT_PLAN",
                "document_id": p.id,
                "document_version": p.plan_version,
                "title": f"個別支援計画 第{p.plan_version}版" + (" (就労定着支援)" if p.retention_detail else ""),
                "delivered_at": delivery.delivered_at.isoformat() if delivery else None,
                "action_required": "CONSENT",
                "is_retention_plan": p.retention_detail is not None
            })

    # 2. 未確認レポート (FINALIZED で本人がまだ確認していないもの)
    unack_reports = MonthlyRetentionReport.query.join(
        JobRetentionContract, MonthlyRetentionReport.contract_id == JobRetentionContract.id
    ).filter(
        JobRetentionContract.user_id == auth_user_id,
        MonthlyRetentionReport.status == 'FINALIZED'
    ).all()

    report_items = []
    for r in unack_reports:
        has_ack = DocumentConsentLog.query.filter_by(
            document_type='RETENTION_SUPPORT_REPORT',
            document_id=r.id,
            user_id=auth_user_id,
            action='ACKNOWLEDGEMENT'
        ).first() is not None

        if not has_ack:
            delivery = DocumentDeliveryLog.query.filter_by(
                document_type='RETENTION_SUPPORT_REPORT',
                document_id=r.id,
                recipient_user_id=auth_user_id,
                delivery_method='DIGITAL'
            ).first()

            report_items.append({
                "document_type": "RETENTION_SUPPORT_REPORT",
                "document_id": r.id,
                "document_version": 1,
                "title": f"就労定着支援状況報告書 ({r.report_year_month})",
                "delivered_at": delivery.delivered_at.isoformat() if delivery else None,
                "action_required": "ACKNOWLEDGEMENT"
            })

    return jsonify({
        "pending_documents": plan_items + report_items
    }), 200


@user_documents_bp.route('/delivered', methods=['GET'])
@jwt_required()
def get_user_delivered_documents():
    """本人アカウントへ電子交付された文書一覧（閲覧可能文書）"""
    role, auth_user_id = parse_jwt_identity(get_jwt_identity())
    if role != 'user' or not auth_user_id:
        return jsonify({"msg": "Forbidden: 本人アカウントのみアクセス可能です。"}), 403

    digital_deliveries = DocumentDeliveryLog.query.filter_by(
        recipient_user_id=auth_user_id,
        delivery_method='DIGITAL'
    ).order_by(DocumentDeliveryLog.delivered_at.desc()).all()

    items = []
    for d in digital_deliveries:
        title = ""
        status_label = ""
        is_signed = False

        if d.document_type == 'SUPPORT_PLAN':
            plan = db.session.get(SupportPlan, d.document_id)
            if plan:
                title = f"個別支援計画 第{d.document_version}版" + (" (就労定着支援)" if plan.retention_detail else "")
                status_label = plan.plan_status
                # 署名ログ
                consent = DocumentConsentLog.query.filter_by(
                    document_type='SUPPORT_PLAN',
                    document_id=d.document_id,
                    document_version=d.document_version,
                    user_id=auth_user_id
                ).first()
                is_signed = consent is not None
        elif d.document_type == 'RETENTION_SUPPORT_REPORT':
            report = db.session.get(MonthlyRetentionReport, d.document_id)
            if report:
                title = f"就労定着支援状況報告書 ({report.report_year_month})"
                status_label = report.status
                consent = DocumentConsentLog.query.filter_by(
                    document_type='RETENTION_SUPPORT_REPORT',
                    document_id=d.document_id,
                    user_id=auth_user_id
                ).first()
                is_signed = consent is not None

        items.append({
            "delivery_id": d.id,
            "document_type": d.document_type,
            "document_id": d.document_id,
            "document_version": d.document_version,
            "title": title,
            "delivered_at": d.delivered_at.isoformat() if d.delivered_at else None,
            "viewed_at": d.viewed_at.isoformat() if d.viewed_at else None,
            "status": status_label,
            "is_signed": is_signed
        })

    return jsonify({
        "delivered_documents": items
    }), 200


@user_documents_bp.route('/<doc_type>/<int:doc_id>/rendered', methods=['GET'])
@jwt_required()
def get_rendered_document(doc_type: str, doc_id: int):
    """
    確定版スナップショットに基づく文書データ取得（A4帳票閲覧・印刷用）。
    本人が実際に開いた瞬間に viewed_at を自動記録する。
    """
    role, auth_id = parse_jwt_identity(get_jwt_identity())
    snapshot = None
    target_user_id = None

    if doc_type == 'SUPPORT_PLAN':
        plan = db.session.get(SupportPlan, doc_id)
        if not plan:
            return jsonify({"msg": "個別支援計画が見つかりません。"}), 404
        target_user_id = plan.user_id

        # 権限チェック (職員または対象本人)
        if role == 'user' and auth_id != target_user_id:
            return jsonify({"msg": "Forbidden: 他の利用者の文書は閲覧できません。"}), 403

        # スナップショットがあればそれを唯一のSource of Truthとして使用
        if plan.document_snapshot:
            snapshot = plan.document_snapshot
        else:
            # 確定前（DRAFT）の場合はリアルタイム生成
            snapshot = DocumentConsentService.generate_document_snapshot(doc_type, doc_id)

    elif doc_type == 'RETENTION_SUPPORT_REPORT':
        report = db.session.get(MonthlyRetentionReport, doc_id)
        if not report:
            return jsonify({"msg": "支援レポートが見つかりません。"}), 404
        target_user_id = report.contract.user_id

        if role == 'user' and auth_id != target_user_id:
            return jsonify({"msg": "Forbidden: 他の利用者のレポートは閲覧できません。"}), 403

        if report.document_snapshot:
            snapshot = report.document_snapshot
        else:
            snapshot = DocumentConsentService.generate_document_snapshot(doc_type, doc_id)
    else:
        return jsonify({"msg": "未対応の文書種別です。"}), 400

    # 本人が閲覧した場合に viewed_at を記録（一覧取得やprefetchでは記録されない）
    if role == 'user' and auth_id == target_user_id:
        DocumentConsentService.record_document_viewed(doc_type, doc_id, auth_id)

    # 署名・同意情報も付加
    consent = DocumentConsentLog.query.filter_by(
        document_type=doc_type,
        document_id=doc_id
    ).order_by(DocumentConsentLog.recorded_at.desc()).first()

    consent_info = None
    if consent:
        consent_info = {
            "signature_method": consent.signature_method,
            "action": consent.action,
            "consent_timestamp": consent.consent_timestamp.isoformat() if consent.consent_timestamp else None,
            "evidence_file_url": consent.evidence_file_url
        }

    return jsonify({
        "document_type": doc_type,
        "document_id": doc_id,
        "snapshot": snapshot,
        "consent": consent_info
    }), 200
