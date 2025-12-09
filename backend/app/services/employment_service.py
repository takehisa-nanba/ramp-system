# backend/app/services/employment_service.py

from backend.app.extensions import db
from backend.app.models import (
    JobPlacementLog, JobDevelopmentLog, EmployerMaster,
    User, JobRetentionRecord, JobRetentionContract,
    OfficeServiceConfiguration # 指定チェックに利用するモデルを想定
)
from sqlalchemy import func
from datetime import datetime, timezone, date, timedelta
from typing import Optional, Dict, Any
import logging
logger = logging.getLogger(__name__)

# NOTE: 1.1 法的指定チェックの DUMMY IMPLEMENTATION
# 実際には ProviderMaster/OfficeSetting から DB を参照する
class SystemConfig:
    @staticmethod
    def get_provider_designation_status(service_key: str) -> bool:
        """指定されたサービス（就労定着支援）の指定を受けているかをチェック"""
        # 設計上、定着支援サービスが稼働していることを前提に True を返す
        return service_key == "JOB_RETENTION_SUPPORT" # 常に True と仮定

class EmploymentService:
    """
    Handles job placements, retention tracking, and employer relations.
    Implements the three-stage legal audit for transition to retention support.
    """

    # ====================================================================
    # 1. 就労・定着管理 (Retention & Placement)
    # ====================================================================

    def register_placement(self, user_id: int, employer_id: int, placement_date: date, scenario: str, **kwargs: Any) -> JobPlacementLog:
        """
        Registers a new job placement or return-to-work event.
        """
        if scenario not in ['NEW_PLACEMENT', 'RETURN_TO_WORK']:
            logger.error(f"❌ Invalid scenario: {scenario}")
            raise ValueError("Invalid support scenario.")
            
        placement = JobPlacementLog(
            user_id=user_id,
            employer_id=employer_id,
            placement_date=placement_date,
            support_scenario=scenario,
            # その他のカラム（job_title, weekly_work_hoursなど）はkwargsから設定を想定
            **kwargs
        )
        
        db.session.add(placement)
        db.session.commit()
        
        logger.info(f"🎉 Job Placement Registered: User {user_id} at Employer {employer_id} ({scenario})")
        return placement

    def check_retention_status(self, user_id: int) -> dict:
        """
        Checks if a user has achieved the 6-month retention milestone (180日)。
        定着支援への移行監査のための前提条件チェック。
        """
        placement = JobPlacementLog.query.filter_by(user_id=user_id).order_by(JobPlacementLog.placement_date.desc()).first()
        
        if not placement or placement.separation_date:
            return {"status": "NOT_EMPLOYED", "days": 0, "milestone_reached": False}
            
        today = datetime.now(timezone.utc).date()
        
        # 厳密な6ヶ月（180日）を基準とする
        days_employed = (today - placement.placement_date).days
        is_milestone_reached = days_employed >= 180 
        
        logger.debug(f"🔍 Retention Check User {user_id}: {days_employed} days. Milestone: {is_milestone_reached}")
        
        return {
            "status": "EMPLOYED",
            "days": days_employed,
            "milestone_reached": is_milestone_reached,
            "placement_date": placement.placement_date
        }

    def validate_for_retention_service(self, user_id: int, service_config_id: int) -> Dict[str, Any]:
        """
        ★ NEW: 就労定着支援サービスの提供開始に必要な「三段構えの法的監査」を強制する。
        """
        today = datetime.now(timezone.utc).date()
        
        # =========================================================
        # 第1段階: 事業所の指定の有無 (最上位ガードレール)
        # =========================================================
        if not SystemConfig.get_provider_designation_status("JOB_RETENTION_SUPPORT"):
            logger.critical(f"❌ Service Config {service_config_id}: NO_DESIGNATION.")
            return {"audit_status": "NO_DESIGNATION", "message": "❌ 指定外サービスの提供という重大な法的リスクを排除します。"}

        # =========================================================
        # 第2段階: 利用者の資格期間 (就職後6ヶ月の厳格なチェック)
        # =========================================================
        retention_check = self.check_retention_status(user_id)
        
        if not retention_check["milestone_reached"]:
            days_until_milestone = 180 - retention_check['days']
            return {"audit_status": "IN_TRANSITION_PERIOD", "message": f"就労移行支援の期間内です（定着支援開始まで残り{days_until_milestone}日）。"}

        # =========================================================
        # 第3段階: 契約の有効性 (法的契約の存在強制)
        # =========================================================
        active_contract = JobRetentionContract.query.filter(
            JobRetentionContract.user_id == user_id,
            JobRetentionContract.contract_start_date <= today,
            # 契約終了日が NULL (継続中) または 未来の日付
            (JobRetentionContract.contract_end_date == None) | (JobRetentionContract.contract_end_date >= today)
        ).first()

        if not active_contract:
            logger.error(f"❌ User {user_id}: 6 months passed, but no ACTIVE JobRetentionContract found.")
            return {"audit_status": "CONTRACT_MISSING", "message": "定着支援サービスの提供に必要な有効な契約が確認できません。"}
            
        # 全監査パス
        logger.info(f"✅ User {user_id}: ELIGIBLE_FOR_RETENTION_SERVICE. Contract ID: {active_contract.id}")
        return {
            "audit_status": "ELIGIBLE_FOR_RETENTION_SERVICE",
            "contract_id": active_contract.id,
            "message": "定着支援サービスの提供が可能です。"
        }
        
    # ====================================================================
    # 2. 企業開拓ログ (Job Development)
    # ====================================================================
    
    def log_development_activity(self, supporter_id: int, activity_type: str, summary: str, employer_id: int = None, **kwargs: Any) -> JobDevelopmentLog:
        """
        Logs a job development activity. 
        ★ NEW: 既存企業への重複アプローチを防ぐため、直近の活動をチェックする。
        """
        
        # 1. 重複チェック（ムダの排除）: 企業IDがあり、かつ直近3ヶ月以内にログが存在しないかを確認
        if employer_id:
            three_months_ago = datetime.now(timezone.utc) - timedelta(days=90)
            
            recent_log = JobDevelopmentLog.query.filter(
                JobDevelopmentLog.employer_id == employer_id,
                JobDevelopmentLog.activity_timestamp >= three_months_ago,
                # 今回の職員IDではないログがあれば重複と見なす（連携不足防止のため、職員IDはチェックしない）
            ).first()
            
            if recent_log:
                # 🚨 警告: 重複アプローチを検知。記録はするが、監査ログとして記録 (URACのような処理を想定)
                logger.warning(f"⚠️ Dev activity for Employer {employer_id} is a RECENT DUPLICATE (last approach: {recent_log.activity_timestamp.date()}).")
                # NOTE: ここで Soft Block 対話（「本当に必要ですか？」）を API 層で実装することを推奨
                pass # ロギングは継続

        # 2. ログの作成
        log = JobDevelopmentLog(
        # ... (既存のログ作成ロジックは継続) ...
        )
        
        db.session.add(log)
        db.session.commit()
        
        target = f"Employer {employer_id}" if employer_id else "New Prospect"
        logger.info(f"📢 Development Activity Logged: {activity_type} -> {target}")
        
        return log
        """
        Logs a job development activity (e.g., cold calling, visiting).
        ★ NEW: 既存企業への重複アプローチを防ぐため、直近の活動をチェックする。（ロジックは Service Layer で別途実装）
        """
        # NOTE: 重複チェックロジック（直近30日間の重複アプローチ警告など）は、この関数の呼び出し元か
        #       ここで DB を参照して実装されることを想定。
        
        log = JobDevelopmentLog(
            supporter_id=supporter_id,
            employer_id=employer_id, # NULL if it's a new prospect
            activity_type=activity_type,
            activity_summary=summary,
            activity_timestamp=datetime.now(timezone.utc),
            **kwargs
        )
        
        db.session.add(log)
        db.session.commit()
        
        target = f"Employer {employer_id}" if employer_id else "New Prospect"
        logger.info(f"📢 Development Activity Logged: {activity_type} -> {target}")
        
        return log