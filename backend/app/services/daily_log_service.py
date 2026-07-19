from backend.app.extensions import db
from backend.app.models import StaffActivityMaster, UserDailyLog, SupportRecord, StaffActivityAllocationLog, User, IndividualSupportGoal, ShortTermGoal, LongTermGoal, SupportPlan, AuditActionLog
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import logging
from backend.app.utils.errors import ValidationError

logger = logging.getLogger(__name__)

class DailyLogService:
    def record_daily_log(
        self,
        supporter_id: int,
        tag_id: int,
        log_date: datetime.date,
        start_time: datetime,
        end_time: datetime,
        duration_seconds: int,
        user_id: int = None,
        notes: str = "",
        log_status: str = 'DRAFT',
        attendance_record_id: int = None
    ):
        """
        日報（活動）を記録する。
        直接支援ならSupportRecordへ、間接業務ならStaffActivityAllocationLogへ保存する。
        """
        if duration_seconds < 0 or duration_seconds > 86400:
            raise ValidationError("活動時間は0秒以上24時間（86400秒）以下で指定してください。")

        if start_time and end_time and end_time <= start_time:
            raise ValidationError("終了時間は開始時間より後の時間に設定してください。日跨ぎの活動記録はサポートされていません。")

        tag = db.session.get(StaffActivityMaster, tag_id)
        if not tag:
            raise ValidationError("無効な活動タグです")

        if tag.is_direct_support:
            if not user_id:
                raise ValidationError("直接支援の場合、利用者の選択が必須です")
            if duration_seconds is None:
                raise ValidationError("直接支援の場合は活動時間の入力が必須です。")

            # 🛡️ 重複時間帯ガードレール (直接支援のみ)
            # 支援記録(SupportRecord)に対して重複チェックを実施
            overlapping_record = db.session.query(SupportRecord)\
                .filter(
                    SupportRecord.supporter_id == supporter_id,
                    SupportRecord.log_date == log_date,
                    SupportRecord.user_id != user_id,
                    SupportRecord.support_record_type == 'DIRECT_SUPPORT',
                    SupportRecord.support_start_time != None,
                    SupportRecord.support_end_time != None,
                    SupportRecord.support_start_time < end_time,
                    start_time < SupportRecord.support_end_time
                ).first()

            if overlapping_record:
                other_user = db.session.get(User, overlapping_record.user_id)
                other_user_name = other_user.display_name if other_user else "他の利用者"
                start_formatted = overlapping_record.support_start_time.strftime('%H:%M') if overlapping_record.support_start_time else "--:--"
                end_formatted = overlapping_record.support_end_time.strftime('%H:%M') if overlapping_record.support_end_time else "--:--"
                raise ValidationError(f"既に同時間帯（{start_formatted}〜{end_formatted}）に別の利用者（{other_user_name}様）の支援記録が登録されています。重複した時間帯での支援記録は作成できません。")

            # 該当利用者の当日のUserDailyLogを探す（なければ自動作成）
            daily_log = UserDailyLog.query.filter_by(user_id=user_id, log_date=log_date).first()
            if not daily_log:
                daily_log = UserDailyLog(
                    user_id=user_id,
                    log_date=log_date,
                    location_type='ON_SITE', # デフォルト値
                    support_content_notes=notes if notes else '支援記録なし', 
                    log_status=log_status,
                    auto_created=True,
                    created_reason='support_record_compatibility'
                )
                db.session.add(daily_log)
                db.session.flush() # ID確定
            else:
                # 既に存在する場合も、ステータスを更新し、ノートを追記
                daily_log.log_status = log_status
                if notes:
                    if daily_log.support_content_notes and daily_log.support_content_notes != '活動トラッカーによる自動生成':
                        daily_log.support_content_notes += f"\n{notes}"
                    else:
                        daily_log.support_content_notes = notes
                
            # 該当利用者の最新のアクティブな支援計画・目標を自動取得する（任意）
            plan = SupportPlan.query.filter_by(user_id=user_id, plan_status='ACTIVE').first()
            plan_id = plan.id if plan else None
            
            goal = None
            if plan:
                goal = db.session.query(IndividualSupportGoal)\
                    .join(ShortTermGoal)\
                    .join(LongTermGoal)\
                    .filter(LongTermGoal.plan_id == plan.id)\
                    .first()
            goal_id = goal.id if goal else None

            # 支援記録(SupportRecord)を作成
            record = SupportRecord(
                user_id=user_id,
                log_date=log_date,
                supporter_id=supporter_id, 
                support_start_time=start_time,
                support_end_time=end_time,
                support_record_type='DIRECT_SUPPORT',
                support_plan_id=plan_id,
                support_goal_id=goal_id,
                support_content=f"[{tag.activity_name}] {notes}",
                support_duration_seconds=duration_seconds
            )

            db.session.add(record)
            db.session.flush() # record.id 確定
            entity_id = record.id

        else:
            # 互換性のため: 現在のtimecardを取得
            from backend.app.models import SupporterTimecard
            from backend.app.domain.attendance.exceptions import AttendanceValidationError
            
            ongoing_timecards = db.session.query(SupporterTimecard).filter(
                SupporterTimecard.supporter_id == supporter_id,
                SupporterTimecard.check_in != None,
                SupporterTimecard.check_out == None
            ).all()
            
            if len(ongoing_timecards) == 1:
                timecard_id = ongoing_timecards[0].id
            else:
                raise AttendanceValidationError("Ongoing timecard not found or multiple found")
            
            # 間接業務として保存 (MINUTES_ONLY mode for legacy compatibility)
            allocation = StaffActivityAllocationLog.query.filter_by(
                supporter_id=supporter_id,
                activity_date=log_date,
                staff_activity_master_id=tag_id,
                allocation_recording_mode='MINUTES_ONLY'
            ).first()
            
            if allocation:
                allocation.allocated_duration_seconds += duration_seconds
                allocation.allocated_minutes = int(allocation.allocated_duration_seconds / 60)
            else:
                allocation = StaffActivityAllocationLog(
                    supporter_id=supporter_id,
                    activity_date=log_date,
                    staff_activity_master_id=tag_id,
                    allocated_duration_seconds=duration_seconds,
                    supporter_timecard_id=timecard_id,
                    allocation_recording_mode='MINUTES_ONLY',
                    allocated_minutes=int(duration_seconds / 60)
                )
                db.session.add(allocation)
                db.session.flush()
            entity_id = allocation.id
                
        audit_log = AuditActionLog(
            action="CREATE_DAILY_LOG",
            user_id=user_id,
            actor_supporter_id=supporter_id,
            entity_type="SupportRecord" if tag.is_direct_support else "StaffActivityAllocationLog",
            entity_id=entity_id,
            reason=f"Support record recorded for tag {tag_id} by supporter {supporter_id}."
        )
        db.session.add(audit_log)
        
        return True

    def record_activity_allocation(self, supporter_id: int, data: dict):
        from backend.app.models import SupporterTimecard
        from backend.app.domain.attendance.exceptions import (
            AttendanceValidationError, AttendanceNotFoundError, AttendanceConflictError, AttendanceForbiddenError
        )

        mode = data.get('allocation_recording_mode')
        timecard_id = data.get('supporter_timecard_id')
        tag_id = data.get('staff_activity_master_id')

        if not mode or mode not in ('TIME_RANGE', 'MINUTES_ONLY'):
            raise AttendanceValidationError("Invalid or missing allocation_recording_mode")
        if not timecard_id:
            raise AttendanceValidationError("supporter_timecard_id is required")
        if not tag_id:
            raise AttendanceValidationError("staff_activity_master_id is required")

        timecard = db.session.query(SupporterTimecard).get(timecard_id)
        if not timecard or timecard.supporter_id != supporter_id:
            raise AttendanceNotFoundError("Timecard not found or unauthorized")

        osc_id = data.get('office_service_configuration_id')
        if osc_id:
            from backend.app.models import OfficeServiceConfiguration
            osc = db.session.query(OfficeServiceConfiguration).get(osc_id)
            if not osc:
                raise AttendanceNotFoundError("Service configuration not found")
            if osc.office_id != timecard.office_id:
                raise AttendanceValidationError("Office mismatch between timecard and service configuration")

        job_title_id = data.get('job_title_id')
        if job_title_id:
            from backend.app.models import SupporterJobAssignment
            valid_assignment = db.session.query(SupporterJobAssignment).filter(
                SupporterJobAssignment.supporter_id == supporter_id,
                SupporterJobAssignment.job_title_id == job_title_id,
                SupporterJobAssignment.office_service_configuration_id == osc_id,
                SupporterJobAssignment.start_date <= timecard.work_date,
                (SupporterJobAssignment.end_date >= timecard.work_date) | (SupporterJobAssignment.end_date == None)
            ).first()
            if not valid_assignment:
                raise AttendanceForbiddenError("Invalid or inactive job assignment for the given date")

        allocated_minutes = 0
        start_time = None
        end_time = None

        if mode == 'TIME_RANGE':
            start_str = data.get('allocation_start_time')
            end_str = data.get('allocation_end_time')
            if not start_str or not end_str:
                raise AttendanceValidationError("allocation_start_time and allocation_end_time are required for TIME_RANGE")
            
            # ISO string to datetime parsing
            start_time = datetime.fromisoformat(start_str.replace('Z', '+00:00')).astimezone(ZoneInfo("Asia/Tokyo")).replace(tzinfo=None)
            end_time = datetime.fromisoformat(end_str.replace('Z', '+00:00')).astimezone(ZoneInfo("Asia/Tokyo")).replace(tzinfo=None)
            
            if start_time >= end_time:
                raise AttendanceValidationError("start_time must be before end_time")
                
            if start_time < timecard.check_in:
                raise AttendanceValidationError("Activity cannot start before timecard check-in")
            if timecard.check_out and end_time > timecard.check_out:
                raise AttendanceValidationError("Activity cannot end after timecard check-out")
                
            # Overlap check
            overlap = db.session.query(StaffActivityAllocationLog).filter(
                StaffActivityAllocationLog.supporter_timecard_id == timecard_id,
                StaffActivityAllocationLog.allocation_recording_mode == 'TIME_RANGE',
                StaffActivityAllocationLog.allocation_start_time < end_time,
                start_time < StaffActivityAllocationLog.allocation_end_time
            ).first()
            if overlap:
                raise AttendanceConflictError("Activity time range overlaps with an existing allocation")
                
            duration = (end_time - start_time).total_seconds()
            allocated_minutes = int(duration / 60)
            
        elif mode == 'MINUTES_ONLY':
            minutes = data.get('allocated_minutes')
            if minutes is None:
                raise AttendanceValidationError("allocated_minutes is required for MINUTES_ONLY")
            if data.get('allocation_start_time') or data.get('allocation_end_time'):
                raise AttendanceValidationError("start_time and end_time are not allowed for MINUTES_ONLY")
            allocated_minutes = int(minutes)
            if allocated_minutes < 0:
                raise AttendanceValidationError("allocated_minutes must be non-negative")

        allocation = StaffActivityAllocationLog(
            supporter_id=supporter_id,
            activity_date=timecard.work_date,
            staff_activity_master_id=tag_id,
            allocated_duration_seconds=allocated_minutes * 60,
            supporter_timecard_id=timecard_id,
            office_service_configuration_id=data.get('office_service_configuration_id'),
            job_title_id=data.get('job_title_id'),
            allocation_recording_mode=mode,
            allocated_minutes=allocated_minutes,
            allocation_start_time=start_time,
            allocation_end_time=end_time
        )
        db.session.add(allocation)
        db.session.flush()
        return allocation

