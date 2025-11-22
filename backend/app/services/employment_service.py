# 🚨 修正点: 'from backend.app.extensions' (絶対参照)
from backend.app.extensions import db
from backend.app.models import (
    JobPlacementLog, JobDevelopmentLog, EmployerMaster,
    User, JobRetentionRecord
)
from sqlalchemy import func
# ★ 修正: timezone
from datetime import datetime, timezone
import logging

# ★ ロガーの取得
logger = logging.getLogger(__name__)

class EmploymentService:
    """
    Handles job placements, retention tracking, and employer relations.
    Calculates retention rates (Principle 3) and tracks development activities (Principle 4).
    """

    # ====================================================================
    # 1. 就労・定着管理 (Retention & Placement)
    # ====================================================================

    def register_placement(self, user_id: int, employer_id: int, placement_date: datetime.date, scenario: str) -> JobPlacementLog:
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
            support_scenario=scenario
        )
        
        db.session.add(placement)
        db.session.commit()
        
        logger.info(f"🎉 Job Placement Registered: User {user_id} at Employer {employer_id} ({scenario})")
        return placement

    def check_retention_status(self, user_id: int) -> dict:
        """
        Checks if a user has achieved the 6-month retention milestone.
        This is critical for 'Shuro Teichaku' validation.
        """
        placement = JobPlacementLog.query.filter_by(user_id=user_id).order_by(JobPlacementLog.placement_date.desc()).first()
        
        if not placement or placement.separation_date:
            return {"status": "NOT_EMPLOYED", "months": 0, "milestone_reached": False}
            
        # ★ 修正: utcnow().date() -> now(timezone.utc).date()
        today = datetime.now(timezone.utc).date()
        
        # 単純な月数計算 (実際はもう少し厳密な計算が必要な場合もあるが、目安として30日区切り)
        days_employed = (today - placement.placement_date).days
        months_employed = days_employed / 30
        is_milestone_reached = months_employed >= 6
        
        logger.debug(f"🔍 Retention Check User {user_id}: {days_employed} days ({months_employed:.1f} months). Milestone: {is_milestone_reached}")
        
        return {
            "status": "EMPLOYED",
            "months": round(months_employed, 1),
            "milestone_reached": is_milestone_reached
        }

    # ====================================================================
    # 2. 企業開拓ログ (Job Development)
    # ====================================================================
    
    def log_development_activity(self, supporter_id: int, activity_type: str, summary: str, employer_id: int = None) -> JobDevelopmentLog:
        """
        Logs a job development activity (e.g., cold calling, visiting).
        """
        log = JobDevelopmentLog(
            supporter_id=supporter_id,
            employer_id=employer_id, # NULL if it's a new prospect
            activity_type=activity_type,
            activity_summary=summary,
            # ★ 修正: utcnow() -> now(timezone.utc)
            activity_timestamp=datetime.now(timezone.utc)
        )
        
        db.session.add(log)
        db.session.commit()
        
        target = f"Employer {employer_id}" if employer_id else "New Prospect"
        logger.info(f"📢 Development Activity Logged: {activity_type} -> {target}")
        
        return log