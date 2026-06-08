from backend.app.extensions import db
from backend.app.models import StaffActivityMaster, UserDailyLog, SupportRecord, StaffActivityAllocationLog, User, IndividualSupportGoal, ShortTermGoal, LongTermGoal, SupportPlan, AuditActionLog
from datetime import datetime, timezone
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
            # 間接業務として保存
            allocation = StaffActivityAllocationLog.query.filter_by(
                supporter_id=supporter_id,
                activity_date=log_date,
                staff_activity_master_id=tag_id
            ).first()
            
            if allocation:
                allocation.allocated_duration_seconds += duration_seconds
            else:
                allocation = StaffActivityAllocationLog(
                    supporter_id=supporter_id,
                    activity_date=log_date,
                    staff_activity_master_id=tag_id,
                    allocated_duration_seconds=duration_seconds
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
