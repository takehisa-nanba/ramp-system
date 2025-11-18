from backend.app.extensions import db
from backend.app.models import (
    JobPlacementLog, JobDevelopmentLog, EmployerMaster,
    User, JobRetentionRecord
)
from sqlalchemy import func
from datetime import datetime, timedelta

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
            raise ValueError("Invalid support scenario.")
            
        placement = JobPlacementLog(
            user_id=user_id,
            employer_id=employer_id,
            placement_date=placement_date,
            support_scenario=scenario
        )
        
        db.session.add(placement)
        db.session.commit()
        return placement

    def check_retention_status(self, user_id: int) -> dict:
        """
        Checks if a user has achieved the 6-month retention milestone.
        This is critical for 'Shuro Teichaku' validation.
        """
        placement = JobPlacementLog.query.filter_by(user_id=user_id).order_by(JobPlacementLog.placement_date.desc()).first()
        
        if not placement or placement.separation_date:
            return {"status": "NOT_employed", "months": 0}
            
        months_employed = (datetime.utcnow().date() - placement.placement_date).days / 30
        is_milestone_reached = months_employed >= 6
        
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
            activity_timestamp=datetime.utcnow()
        )
        
        db.session.add(log)
        db.session.commit()
        return log