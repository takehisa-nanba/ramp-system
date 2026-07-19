# backend/app/services/attendance_service.py

import calendar
from datetime import date, datetime
from sqlalchemy.orm import Session
from backend.app.models import Supporter, EmploymentShiftPattern, StaffDailyShift, SupporterTimecard, AttendanceCorrectionRequest
from backend.app.domain.attendance.fte_calculation import FteCalculationDomain
from backend.app.domain.attendance.decision_rules import AttendanceDecisionDomain
from backend.app.domain.attendance.exceptions import (
    AttendanceDomainError,
    AttendanceValidationError,
    AttendanceNotFoundError,
    AttendanceConflictError
)

class AttendanceService:
    def __init__(self, db_session: Session):
        self.db = db_session
        
    def _check_admin_authorization(self, approver_id: int):
        """
        管理権限チェックの物理法則 (仮実装: 本来はRBACなどを参照)
        """
        approver = self.db.query(Supporter).get(approver_id)
        if not approver or approver.employment_type != 'FULL_TIME':
            raise AttendanceForbiddenError("Only FULL_TIME admins can approve or edit attendance")

    def _check_timecard_exists(self, supporter_id: int, target_date: date):
        """
        タイムカード保護の物理法則: 打刻済みの日は一切のシフト変更を許可しない
        """
        timecard = self.db.query(SupporterTimecard).filter_by(
            supporter_id=supporter_id,
            work_date=target_date
        ).first()
        if timecard:
            raise AttendanceConflictError("Timecard already exists for this date. Manual changes are prohibited.")

    def create_manual_shift(self, admin_id: int, data: dict):
        self._check_admin_authorization(admin_id)
        supporter_id = data.get('supporter_id')
        target_date = date.fromisoformat(data['target_date'])
        
        self._check_timecard_exists(supporter_id, target_date)
        
        existing = self.db.query(StaffDailyShift).filter_by(
            supporter_id=supporter_id, target_date=target_date
        ).first()
        if existing:
            raise AttendanceConflictError("Shift already exists for this date.")
            
        start_dt = datetime.strptime(f"{data['target_date']} {data['start_time']}", "%Y-%m-%d %H:%M") if data.get('start_time') else None
        end_dt = datetime.strptime(f"{data['target_date']} {data['end_time']}", "%Y-%m-%d %H:%M") if data.get('end_time') else None
        
        # Office config fallback
        from backend.app.models.core.office import OfficeServiceConfiguration
        supporter = self.db.query(Supporter).get(supporter_id)
        sc = self.db.query(OfficeServiceConfiguration).filter_by(office_id=supporter.office_id).first()
        office_config_id = sc.id if sc else 1
        
        shift = StaffDailyShift(
            supporter_id=supporter_id,
            office_service_configuration_id=office_config_id,
            target_date=target_date,
            planned_start_time=start_dt,
            planned_end_time=end_dt,
            planned_break_minutes=data.get('break_minutes', 0)
        )
        self.db.add(shift)
        self.db.commit()
        return shift

    def update_manual_shift(self, admin_id: int, shift_id: int, data: dict):
        self._check_admin_authorization(admin_id)
        shift = self.db.query(StaffDailyShift).get(shift_id)
        if not shift:
            raise AttendanceNotFoundError("Shift not found.")
            
        self._check_timecard_exists(shift.supporter_id, shift.target_date)
        if shift.is_confirmed:
            raise AttendanceConflictError("Cannot edit a confirmed shift.")
            
        if 'start_time' in data and data['start_time']:
            shift.planned_start_time = datetime.strptime(f"{shift.target_date} {data['start_time']}", "%Y-%m-%d %H:%M")
        if 'end_time' in data and data['end_time']:
            shift.planned_end_time = datetime.strptime(f"{shift.target_date} {data['end_time']}", "%Y-%m-%d %H:%M")
        if 'break_minutes' in data:
            shift.planned_break_minutes = data['break_minutes']
            
        self.db.commit()
        return shift

    def delete_manual_shift(self, admin_id: int, shift_id: int):
        self._check_admin_authorization(admin_id)
        shift = self.db.query(StaffDailyShift).get(shift_id)
        if not shift:
            raise AttendanceNotFoundError("Shift not found.")
            
        self._check_timecard_exists(shift.supporter_id, shift.target_date)
        if shift.is_confirmed:
            raise AttendanceConflictError("Cannot delete a confirmed shift.")
            
        self.db.delete(shift)
        self.db.commit()

    def generate_monthly_shifts(self, target_year: int, target_month: int, supporter_id: int = None, ai_instruction: str = None):
        """
        基本パターン(EmploymentShiftPattern)から指定月のシフト(StaffDailyShift)を一括生成する。
        """
        num_days = calendar.monthrange(target_year, target_month)[1]
        
        query = self.db.query(EmploymentShiftPattern)
        if supporter_id:
            query = query.filter(EmploymentShiftPattern.supporter_id == supporter_id)
        
        patterns = query.all()
        if not patterns:
            return 0
            
        pattern_dict = {}
        for p in patterns:
            if p.supporter_id not in pattern_dict:
                pattern_dict[p.supporter_id] = {}
            pattern_dict[p.supporter_id][p.day_of_week] = p

        created_count = 0
        
        # Supporter情報を事前取得
        supporters = self.db.query(Supporter).filter(Supporter.id.in_(pattern_dict.keys())).all()
        supporter_map = {s.id: s for s in supporters}
        
        # JobAssignments を全件取得して日付ごとに解決できるようにする
        from backend.app.models import SupporterJobAssignment
        job_assignments = self.db.query(SupporterJobAssignment).filter(
            SupporterJobAssignment.supporter_id.in_(pattern_dict.keys())
        ).all()
        ja_map = {}
        for ja in job_assignments:
            if ja.supporter_id not in ja_map:
                ja_map[ja.supporter_id] = []
            ja_map[ja.supporter_id].append(ja)
        
        # Fallback office_config
        fallback_config_map = {}
        from backend.app.models.core.office import OfficeServiceConfiguration
        for s in supporters:
            sc = self.db.query(OfficeServiceConfiguration).filter_by(office_id=s.office_id).first()
            fallback_config_map[s.id] = sc.id if sc else 1
            
        if ai_instruction:
            from backend.app.services.ai_shift_service import AiShiftService
            ai_svc = AiShiftService()
            if ai_svc.client:
                # Gather data for AI
                current_shifts_data = []
                start_date = date(target_year, target_month, 1)
                end_date = date(target_year, target_month, num_days)
                existing_shifts = self.db.query(StaffDailyShift).filter(
                    StaffDailyShift.target_date >= start_date,
                    StaffDailyShift.target_date <= end_date
                ).all()
                for s in existing_shifts:
                    if not s.is_confirmed:
                        current_shifts_data.append({
                            "id": s.id,
                            "supporter_id": s.supporter_id,
                            "date": str(s.target_date),
                            "start_time": s.planned_start_time.strftime("%H:%M") if s.planned_start_time else None,
                            "end_time": s.planned_end_time.strftime("%H:%M") if s.planned_end_time else None
                        })
                
                pattern_data = []
                for p in patterns:
                    pattern_data.append({
                        "supporter_id": p.supporter_id,
                        "day_of_week": p.day_of_week,
                        "start_time": str(p.start_time) if p.start_time else None,
                        "end_time": str(p.end_time) if p.end_time else None
                    })
                    
                overwrites = ai_svc.adjust_shifts(current_shifts_data, pattern_data, ai_instruction)
                if overwrites:
                    # Apply AI overwrites
                    for ow in overwrites:
                        try:
                            sid = ow.get('supporter_id')
                            target_date_str = ow.get('date')
                            action = ow.get('action')
                            target_date_obj = datetime.strptime(target_date_str, "%Y-%m-%d").date()
                            
                            # check timecard
                            timecard = self.db.query(SupporterTimecard).filter_by(supporter_id=sid, work_date=target_date_obj).first()
                            if timecard:
                                continue # protect
                                
                            existing = self.db.query(StaffDailyShift).filter_by(supporter_id=sid, target_date=target_date_obj).first()
                            
                            if action == 'DELETE':
                                if existing and not existing.is_confirmed:
                                    self.db.delete(existing)
                                    created_count += 1
                            elif action in ('UPDATE', 'CREATE'):
                                start_t = ow.get('start_time')
                                end_t = ow.get('end_time')
                                if not start_t or not end_t:
                                    continue
                                start_dt = datetime.strptime(f"{target_date_str} {start_t}", "%Y-%m-%d %H:%M")
                                end_dt = datetime.strptime(f"{target_date_str} {end_t}", "%Y-%m-%d %H:%M")
                                
                                if existing:
                                    if not existing.is_confirmed:
                                        existing.planned_start_time = start_dt
                                        existing.planned_end_time = end_dt
                                        created_count += 1
                                else:
                                    office_config_id = fallback_config_map.get(sid, 1)
                                    # simplification: just use fallback for AI creations
                                    shift = StaffDailyShift(
                                        supporter_id=sid,
                                        office_service_configuration_id=office_config_id,
                                        target_date=target_date_obj,
                                        planned_start_time=start_dt,
                                        planned_end_time=end_dt,
                                        planned_break_minutes=ow.get('break_minutes', 0)
                                    )
                                    self.db.add(shift)
                                    created_count += 1
                        except Exception as e:
                            print("AI overwrite error:", e)
                    self.db.commit()
                    return created_count

        for day in range(1, num_days + 1):
            current_date = date(target_year, target_month, day)
            day_name = current_date.strftime('%A')
            
            for sid, p_map in pattern_dict.items():
                supporter = supporter_map.get(sid)
                if not supporter:
                    continue
                
                # 入社前、退職後は対象外
                if current_date < supporter.hire_date or (supporter.retirement_date and current_date > supporter.retirement_date):
                    is_active_date = False
                else:
                    is_active_date = True
                    
                # その日の office_service_configuration_id を解決
                office_config_id = fallback_config_map.get(sid, 1)
                for ja in ja_map.get(sid, []):
                    if ja.start_date <= current_date and (not ja.end_date or ja.end_date >= current_date):
                        office_config_id = ja.office_service_configuration_id
                        break
                        
                # タイムカード（実績）がすでに存在する場合は、保護のため一切変更しない
                timecard = self.db.query(SupporterTimecard).filter_by(
                    supporter_id=sid,
                    work_date=current_date
                ).first()
                if timecard:
                    continue
                
                pattern = p_map.get(day_name) if is_active_date else None
                
                existing = self.db.query(StaffDailyShift).filter_by(
                    supporter_id=sid,
                    target_date=current_date
                ).first()
                
                if pattern and pattern.start_time and pattern.end_time:
                    start_dt = datetime.strptime(f"{current_date} {pattern.start_time}", "%Y-%m-%d %H:%M")
                    end_dt = datetime.strptime(f"{current_date} {pattern.end_time}", "%Y-%m-%d %H:%M")
                    
                    if existing:
                        if not existing.is_confirmed:
                            existing.planned_start_time = start_dt
                            existing.planned_end_time = end_dt
                            existing.planned_break_minutes = pattern.break_minutes
                            created_count += 1
                    else:
                        shift = StaffDailyShift(
                            supporter_id=sid,
                            office_service_configuration_id=office_config_id,
                            target_date=current_date,
                            planned_start_time=start_dt,
                            planned_end_time=end_dt,
                            planned_break_minutes=pattern.break_minutes
                        )
                        self.db.add(shift)
                        created_count += 1
                else:
                    if existing and not existing.is_confirmed:
                        self.db.delete(existing)
                        created_count += 1
                        
    def check_overlap(self, supporter_id: int, start_time: datetime, end_time: datetime = None, exclude_timecard_id: int = None):
        """対象職員の勤務区間重複を検証する"""
        query = self.db.query(SupporterTimecard).filter(
            SupporterTimecard.supporter_id == supporter_id
        )
        if exclude_timecard_id:
            query = query.filter(SupporterTimecard.id != exclude_timecard_id)
            
        timecards = query.all()
        for tc in timecards:
            if not tc.check_in:
                continue
            e_start = tc.check_in
            e_end = tc.check_out
            n_start = start_time
            n_end = end_time
            
            if e_end is None and n_end is None:
                return True
            if e_end is None:
                if n_end is None or n_end > e_start:
                    return True
                continue
            if n_end is None:
                if n_start < e_end:
                    return True
                continue
            if max(e_start, n_start) < min(e_end, n_end):
                return True
        return False

    def get_ongoing_timecard(self, supporter_id: int) -> SupporterTimecard:
        ongoing_timecards = self.db.query(SupporterTimecard).filter(
            SupporterTimecard.supporter_id == supporter_id,
            SupporterTimecard.check_in != None,
            SupporterTimecard.check_out == None
        ).all()
        
        if len(ongoing_timecards) == 1:
            return ongoing_timecards[0]
        elif len(ongoing_timecards) > 1:
            raise AttendanceValidationError("Multiple ongoing timecards found")
        return None

    def clock_in(self, supporter_id: int, office_id: int, location_type: str, location_detail: str) -> SupporterTimecard:
        from sqlalchemy.exc import IntegrityError
        from zoneinfo import ZoneInfo
        from backend.app.domain.attendance.exceptions import AttendanceForbiddenError
        
        supporter = (
            self.db.query(Supporter)
            .filter(Supporter.id == supporter_id)
            .with_for_update()
            .one_or_none()
        )
        if not supporter:
            raise AttendanceNotFoundError("Supporter not found")

        now = datetime.now(ZoneInfo("Asia/Tokyo")).replace(tzinfo=None)
        today = now.date()

        ongoing = self.get_ongoing_timecard(supporter_id)
        if ongoing:
            raise AttendanceConflictError("Already clocked in")

        valid_locations = {"OFFICE", "CLIENT_COMPANY", "USER_HOME", "REMOTE", "EXTERNAL_FACILITY", "TRAVEL", "OTHER"}
        if location_type not in valid_locations:
            raise AttendanceValidationError(f"Invalid location_type: {location_type}")

        if self.check_overlap(supporter_id, start_time=now):
            raise AttendanceConflictError("Timecard overlaps with existing completed record")

        from backend.app.models import SupporterJobAssignment
        from backend.app.models.core.office import OfficeServiceConfiguration
        
        assignments = self.db.query(SupporterJobAssignment).join(
            OfficeServiceConfiguration,
            SupporterJobAssignment.office_service_configuration_id == OfficeServiceConfiguration.id
        ).filter(
            SupporterJobAssignment.supporter_id == supporter_id,
            OfficeServiceConfiguration.office_id == office_id,
            SupporterJobAssignment.start_date <= today,
            (SupporterJobAssignment.end_date >= today) | (SupporterJobAssignment.end_date == None)
        ).all()
        
        if len(assignments) == 0:
            raise AttendanceForbiddenError("Not assigned to this office")
        elif len(assignments) > 1:
            raise AttendanceValidationError("Multiple active assignments in this office")
            
        osc_id = assignments[0].office_service_configuration_id

        from sqlalchemy import func
        max_seq = self.db.query(func.max(SupporterTimecard.sequence_no)).filter(
            SupporterTimecard.supporter_id == supporter_id,
            SupporterTimecard.work_date == today
        ).scalar()
        next_seq = 1 if max_seq is None else max_seq + 1

        timecard = SupporterTimecard(
            supporter_id=supporter_id,
            work_date=today,
            office_id=office_id,
            office_service_configuration_id=osc_id,
            location_type=location_type,
            location_detail=location_detail,
            sequence_no=next_seq,
            check_in=now
        )
        self.db.add(timecard)
        try:
            self.db.flush()
        except IntegrityError as e:
            self.db.rollback()
            constraint = getattr(getattr(e, "orig", None), "diag", None)
            if constraint and getattr(constraint, "constraint_name", None) in ("uq_supporter_ongoing_timecard", "uq_supporter_timecard_seq"):
                raise AttendanceConflictError("Already clocked in or sequence conflict")
            raise e
            
        return timecard

    def clock_out(self, supporter_id: int, timecard_id: int = None, break_minutes: int = 0) -> SupporterTimecard:
        if timecard_id is None:
            timecard = self.get_ongoing_timecard(supporter_id)
            if not timecard:
                raise AttendanceNotFoundError("Timecard not found")
            timecard_id = timecard.id
            
        timecard = self.db.query(SupporterTimecard).get(timecard_id)
        if not timecard or timecard.supporter_id != supporter_id:
            raise AttendanceNotFoundError("Timecard not found")

        if timecard.check_out:
            raise AttendanceConflictError("Already clocked out")

        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo("Asia/Tokyo")).replace(tzinfo=None)

        if timecard.check_in and now <= timecard.check_in:
            raise AttendanceValidationError("check_out must be after check_in")

        if break_minutes < 0:
            raise AttendanceValidationError("break_minutes cannot be negative")

        if timecard.check_in:
            duration_mins = (now - timecard.check_in).total_seconds() / 60
            if break_minutes > duration_mins:
                raise AttendanceValidationError("break_minutes cannot exceed worked duration")

        if self.check_overlap(supporter_id, start_time=timecard.check_in, end_time=now, exclude_timecard_id=timecard.id):
            raise AttendanceConflictError("Timecard overlaps with existing completed record")

        timecard.check_out = now
        timecard.total_break_minutes = break_minutes
        
        # calc scheduled_work_minutes
        timecard.scheduled_work_minutes = 0
        if timecard.check_in:
            duration = timecard.check_out - timecard.check_in
            total_mins = int(duration.total_seconds() / 60)
            actual_work_mins = max(0, total_mins - break_minutes)
            timecard.scheduled_work_minutes = actual_work_mins

        return timecard

    def process_attendance_correction(self, request_id: int, approver_id: int, is_approved: bool):
        """
        勤怠修正申請を処理し、Decision（意思決定）を下す。
        """
        self._check_admin_authorization(approver_id)
        
        req = self.db.query(AttendanceCorrectionRequest).get(request_id)
        if not req or req.request_status != 'PENDING':
            raise ValueError("Invalid request or already processed")
            
        req.approver_id = approver_id
        req.processed_at = datetime.now()
        req.request_status = 'APPROVED' if is_approved else 'REJECTED'
        
        if is_approved:
            # TODO: 申請内容(JSON等)に基づいて編集データを組み立てる処理を実装
            # ここではダミーデータを使用 (実際には req から取得する)
            edit_data = {} 
            
            # 対象のタイムカードを取得
            timecard = self.db.query(SupporterTimecard).filter_by(
                supporter_id=req.supporter_id,
                work_date=req.target_date
            ).first()
            
            if timecard:
                # 申請承認によるみなし時間の再計算とDecision適用を統一メソッドで実行
                self._apply_attendance_changes(timecard, approver_id, edit_data, reason=f"Approved correction request {request_id}")
            
        self.db.commit()
        return req

    def direct_edit_timecard(self, timecard_id: int, approver_id: int, edit_data: dict):
        """
        管理者が直接タイムカードを編集する経路。
        """
        self._check_admin_authorization(approver_id)
        
        timecard = self.db.query(SupporterTimecard).get(timecard_id)
        if not timecard:
            raise ValueError("Timecard not found")
            
        self._apply_attendance_changes(timecard, approver_id, edit_data, reason="Admin direct edit")
        
        self.db.commit()
        return timecard
        
    def _apply_attendance_changes(self, timecard: SupporterTimecard, approver_id: int, edit_data: dict, reason: str):
        """
        直接編集・申請承認の両経路から呼ばれる共通ロジック。
        みなし時間の再計算と、Decisionの適用（監査ログ生成）を確実に行う。
        """
        supporter = self.db.query(Supporter).get(timecard.supporter_id)
        
        # --- 1. みなし時間の再計算 (FteCalculationDomain) ---
        new_is_absent = edit_data.get('is_absent', timecard.is_absent)
        new_absence_type = edit_data.get('absence_type', timecard.absence_type)
        deemed = timecard.deemed_work_minutes
        
        if new_is_absent:
            # 該当日のシフト予定を取得
            shift = self.db.query(StaffDailyShift).filter_by(
                supporter_id=supporter.id, 
                target_date=timecard.work_date
            ).first()
            
            scheduled_mins = 0
            if shift and shift.planned_start_time and shift.planned_end_time:
                diff = shift.planned_end_time - shift.planned_start_time
                scheduled_mins = int(diff.total_seconds() / 60) - (shift.planned_break_minutes or 0)
                
            deemed = FteCalculationDomain.calculate_deemed_minutes(
                employment_type=supporter.employment_type,
                absence_type=new_absence_type,
                scheduled_minutes=scheduled_mins
            )
            
        # --- 2. 意思決定の適用と監査ログ発行 (AttendanceDecisionDomain) ---
        audit_logs = AttendanceDecisionDomain.apply_decision_to_timecard(
            timecard=timecard,
            approver_id=approver_id,
            reason=reason,
            check_in=edit_data.get('check_in'),
            check_out=edit_data.get('check_out'),
            break_minutes=edit_data.get('break_minutes'),
            is_absent=edit_data.get('is_absent'),
            absence_type=edit_data.get('absence_type'),
            deemed_work_minutes=deemed
        )
        
        # 生成された監査ログをDBに保存
        for log in audit_logs:
            self.db.add(log)
