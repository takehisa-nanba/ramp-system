from backend.app.extensions import db
# 🚨 修正点: 'from app.models...' を相対パスに変更
from backend.app.models import (
    Supporter, 
    SupporterTimecard, 
    SupporterJobAssignment, 
    OfficeSetting, 
    OfficeServiceConfiguration
)
from sqlalchemy import func, extract
from datetime import datetime

class FinanceService:
    """
    Handles all financial calculations, specializing in Full-Time Equivalent (FTE)
    calculations and billing compliance based on legal principles.
    This service is the single source of truth for Principle 3 (Accounting Accuracy).
    """

    def calculate_fte_for_service(self, office_service_config_id: int, target_start_date: datetime.date, target_end_date: datetime.date):
        """
        Calculates the total FTE for a specific service configuration (jigyosho_bango)
        over a given period (usually a week or a month).
        
        This is the master logic that enforces all compliance rules.
        """
        
        # 1. Get the Denominator (The Standard): 常勤換算の「分母」を取得
        # ----------------------------------------------------------------
        service_config = OfficeServiceConfiguration.query.get(office_service_config_id)
        if not service_config or not service_config.office:
            raise Exception(f"Invalid service configuration ID: {office_service_config_id}")
            
        # Get the standard full-time minutes for this specific office (e.g., 2400 mins/week)
        # 基準（分母）は事業所（OfficeSetting）が持つ
        office_standard_minutes = service_config.office.full_time_weekly_minutes
        if office_standard_minutes == 0:
            raise Exception(f"Office {service_config.office.office_name} has no standard work time set.")
            
        # ---
        # 2. Get the Numerator (The Facts): 職員ごとの「分子」を計算
        # ----------------------------------------------------------------
        
        # Find all supporters *assigned* to this service during this period
        # このサービスに割り当てられている全ての職務履歴を取得
        assignments = SupporterJobAssignment.query.filter(
            SupporterJobAssignment.office_service_configuration_id == office_service_config_id,
            SupporterJobAssignment.start_date <= target_end_date,
            (SupporterJobAssignment.end_date == None) | (SupporterJobAssignment.end_date >= target_start_date)
        ).all()
        
        total_fte = 0.0
        
        # Get unique supporter IDs from the assignments
        supporter_ids = list(set([a.supporter_id for a in assignments]))

        for supporter_id in supporter_ids:
            supporter = Supporter.query.get(supporter_id)
            
            # --- 3. Apply Legal Rules (The Logic): 法令ルール（みなし時間）を適用 ---
            
            # Fetch all timecards for this supporter *at this service*
            # この職員の、このサービスでの勤怠記録を取得
            timecards = SupporterTimecard.query.filter(
                SupporterTimecard.supporter_id == supporter_id,
                SupporterTimecard.office_service_configuration_id == office_service_config_id,
                SupporterTimecard.work_date.between(target_start_date, target_end_date)
            ).all()
            
            weekly_minutes_to_count = 0
            
            # Check if this supporter is '常勤・専従' (Full-Time AND Dedicated)
            # 職員が「常勤・専従」か「それ以外」かを判定する
            is_full_time_dedicated = self._is_supporter_full_time_dedicated(supporter)

            for tc in timecards:
                # A. Calculate actual work minutes
                # A. 実働時間を計算
                actual_minutes = 0
                if tc.check_in and tc.check_out:
                    duration = (tc.check_out - tc.check_in).total_seconds() / 60
                    actual_minutes = max(0, duration - tc.total_break_minutes)
                
                # B. Check deemed work minutes (e.g., Paid Leave)
                # B. みなし時間（有給など）を取得
                deemed_minutes = tc.deemed_work_minutes or 0
                
                # C. Apply the Rule (原理1, 3)
                # C. ルールを適用
                if is_full_time_dedicated:
                    # '常勤・専従' の場合: 実働 + みなし
                    weekly_minutes_to_count += actual_minutes + deemed_minutes
                else:
                    # '非常勤' or '常勤・兼務' の場合: 実働のみ
                    weekly_minutes_to_count += actual_minutes
            
            # Add this supporter's contribution to the total FTE
            # この職員の常勤換算数を合計に加算
            total_fte += (weekly_minutes_to_count / office_standard_minutes)
            
        # Return the final calculated FTE, rounded appropriately
        return round(total_fte, 2)


    def _is_supporter_full_time_dedicated(self, supporter: Supporter) -> bool:
        """
        Helper function to determine if a supporter meets the "Full-Time AND Dedicated"
        criteria for including deemed work hours (e.g., paid leave) in FTE calculations.
        
        「常勤・専従」の定義（有給算入の条件）を満たすか判定する。
        """
        
        # 1. Check Employment Type (契約身分の確認)
        # 法令上の「常勤」か？ (時短職員 'SHORTENED_FT' は「常勤」ではない)
        if supporter.employment_type != 'FULL_TIME':
            return False
            
        # 2. Check for Inter-Office Assignments (事業所間兼務の確認)
        # この職員の「職務割り当て」が、複数のサービス(事業所番号)にまたがっていないか？
        active_assignments = SupporterJobAssignment.query.filter(
            SupporterJobAssignment.supporter_id == supporter.id,
            (SupporterJobAssignment.end_date == None) | (SupporterJobAssignment.end_date >= datetime.utcnow().date())
        ).all()
        
        if not active_assignments:
            return False # No active assignments

        # Get all unique service config IDs this supporter is assigned to
        assigned_service_ids = set([a.office_service_configuration_id for a in active_assignments])
        
        # If the supporter is assigned to more than one service ID, they are '兼務' (not dedicated)
        # 複数のサービスIDに割り当てられていれば「兼務」であり、「専従」ではない
        if len(assigned_service_ids) > 1:
            return False
            
        # Passed all checks: Must be Full-Time and Dedicated
        return True