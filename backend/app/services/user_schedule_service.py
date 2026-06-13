# backend/app/services/user_schedule_service.py
from datetime import date, datetime, timedelta, UTC
from backend.app.extensions import db
from backend.app.models import (
    UserScheduleTemplate, UserDailySchedule, UserScheduleRequest, 
    SupportRecord, User, Supporter
)
from backend.app.utils.errors import ValidationError

class UserScheduleService:
    def generate_daily_schedules_for_month(self, user_id: int, target_month: date, force_overwrite: bool = False) -> int:
        """
        指定された利用者の、指定月に対応する日別予定をテンプレートから自動生成する。
        """
        user = db.session.get(User, user_id)
        if not user:
            raise ValidationError("指定された利用者が見つかりません。")

        # 対象月の開始日と終了日を計算
        start_date = date(target_month.year, target_month.month, 1)
        if target_month.month == 12:
            end_date = date(target_month.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(target_month.year, target_month.month + 1, 1) - timedelta(days=1)

        # 曜日マッピング
        weekday_map = {
            0: "Monday",
            1: "Tuesday",
            2: "Wednesday",
            3: "Thursday",
            4: "Friday",
            5: "Saturday",
            6: "Sunday"
        }

        # テンプレートを取得
        templates = UserScheduleTemplate.query.filter_by(user_id=user_id).all()
        template_dict = {t.day_of_week: t for t in templates}

        from backend.app.models.support.attendance_workflow import AttendanceRecord
        from sqlalchemy import func

        created_count = 0
        curr = start_date
        while curr <= end_date:
            day_name = weekday_map[curr.weekday()]
            template = template_dict.get(day_name)
            
            # 既存予定のチェック
            existing = UserDailySchedule.query.filter_by(user_id=user_id, date=curr).first()
            
            # 実績打刻 (CHECK_IN) が存在するかチェック
            has_attendance = AttendanceRecord.query.filter_by(
                user_id=user_id,
                record_type='CHECK_IN'
            ).filter(
                func.date(AttendanceRecord.timestamp) == curr
            ).first() is not None

            # 承認された申請があるかチェック
            has_approved_request = UserScheduleRequest.query.filter_by(
                user_id=user_id,
                target_date=curr,
                request_status='APPROVED'
            ).first() is not None

            # 既存レコードがあり、上書きが要求されている場合
            if existing and force_overwrite:
                # 実績や承認された申請がある日は、予定を上書きしない（維持する）
                if not has_attendance and not has_approved_request:
                    if template and template.is_scheduled:
                        existing.start_time = template.start_time
                        existing.end_time = template.end_time
                        existing.schedule_kind = 'NORMAL'
                        existing.approval_status = 'APPROVED'
                        existing.location_type = template.location_type or 'ON_SITE'
                    else:
                        existing.start_time = None
                        existing.end_time = None
                        existing.schedule_kind = 'NORMAL'
                        existing.approval_status = 'APPROVED'
                        existing.location_type = None
                    created_count += 1
            # 新規作成の場合
            elif not existing:
                if template and template.is_scheduled:
                    daily = UserDailySchedule(
                        user_id=user_id,
                        date=curr,
                        start_time=template.start_time,
                        end_time=template.end_time,
                        schedule_kind='NORMAL',
                        approval_status='APPROVED',
                        location_type=template.location_type or 'ON_SITE'
                    )
                    db.session.add(daily)
                    created_count += 1
                else:
                    daily = UserDailySchedule(
                        user_id=user_id,
                        date=curr,
                        schedule_kind='NORMAL',
                        approval_status='APPROVED',
                        location_type=None
                    )
                    db.session.add(daily)
                    created_count += 1
            curr += timedelta(days=1)

        db.session.commit()
        return created_count

    def create_schedule_request(
        self,
        user_id: int,
        target_date: date,
        request_type: str,
        request_reason: str,
        requested_start_time: str = None,
        requested_end_time: str = None,
        requested_by_user_id: int = None,
        requested_by_supporter_id: int = None
    ) -> UserScheduleRequest:
        """
        予定の追加、欠席、変更申請を作成する。
        重複申請を防ぐためのガードレールを含む。
        """
        if request_type not in ['ABSENCE', 'EXTRA_DAY', 'SHIFT_TIME']:
            raise ValidationError("無効な申請タイプです。")

        if not request_reason or len(request_reason.strip()) < 10:
            raise ValidationError("申請理由は10文字以上で入力してください。")

        # 時間チェック (日跨ぎ防止)
        if requested_start_time and requested_end_time:
            sh, sm = map(int, requested_start_time.split(':'))
            eh, em = map(int, requested_end_time.split(':'))
            if (eh * 60 + em) <= (sh * 60 + sm):
                raise ValidationError("終了時間は開始時間より後の時間に設定してください。日跨ぎ予定は非対応です。")

        # 重複するPENDING申請のガードレール
        existing = UserScheduleRequest.query.filter_by(
            user_id=user_id,
            target_date=target_date,
            request_status='PENDING'
        ).first()
        if existing:
            raise ValidationError("同じ日付に対する未決の申請がすでに存在します。")

        req = UserScheduleRequest(
            user_id=user_id,
            target_date=target_date,
            request_type=request_type,
            requested_start_time=requested_start_time,
            requested_end_time=requested_end_time,
            request_reason=request_reason,
            request_status='PENDING',
            requested_by_user_id=requested_by_user_id,
            requested_by_supporter_id=requested_by_supporter_id
        )
        db.session.add(req)
        db.session.commit()
        return req

    def decide_schedule_request(
        self,
        request_id: int,
        supporter_id: int,
        status: str,
        decision_reason: str
    ) -> UserScheduleRequest:
        """
        予定申請を承認または却下する。
        """
        req = db.session.get(UserScheduleRequest, request_id)
        if not req:
            raise ValidationError("指定された申請が見つかりません。")

        if req.request_status != 'PENDING':
            raise ValidationError("この申請はすでに処理済みです。")

        if status not in ['APPROVED', 'REJECTED']:
            raise ValidationError("ステータスは APPROVED または REJECTED を指定してください。")

        if not decision_reason or len(decision_reason.strip()) < 10:
            raise ValidationError("意思決定の判断理由は10文字以上で入力してください。")

        req.request_status = status
        req.decided_by_supporter_id = supporter_id
        req.decided_at = datetime.now(tz=UTC)
        req.decision_reason = decision_reason

        if status == 'APPROVED':
            # 確定予定 (UserDailySchedule) への反映
            daily = UserDailySchedule.query.filter_by(user_id=req.user_id, date=req.target_date).first()
            if not daily:
                daily = UserDailySchedule(
                    user_id=req.user_id,
                    date=req.target_date
                )
                db.session.add(daily)

            daily.schedule_request_id = req.id

            if req.request_type == 'ABSENCE':
                daily.approval_status = 'CANCELLED'
                daily.start_time = None
                daily.end_time = None

                # 欠席対応記録 (ABSENCE_CONTACT) の下書きを自動起票
                # 重複作成を避けるチェック
                existing_record = SupportRecord.query.filter_by(
                    user_id=req.user_id,
                    log_date=req.target_date,
                    support_record_type='ABSENCE_CONTACT'
                ).first()

                if not existing_record:
                    absence_record = SupportRecord(
                        user_id=req.user_id,
                        log_date=req.target_date,
                        supporter_id=supporter_id,
                        support_record_type='ABSENCE_CONTACT',
                        support_content=f"[欠席対応連絡] 欠席理由: {req.request_reason}",
                        decision_reason=f"[システム連動] 欠席申請承認に伴う自動生成。判断理由: {decision_reason}",
                        observation_note="【職員入力用】欠席の連絡受付、および必要に応じた安否確認対応の結果をここに記録してください。"
                    )
                    db.session.add(absence_record)

            elif req.request_type == 'EXTRA_DAY':
                daily.schedule_kind = 'EXTRA'
                daily.start_time = req.requested_start_time
                daily.end_time = req.requested_end_time

            elif req.request_type == 'SHIFT_TIME':
                daily.schedule_kind = 'SUBSTITUTED'
                daily.start_time = req.requested_start_time
                daily.end_time = req.requested_end_time

        db.session.commit()
        return req
