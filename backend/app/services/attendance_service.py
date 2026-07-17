# backend/app/services/attendance_service.py

import calendar
from datetime import date, datetime
from sqlalchemy.orm import Session
from backend.app.models import Supporter, EmploymentShiftPattern, StaffDailyShift, SupporterTimecard, AttendanceCorrectionRequest
from backend.app.domain.attendance.fte_calculation import FteCalculationDomain
from backend.app.domain.attendance.decision_rules import AttendanceDecisionDomain

class AttendanceService:
    def __init__(self, db_session: Session):
        self.db = db_session
        
    def _check_admin_authorization(self, approver_id: int):
        """
        管理権限チェックの物理法則 (仮実装: 本来はRBACなどを参照)
        """
        approver = self.db.query(Supporter).get(approver_id)
        if not approver or approver.employment_type != 'FULL_TIME':
            raise PermissionError("Only FULL_TIME admins can approve or edit attendance")

    def generate_monthly_shifts(self, target_year: int, target_month: int, supporter_id: int = None):
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
        
        for day in range(1, num_days + 1):
            current_date = date(target_year, target_month, day)
            day_name = current_date.strftime('%A')
            
            for sid, p_map in pattern_dict.items():
                if day_name in p_map:
                    pattern = p_map[day_name]
                    
                    existing = self.db.query(StaffDailyShift).filter_by(
                        supporter_id=sid,
                        target_date=current_date
                    ).first()
                    
                    if not existing and pattern.start_time and pattern.end_time:
                        start_dt = datetime.strptime(f"{current_date} {pattern.start_time}", "%Y-%m-%d %H:%M")
                        end_dt = datetime.strptime(f"{current_date} {pattern.end_time}", "%Y-%m-%d %H:%M")
                        
                        shift = StaffDailyShift(
                            supporter_id=sid,
                            target_date=current_date,
                            planned_start_time=start_dt,
                            planned_end_time=end_dt,
                            planned_break_minutes=pattern.break_minutes
                        )
                        self.db.add(shift)
                        created_count += 1
                        
        self.db.commit()
        return created_count

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
