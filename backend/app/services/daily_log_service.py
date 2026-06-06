from backend.app.extensions import db
from backend.app.models import StaffActivityMaster, DailyLog, DailyLogActivity, StaffActivityAllocationLog, User, IndividualSupportGoal, ShortTermGoal, LongTermGoal, SupportPlan
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
        duration_minutes: int,
        user_id: int = None,
        notes: str = ""
    ):
        """
        日報（活動）を記録する。
        直接支援ならDailyLogActivityへ、間接業務ならStaffActivityAllocationLogへ保存する。
        """
        tag = db.session.get(StaffActivityMaster, tag_id)
        if not tag:
            raise ValidationError("無効な活動タグです")

        if tag.is_direct_support:
            if not user_id:
                raise ValidationError("直接支援の場合、利用者の選択が必須です")

            # 🛡️ 重複時間帯ガードレール
            overlapping_activity = db.session.query(DailyLogActivity)\
                .join(DailyLog, DailyLogActivity.daily_log_id == DailyLog.id)\
                .filter(
                    DailyLogActivity.supporter_id == supporter_id,
                    DailyLog.log_date == log_date,
                    DailyLog.user_id != user_id,
                    DailyLogActivity.support_start_time < end_time,
                    start_time < DailyLogActivity.support_end_time
                ).first()

            if overlapping_activity:
                other_user = db.session.get(User, overlapping_activity.daily_log.user_id)
                other_user_name = other_user.display_name if other_user else "他の利用者"
                start_formatted = overlapping_activity.support_start_time.strftime('%H:%M') if overlapping_activity.support_start_time else "--:--"
                end_formatted = overlapping_activity.support_end_time.strftime('%H:%M') if overlapping_activity.support_end_time else "--:--"
                raise ValidationError(f"既に同時間帯（{start_formatted}〜{end_formatted}）に別の利用者（{other_user_name}様）の支援記録が登録されています。重複した時間帯での支援記録は作成できません。")

            # 該当利用者の当日のDailyLogを探す（なければ作成）
            daily_log = DailyLog.query.filter_by(user_id=user_id, log_date=log_date).first()
            if not daily_log:
                daily_log = DailyLog(
                    user_id=user_id,
                    log_date=log_date,
                    location_type='ON_SITE', # デフォルト値
                    support_content_notes='活動トラッカーによる自動生成', # 必須項目
                    log_status='DRAFT'
                )
                db.session.add(daily_log)
                db.session.flush() # ID確定
                
            # 該当利用者の最新の目標を自動取得する（簡易化のため）
            goal = db.session.query(IndividualSupportGoal)\
                .join(ShortTermGoal)\
                .join(LongTermGoal)\
                .join(SupportPlan)\
                .filter(SupportPlan.user_id == user_id)\
                .filter(SupportPlan.plan_status == 'ACTIVE')\
                .first()
                
            if not goal:
                raise ValidationError("この利用者に有効な支援目標が見つかりません。活動を記録できません。")

            activity = DailyLogActivity(
                daily_log_id=daily_log.id,
                supporter_id=supporter_id, 
                support_goal_id=goal.id, 
                support_content=f"[{tag.activity_name}] {notes}",
                support_start_time=start_time,
                support_end_time=end_time
            )

            db.session.add(activity)

        else:
            # 間接業務として保存
            allocation = StaffActivityAllocationLog.query.filter_by(
                supporter_id=supporter_id,
                activity_date=log_date,
                staff_activity_master_id=tag_id
            ).first()
            
            if allocation:
                allocation.allocated_minutes += duration_minutes
            else:
                allocation = StaffActivityAllocationLog(
                    supporter_id=supporter_id,
                    activity_date=log_date,
                    staff_activity_master_id=tag_id,
                    allocated_minutes=duration_minutes
                )
                db.session.add(allocation)
                
        return True
