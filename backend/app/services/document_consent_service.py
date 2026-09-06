# backend/app/services/document_consent_service.py

import os
import uuid
import datetime
from typing import Optional, Dict, Any, List
from werkzeug.utils import secure_filename
from sqlalchemy import func

from backend.app.extensions import db
from backend.app.models import (
    User, Supporter, OfficeSetting, OfficeServiceConfiguration,
    SupportPlan, MonthlyRetentionReport, DocumentConsentLog, DocumentDeliveryLog,
    AuditActionLog
)
from backend.app.models.support.job_retention import JobRetentionContract, RetentionSupportPlan


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


class DocumentConsentService:
    """
    確定文書の交付・閲覧・署名証跡を統括する共通サービスクラス。
    電子交付・本人電子署名(USER_DIGITAL)と紙交付・紙署名証拠アップロード(PAPER_UPLOAD)
    を同一の監査証跡基盤へ安全に合流させる。
    """

    @staticmethod
    def can_user_sign_digitally(user_id: int, office_id: int) -> bool:
        """
        事業所標準、利用者例外、本人認証状態を評価し、
        利用者が現時点でRAMPSystem上で電子署名可能かを判定する（Fail Closed）。
        """
        office = db.session.get(OfficeSetting, office_id)
        if not office or not office.electronic_document_enabled:
            return False

        user = db.session.get(User, user_id)
        if not user or user.deleted_at is not None:
            return False

        if user.electronic_document_opt_out:
            return False

        if not user.pii or not user.pii.password_hash:
            return False

        if not (user.user_code or user.pii.email):
            return False

        return True

    @staticmethod
    def get_office_id_for_document(document_type: str, document_id: int) -> Optional[int]:
        """文書に紐づく事業所IDを取得する。"""
        if document_type == 'SUPPORT_PLAN':
            plan = db.session.get(SupportPlan, document_id)
            if plan and plan.office_service_configuration:
                return plan.office_service_configuration.office_id
            # fallback: user primary office
            if plan and plan.user and plan.user.primary_supporter and plan.user.primary_supporter.office_id:
                return plan.user.primary_supporter.office_id
        elif document_type == 'RETENTION_SUPPORT_REPORT':
            report = db.session.get(MonthlyRetentionReport, document_id)
            if report and report.contract and report.contract.office_service_configuration:
                return report.contract.office_service_configuration.office_id
        return None

    @staticmethod
    def generate_document_snapshot(document_type: str, document_id: int) -> Dict[str, Any]:
        """
        確定時点の文書構成およびマスタ情報の完全なスナップショットを生成する。
        以後のマスタ変更によって確定文書のレンダリング内容が変化しないSource of Truthとなる。
        """
        if document_type == 'SUPPORT_PLAN':
            plan = db.session.get(SupportPlan, document_id)
            if not plan:
                raise ValueError("個別支援計画が見つかりません。")

            user = plan.user
            user_pii = user.pii if user else None
            office_config = plan.office_service_configuration
            office = office_config.office if office_config else (
                user.primary_supporter.office if (user and user.primary_supporter) else None
            )

            # 目標情報
            long_term_goals = []
            for ltg in plan.long_term_goals:
                long_term_goals.append({
                    "id": ltg.id,
                    "goal_text": ltg.goal_text,
                    "set_year_month": getattr(ltg, 'set_year_month', None),
                    "target_year_month": getattr(ltg, 'target_year_month', None),
                    "achievement_status": getattr(ltg, 'achievement_status', None),
                    "short_term_goals": [
                        {
                            "id": stg.id,
                            "goal_text": stg.goal_text,
                            "set_year_month": getattr(stg, 'set_year_month', None),
                            "target_year_month": getattr(stg, 'target_year_month', None),
                            "achievement_status": getattr(stg, 'achievement_status', None),
                        }
                        for stg in ltg.short_term_goals
                    ]
                })

            snapshot = {
                "document_type": "SUPPORT_PLAN",
                "document_id": plan.id,
                "plan_version": plan.plan_version,
                "plan_start_date": plan.plan_start_date.strftime('%Y-%m-%d') if plan.plan_start_date else None,
                "plan_end_date": plan.plan_end_date.strftime('%Y-%m-%d') if plan.plan_end_date else None,
                "created_at": plan.created_at.strftime('%Y-%m-%d %H:%M:%S') if plan.created_at else None,
                "sabikan_approved_at": plan.sabikan_approved_at.strftime('%Y-%m-%d %H:%M:%S') if plan.sabikan_approved_at else None,
                "sabikan_name": plan.sabikan_approved_by.name if getattr(plan, 'sabikan_approved_by', None) else None,
                # 利用者情報
                "user": {
                    "id": user.id if user else None,
                    "display_name": user.display_name if user else "",
                    "user_code": user.user_code if user else "",
                    "last_name": user_pii.last_name if user_pii else "",
                    "first_name": user_pii.first_name if user_pii else "",
                    "last_name_kana": user_pii.last_name_kana if user_pii else "",
                    "first_name_kana": user_pii.first_name_kana if user_pii else "",
                    "birth_date": user_pii.birth_date.strftime('%Y-%m-%d') if (user_pii and user_pii.birth_date) else None,
                    "gender": user_pii.gender_identity if user_pii else "",
                    "handbook_level": user_pii.handbook_level if user_pii else "",
                    "disability_type": user_pii.disability_type.type_name if (user_pii and user_pii.disability_type) else "",
                },
                # 事業所情報
                "office": {
                    "office_name": office.office_name if office else "",
                    "address": office.address if office else "",
                    "phone_number": office.phone_number if office else "",
                    "fax_number": office.fax_number if office else "",
                    "representative_name": office.representative_name if office else "",
                },
                "long_term_goals": long_term_goals,
            }

            # 定着支援計画固有のDetail情報
            if plan.retention_detail:
                rd = plan.retention_detail
                snapshot["is_retention_plan"] = True
                snapshot["retention_detail"] = {
                    "overall_support_goal": rd.overall_support_goal,
                    "review_date": rd.review_date.strftime('%Y-%m-%d') if rd.review_date else None,
                    "review_reason": rd.review_reason,
                    # スナップショット事実
                    "user_name": rd.user_name,
                    "user_name_kana": rd.user_name_kana,
                    "gender": rd.gender,
                    "birth_date": rd.birth_date.strftime('%Y-%m-%d') if rd.birth_date else None,
                    "age_at_planning": rd.age_at_planning,
                    "support_level": rd.support_level,
                    "disability_handbook_type": rd.disability_handbook_type,
                    "employer_name": rd.employer_name,
                    "employer_industry": rd.employer_industry,
                    "employer_address": rd.employer_address,
                    "employer_tel": rd.employer_tel,
                    "employer_contact_person": rd.employer_contact_person,
                    "job_start_date": rd.job_start_date.strftime('%Y-%m-%d') if rd.job_start_date else None,
                    "office_name": rd.office_name,
                    "office_number": rd.office_number,
                    "office_address": rd.office_address,
                    "office_tel": rd.office_tel,
                    "office_fax": rd.office_fax,
                    "items": [
                        {
                            "item_number": item.item_number,
                            "challenge_topic": item.challenge_topic,
                            "support_policy": item.support_policy,
                            "support_content": item.support_content,
                            "support_period_start": item.support_period_start.strftime('%Y-%m-%d') if item.support_period_start else None,
                            "support_period_end": item.support_period_end.strftime('%Y-%m-%d') if item.support_period_end else None,
                            "support_frequency": item.support_frequency,
                        }
                        for item in rd.items
                    ]
                }
            else:
                snapshot["is_retention_plan"] = False

            return snapshot

        elif document_type == 'RETENTION_SUPPORT_REPORT':
            report = db.session.get(MonthlyRetentionReport, document_id)
            if not report:
                raise ValueError("就労定着支援レポートが見つかりません。")

            contract = report.contract
            user = contract.user if contract else None
            user_pii = user.pii if user else None
            office_config = contract.office_service_configuration if contract else None
            office = office_config.office if office_config else None

            snapshot = {
                "document_type": "RETENTION_SUPPORT_REPORT",
                "document_id": report.id,
                "report_year_month": report.report_year_month,
                "status": report.status,
                "created_at": report.created_at.strftime('%Y-%m-%d %H:%M:%S') if report.created_at else None,
                "created_by_name": report.created_by.name if report.created_by else None,
                # 利用者情報
                "user": {
                    "id": user.id if user else None,
                    "display_name": user.display_name if user else "",
                    "user_code": user.user_code if user else "",
                    "last_name": user_pii.last_name if user_pii else "",
                    "first_name": user_pii.first_name if user_pii else "",
                },
                # 事業所情報
                "office": {
                    "office_name": office.office_name if office else "",
                    "address": office.address if office else "",
                    "phone_number": office.phone_number if office else "",
                },
                # レポート本文項目
                "support_goal": report.support_goal,
                "support_content": report.support_content,
                "support_result": report.support_result,
                "future_support_plan": report.future_support_plan,
                "stakeholder_efforts": report.stakeholder_efforts,
                "sharing_notes": report.sharing_notes,
                "interview_records": report.interview_records,
                "company_visit_records": report.company_visit_records,
                "work_status_summary": report.work_status_summary,
                "life_status_summary": report.life_status_summary,
                "user_coping_summary": report.user_coping_summary,
                "employer_feedback_summary": report.employer_feedback_summary,
                "support_details": report.support_details,
                "future_support_policy": report.future_support_policy,
            }
            return snapshot

        else:
            raise ValueError(f"未対応の文書種別です: {document_type}")

    @staticmethod
    def finalize_document(document_type: str, document_id: int, supporter_id: int) -> Dict[str, Any]:
        """
        職員・サビ管による文書内容の確定処理。
        確定版スナップショットを文書本体へ固定し、ステータスを遷移させる。
        """
        if document_type == 'SUPPORT_PLAN':
            plan = db.session.get(SupportPlan, document_id)
            if not plan:
                raise ValueError("個別支援計画が見つかりません。")

            if plan.plan_status not in ('DRAFT', 'PENDING_CONFERENCE'):
                raise ValueError(f"DRAFT以外の計画は確定できません（現在: {plan.plan_status}）")

            # サビ管承認の完了を確認（サビ管による確定）
            supporter = db.session.get(Supporter, supporter_id)
            if not supporter:
                raise ValueError("職員が見つかりません。")

            plan.sabikan_approved_by_id = supporter_id
            plan.sabikan_approved_at = datetime.datetime.now()

            # スナップショット生成・固定
            plan.document_snapshot = DocumentConsentService.generate_document_snapshot(document_type, document_id)
            plan.plan_status = 'PENDING_CONSENT'

            # 互換テーブル retention_support_plans の同期
            if plan.retention_detail:
                legacy_plan = RetentionSupportPlan.query.filter_by(
                    contract_id=plan.retention_detail.retention_contract_id,
                    version=plan.plan_version
                ).first()
                if legacy_plan:
                    legacy_plan.status = 'PENDING_CONSENT'
                    db.session.add(legacy_plan)

            db.session.add(plan)

            # Audit
            audit_log = AuditActionLog(
                action="DOCUMENT_FINALIZED",
                user_id=plan.user_id,
                actor_supporter_id=supporter_id,
                entity_type="SupportPlan",
                entity_id=plan.id,
                reason=f"Plan {plan.id} (v{plan.plan_version}) finalized and snapshot frozen."
            )
            db.session.add(audit_log)
            db.session.commit()

            return {
                "document_type": "SUPPORT_PLAN",
                "document_id": plan.id,
                "plan_version": plan.plan_version,
                "status": plan.plan_status,
                "sabikan_approved_at": plan.sabikan_approved_at.isoformat()
            }

        elif document_type == 'RETENTION_SUPPORT_REPORT':
            report = db.session.get(MonthlyRetentionReport, document_id)
            if not report:
                raise ValueError("就労定着支援レポートが見つかりません。")

            if report.status != 'DRAFT':
                raise ValueError(f"DRAFT以外のレポートは確定できません（現在: {report.status}）")

            report.document_snapshot = DocumentConsentService.generate_document_snapshot(document_type, document_id)
            report.status = 'FINALIZED'
            db.session.add(report)

            audit_log = AuditActionLog(
                action="DOCUMENT_FINALIZED",
                user_id=report.contract.user_id if report.contract else None,
                actor_supporter_id=supporter_id,
                entity_type="MonthlyRetentionReport",
                entity_id=report.id,
                reason=f"Report {report.id} ({report.report_year_month}) finalized and snapshot frozen."
            )
            db.session.add(audit_log)
            db.session.commit()

            return {
                "document_type": "RETENTION_SUPPORT_REPORT",
                "document_id": report.id,
                "status": report.status
            }

        else:
            raise ValueError(f"未対応の文書種別です: {document_type}")

    @staticmethod
    def deliver_digital(document_type: str, document_id: int, supporter_id: Optional[int] = None) -> DocumentDeliveryLog:
        """
        確定文書を本人アカウントへ電磁的交付（配信）する。
        確定状態であることを検証し、DocumentDeliveryLog (delivery_method='DIGITAL') を作成。
        """
        recipient_user_id = None
        document_version = 1

        if document_type == 'SUPPORT_PLAN':
            plan = db.session.get(SupportPlan, document_id)
            if not plan:
                raise ValueError("個別支援計画が見つかりません。")
            if plan.plan_status not in ('PENDING_CONSENT', 'ACTIVE', 'ARCHIVED'):
                raise ValueError("確定前の計画は交付できません。")
            recipient_user_id = plan.user_id
            document_version = plan.plan_version

        elif document_type == 'RETENTION_SUPPORT_REPORT':
            report = db.session.get(MonthlyRetentionReport, document_id)
            if not report:
                raise ValueError("支援レポートが見つかりません。")
            if report.status != 'FINALIZED':
                raise ValueError("確定前のレポートは交付できません。")
            recipient_user_id = report.contract.user_id
            document_version = 1
        else:
            raise ValueError(f"未対応の文書種別です: {document_type}")

        # 既存の DIGITAL 交付があればそれを返す（重複防止）
        existing_log = DocumentDeliveryLog.query.filter_by(
            document_type=document_type,
            document_id=document_id,
            document_version=document_version,
            recipient_user_id=recipient_user_id,
            delivery_method='DIGITAL'
        ).first()

        if existing_log:
            return existing_log

        delivery_log = DocumentDeliveryLog(
            document_type=document_type,
            document_id=document_id,
            document_version=document_version,
            recipient_user_id=recipient_user_id,
            delivery_method='DIGITAL',
            delivered_at=datetime.datetime.now(),
            delivered_by_supporter_id=supporter_id
        )
        db.session.add(delivery_log)

        audit_log = AuditActionLog(
            action="DOCUMENT_PRESENTED",
            user_id=recipient_user_id,
            actor_supporter_id=supporter_id,
            entity_type=document_type,
            entity_id=document_id,
            reason=f"{document_type} {document_id} (v{document_version}) delivered digitally to user {recipient_user_id}."
        )
        db.session.add(audit_log)
        db.session.commit()

        return delivery_log

    @staticmethod
    def deliver_paper(
        document_type: str, 
        document_id: int, 
        supporter_id: int, 
        delivered_at: Optional[datetime.date] = None
    ) -> DocumentDeliveryLog:
        """
        確定文書を印刷して本人へ紙交付した事実を記録する。
        DocumentDeliveryLog (delivery_method='PAPER') を作成。
        """
        recipient_user_id = None
        document_version = 1

        if document_type == 'SUPPORT_PLAN':
            plan = db.session.get(SupportPlan, document_id)
            if not plan:
                raise ValueError("個別支援計画が見つかりません。")
            if plan.plan_status not in ('PENDING_CONSENT', 'ACTIVE', 'ARCHIVED'):
                raise ValueError("確定前の計画は交付できません。")
            recipient_user_id = plan.user_id
            document_version = plan.plan_version

        elif document_type == 'RETENTION_SUPPORT_REPORT':
            report = db.session.get(MonthlyRetentionReport, document_id)
            if not report:
                raise ValueError("支援レポートが見つかりません。")
            if report.status != 'FINALIZED':
                raise ValueError("確定前のレポートは交付できません。")
            recipient_user_id = report.contract.user_id
            document_version = 1
        else:
            raise ValueError(f"未対応の文書種別です: {document_type}")

        # 既存の PAPER 交付があればそれを返す
        existing_log = DocumentDeliveryLog.query.filter_by(
            document_type=document_type,
            document_id=document_id,
            document_version=document_version,
            recipient_user_id=recipient_user_id,
            delivery_method='PAPER'
        ).first()

        if existing_log:
            return existing_log

        delivery_time = datetime.datetime.combine(delivered_at, datetime.time(9, 0)) if delivered_at else datetime.datetime.now()

        delivery_log = DocumentDeliveryLog(
            document_type=document_type,
            document_id=document_id,
            document_version=document_version,
            recipient_user_id=recipient_user_id,
            delivery_method='PAPER',
            delivered_at=delivery_time,
            delivered_by_supporter_id=supporter_id
        )
        db.session.add(delivery_log)

        audit_log = AuditActionLog(
            action="DOCUMENT_PRESENTED",
            user_id=recipient_user_id,
            actor_supporter_id=supporter_id,
            entity_type=document_type,
            entity_id=document_id,
            reason=f"{document_type} {document_id} (v{document_version}) delivered on paper to user {recipient_user_id}."
        )
        db.session.add(audit_log)
        db.session.commit()

        return delivery_log

    @staticmethod
    def record_document_viewed(document_type: str, document_id: int, user_id: int) -> Optional[DocumentDeliveryLog]:
        """
        利用者が確定文書の詳細またはA4プレビューを実際に開いた瞬間に viewed_at を記録する。
        一覧取得やprefetchでは記録しない。
        """
        delivery_logs = DocumentDeliveryLog.query.filter_by(
            document_type=document_type,
            document_id=document_id,
            recipient_user_id=user_id,
            delivery_method='DIGITAL'
        ).all()

        updated = False
        target_log = None
        for log in delivery_logs:
            if log.viewed_at is None:
                log.viewed_at = datetime.datetime.now()
                db.session.add(log)
                updated = True
                target_log = log

        if updated:
            db.session.commit()

        return target_log

    @staticmethod
    def sign_digitally(document_type: str, document_id: int, auth_user_id: int) -> DocumentConsentLog:
        """
        本人による電子署名 (USER_DIGITAL)。
        本人JWT認証(auth_user_id)で厳格に検証し、別利用者はFail Closed (403)とする。
        """
        if document_type == 'SUPPORT_PLAN':
            plan = db.session.get(SupportPlan, document_id)
            if not plan:
                raise ValueError("個別支援計画が見つかりません。")

            # Fail Closed: 本人認証チェック
            if plan.user_id != auth_user_id:
                raise PermissionError("Forbidden: 他の利用者の文書には署名できません。")

            # 確定状態チェック
            if plan.plan_status != 'PENDING_CONSENT':
                raise ValueError(f"署名対象の計画が確定状態（PENDING_CONSENT）ではありません（現在: {plan.plan_status}）")

            # 署名証跡の記録
            consent_log = DocumentConsentLog(
                user_id=auth_user_id,
                document_type='SUPPORT_PLAN',
                document_id=plan.id,
                document_version=plan.plan_version,
                action='CONSENT',
                signature_method='USER_DIGITAL',
                consent_timestamp=datetime.datetime.now(),
                consent_proof=f"USER_DIGITAL_SIGNATURE_USER_{auth_user_id}_{uuid.uuid4().hex[:12]}",
                recorded_at=datetime.datetime.now()
            )
            db.session.add(consent_log)
            db.session.flush()

            # 計画の有効化（同一トランザクションでアトミック実行）
            DocumentConsentService.activate_plan_with_consent(plan, consent_log)

            audit_log = AuditActionLog(
                action="DOCUMENT_SIGNED_DIGITALLY",
                user_id=auth_user_id,
                entity_type="SupportPlan",
                entity_id=plan.id,
                reason=f"Plan {plan.id} (v{plan.plan_version}) digitally signed by user {auth_user_id}."
            )
            db.session.add(audit_log)
            db.session.commit()

            return consent_log

        elif document_type == 'RETENTION_SUPPORT_REPORT':
            report = db.session.get(MonthlyRetentionReport, document_id)
            if not report:
                raise ValueError("支援レポートが見つかりません。")

            if report.contract.user_id != auth_user_id:
                raise PermissionError("Forbidden: 他の利用者のレポートは確認できません。")

            if report.status != 'FINALIZED':
                raise ValueError(f"レポートが確定状態（FINALIZED）ではありません（現在: {report.status}）")

            consent_log = DocumentConsentLog(
                user_id=auth_user_id,
                document_type='RETENTION_SUPPORT_REPORT',
                document_id=report.id,
                document_version=1,
                action='ACKNOWLEDGEMENT',
                signature_method='USER_DIGITAL',
                consent_timestamp=datetime.datetime.now(),
                consent_proof=f"USER_DIGITAL_ACK_USER_{auth_user_id}_{uuid.uuid4().hex[:12]}",
                recorded_at=datetime.datetime.now()
            )
            db.session.add(consent_log)

            audit_log = AuditActionLog(
                action="DOCUMENT_ACKNOWLEDGED",
                user_id=auth_user_id,
                entity_type="MonthlyRetentionReport",
                entity_id=report.id,
                reason=f"Report {report.id} ({report.report_year_month}) digitally acknowledged by user {auth_user_id}."
            )
            db.session.add(audit_log)
            db.session.commit()

            return consent_log

        else:
            raise ValueError(f"未対応の文書種別です: {document_type}")

    @staticmethod
    def upload_paper_signature(
        document_type: str,
        document_id: int,
        supporter_id: int,
        signed_at: datetime.date,
        file_storage,
        upload_folder: str
    ) -> DocumentConsentLog:
        """
        紙署名＋職員アップロード (PAPER_UPLOAD)。
        本人が紙に署名した事実を、職員が署名済み画像/PDFを添付して登録する。
        """
        if not file_storage or not file_storage.filename or file_storage.filename.strip() == '':
            raise ValueError("紙署名済みの証拠ファイル（画像またはPDF）は必須です。")

        if not allowed_file(file_storage.filename):
            raise ValueError("証拠ファイルは画像（png, jpg, jpeg）またはPDF形式でアップロードしてください。")

        # ファイル保存
        ext = file_storage.filename.rsplit('.', 1)[1].lower()
        unique_name = f"{document_type}_{document_id}_{uuid.uuid4().hex}.{ext}"
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, unique_name)
        file_storage.save(file_path)
        evidence_url = f"/api/consents/evidence/{unique_name}"

        signed_datetime = datetime.datetime.combine(signed_at, datetime.time(12, 0))

        if document_type == 'SUPPORT_PLAN':
            plan = db.session.get(SupportPlan, document_id)
            if not plan:
                raise ValueError("個別支援計画が見つかりません。")

            # サビ管承認完了チェック (Fail Closed)
            if plan.plan_status != 'PENDING_CONSENT':
                raise ValueError(f"サビ管承認が完了していない計画（現在: {plan.plan_status}）には署名証拠を登録できません。")

            consent_log = DocumentConsentLog(
                user_id=plan.user_id,
                document_type='SUPPORT_PLAN',
                document_id=plan.id,
                document_version=plan.plan_version,
                action='CONSENT',
                signature_method='PAPER_UPLOAD',
                consent_timestamp=signed_datetime,
                consent_proof=f"PAPER_SIGNED_ON_{signed_at.strftime('%Y%m%d')}",
                evidence_file_url=evidence_url,
                recorded_by_supporter_id=supporter_id,
                recorded_at=datetime.datetime.now()
            )
            db.session.add(consent_log)
            db.session.flush()

            # 計画の有効化（同一トランザクションでアトミック実行）
            DocumentConsentService.activate_plan_with_consent(plan, consent_log)

            audit_log = AuditActionLog(
                action="PAPER_SIGNATURE_EVIDENCE_UPLOADED",
                user_id=plan.user_id,
                actor_supporter_id=supporter_id,
                entity_type="SupportPlan",
                entity_id=plan.id,
                reason=f"Plan {plan.id} (v{plan.plan_version}) paper signature uploaded by staff {supporter_id}."
            )
            db.session.add(audit_log)
            db.session.commit()

            return consent_log

        elif document_type == 'RETENTION_SUPPORT_REPORT':
            report = db.session.get(MonthlyRetentionReport, document_id)
            if not report:
                raise ValueError("支援レポートが見つかりません。")

            if report.status != 'FINALIZED':
                raise ValueError(f"レポートが確定状態（FINALIZED）ではありません（現在: {report.status}）")

            consent_log = DocumentConsentLog(
                user_id=report.contract.user_id,
                document_type='RETENTION_SUPPORT_REPORT',
                document_id=report.id,
                document_version=1,
                action='ACKNOWLEDGEMENT',
                signature_method='PAPER_UPLOAD',
                consent_timestamp=signed_datetime,
                consent_proof=f"PAPER_ACK_ON_{signed_at.strftime('%Y%m%d')}",
                evidence_file_url=evidence_url,
                recorded_by_supporter_id=supporter_id,
                recorded_at=datetime.datetime.now()
            )
            db.session.add(consent_log)

            audit_log = AuditActionLog(
                action="PAPER_SIGNATURE_EVIDENCE_UPLOADED",
                user_id=report.contract.user_id,
                actor_supporter_id=supporter_id,
                entity_type="MonthlyRetentionReport",
                entity_id=report.id,
                reason=f"Report {report.id} ({report.report_year_month}) paper acknowledgement uploaded by staff {supporter_id}."
            )
            db.session.add(audit_log)
            db.session.commit()

            return consent_log

        else:
            raise ValueError(f"未対応の文書種別です: {document_type}")

    @staticmethod
    def activate_plan_with_consent(plan: SupportPlan, consent_log: DocumentConsentLog):
        """
        署名証跡に基づき計画を ACTIVE 化する。
        新版 ACTIVE 化と旧版 ARCHIVED 化、および互換テーブル同期を同一トランザクションでアトミックに実行する。
        """
        today = datetime.date.today()

        # 既存のACTIVE計画を検索（同一利用者の別計画）
        old_active_plan = SupportPlan.query.filter(
            SupportPlan.user_id == plan.user_id,
            SupportPlan.id != plan.id,
            SupportPlan.plan_status == 'ACTIVE'
        ).first()

        if old_active_plan:
            old_active_plan.plan_status = 'ARCHIVED'
            if plan.plan_start_date:
                old_active_plan.plan_end_date = plan.plan_start_date - datetime.timedelta(days=1)
            db.session.add(old_active_plan)

            # 互換テーブル旧版も ARCHIVED
            if old_active_plan.retention_detail:
                legacy_old = RetentionSupportPlan.query.filter_by(
                    contract_id=old_active_plan.retention_detail.retention_contract_id,
                    version=old_active_plan.plan_version
                ).first()
                if legacy_old:
                    legacy_old.status = 'ARCHIVED'
                    if old_active_plan.plan_end_date:
                        legacy_old.plan_end_date = old_active_plan.plan_end_date
                    db.session.add(legacy_old)

            db.session.add(AuditActionLog(
                action="PLAN_ARCHIVED",
                user_id=plan.user_id,
                entity_type="SupportPlan",
                entity_id=old_active_plan.id,
                reason=f"Previous plan {old_active_plan.id} archived upon activation of new plan {plan.id}."
            ))

        # 新版の ACTIVE 化
        plan.plan_status = 'ACTIVE'
        plan.consented_at = consent_log.consent_timestamp.date() if isinstance(consent_log.consent_timestamp, datetime.datetime) else consent_log.consent_timestamp
        plan.explained_at = plan.consented_at
        if not plan.activated_at:
            plan.activated_at = plan.plan_start_date or today

        # 互換テーブル新版も ACTIVE
        if plan.retention_detail:
            legacy_new = RetentionSupportPlan.query.filter_by(
                contract_id=plan.retention_detail.retention_contract_id,
                version=plan.plan_version
            ).first()
            if legacy_new:
                legacy_new.status = 'ACTIVE'
                if plan.plan_start_date:
                    legacy_new.start_date = plan.plan_start_date
                if plan.plan_end_date:
                    legacy_new.plan_end_date = plan.plan_end_date
                db.session.add(legacy_new)

        db.session.add(plan)
        db.session.add(AuditActionLog(
            action="PLAN_ACTIVATED",
            user_id=plan.user_id,
            entity_type="SupportPlan",
            entity_id=plan.id,
            reason=f"Plan {plan.id} (v{plan.plan_version}) ACTIVATED and fully consented."
        ))
