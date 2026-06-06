from backend.app.extensions import db
from backend.app.models import CaseConferenceLog, CaseConferenceParticipant, User
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class CaseConferenceService:
    def record_case_conference(
        self,
        initiator_id: int,
        user_id: int,
        conference_type: str,
        concern_summary: str,
        agreed_action: str,
        participant_ids: list[int],
        conference_datetime: datetime = None,
        triggering_log_reference: str = None,
        plan_direction_update: str = None,
        external_collaboration_required: bool = False,
        issue_category_id: int = None
    ) -> CaseConferenceLog:
        """
        ケース会議を記録し、参加者を保存する。
        """
        user = db.session.get(User, user_id)
        if not user:
            raise Exception("User not found")
            
        conference_time = conference_datetime or datetime.now()
        
        conference = CaseConferenceLog(
            initiator_supporter_id=initiator_id,
            user_id=user_id,
            conference_type=conference_type,
            concern_summary=concern_summary,
            agreed_action=agreed_action,
            conference_datetime=conference_time,
            triggering_log_reference=triggering_log_reference,
            plan_direction_update=plan_direction_update,
            external_collaboration_required=external_collaboration_required,
            issue_category_id=issue_category_id
        )
        db.session.add(conference)
        db.session.flush() # get ID
        
        # 参加者の保存
        participants = []
        # initiator always included as a participant
        all_participants = set(participant_ids)
        all_participants.add(initiator_id)
        
        for pid in all_participants:
            p = CaseConferenceParticipant(
                case_conference_log_id=conference.id,
                supporter_id=pid
            )
            participants.append(p)
            
        db.session.add_all(participants)
        logger.info(f"Case conference {conference.id} recorded for User {user_id} with {len(participants)} participants.")
        
        return conference
