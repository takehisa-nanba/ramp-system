# backend/app/domain/attendance/decision_rules.py

import json
from datetime import datetime
from backend.app.models.core.audit_log import AuditActionLog

class AttendanceDecisionDomain:
    """
    勤怠およびシフトにおける「意思決定(Decision)」の共通物理法則。
    全ての状態改変（打刻修正・シフト修正・休暇承認）はここを通らなければならず、
    変更の理由は必ず監査証跡(AuditLog)として残されなければならない。
    """
    
    @classmethod
    def apply_decision_to_timecard(
        cls,
        timecard,
        approver_id: int,
        reason: str,
        check_in: datetime = None,
        check_out: datetime = None,
        break_minutes: int = None,
        is_absent: bool = None,
        absence_type: str = None,
        deemed_work_minutes: int = None
    ) -> list[AuditActionLog]:
        """
        タイムカードに対する意思決定を適用する。
        変更前後の状態を比較し、差分がある場合のみ更新を実施して監査ログを生成する純粋関数。
        """
        logs = []
        
        # 変更対象のプロパティと新しい値のマッピング
        updates = {
            'check_in': check_in,
            'check_out': check_out,
            'total_break_minutes': break_minutes,
            'is_absent': is_absent,
            'absence_type': absence_type,
            'deemed_work_minutes': deemed_work_minutes
        }
        
        before_state = {}
        after_state = {}
        
        for key, new_val in updates.items():
            if new_val is not None:
                old_val = getattr(timecard, key)
                if old_val != new_val:
                    before_state[key] = str(old_val) if old_val is not None else None
                    after_state[key] = str(new_val) if new_val is not None else None
                    setattr(timecard, key, new_val)
                    
        # 変更があった場合のみAuditLogを生成
        if before_state or after_state:
            log = AuditActionLog(
                actor_supporter_id=approver_id,
                action='UPDATE_TIMECARD_DECISION',
                entity_type='SupporterTimecard',
                entity_id=timecard.id,
                before_value=json.dumps(before_state, ensure_ascii=False),
                after_value=json.dumps(after_state, ensure_ascii=False),
                reason=reason
            )
            logs.append(log)
            
        return logs

    @classmethod
    def apply_decision_to_shift(
        cls,
        shift,
        approver_id: int,
        reason: str,
        planned_start_time: datetime = None,
        planned_end_time: datetime = None,
        planned_break_minutes: int = None
    ) -> list[AuditActionLog]:
        """
        シフトに対する意思決定を適用する。
        """
        logs = []
        updates = {
            'planned_start_time': planned_start_time,
            'planned_end_time': planned_end_time,
            'planned_break_minutes': planned_break_minutes
        }
        
        before_state = {}
        after_state = {}
        
        for key, new_val in updates.items():
            if new_val is not None:
                old_val = getattr(shift, key)
                if old_val != new_val:
                    before_state[key] = str(old_val) if old_val is not None else None
                    after_state[key] = str(new_val) if new_val is not None else None
                    setattr(shift, key, new_val)
                    
        if before_state or after_state:
            log = AuditActionLog(
                actor_supporter_id=approver_id,
                action='UPDATE_SHIFT_DECISION',
                entity_type='StaffDailyShift',
                entity_id=shift.id,
                before_value=json.dumps(before_state, ensure_ascii=False),
                after_value=json.dumps(after_state, ensure_ascii=False),
                reason=reason
            )
            logs.append(log)
            
        return logs
