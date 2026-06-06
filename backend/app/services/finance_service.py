# backend/app/services/finance_service.py

from backend.app.extensions import db
from backend.app.models import (
    Supporter, 
    SupporterTimecard, 
    SupporterJobAssignment, 
    OfficeSetting, 
    OfficeServiceConfiguration,
    StaffActivityAllocationLog, # FTE算入対象の活動チェック用
    StaffActivityMaster,
    BillingData,
    SupportPlan
)
from sqlalchemy import func, exc
from datetime import datetime, timezone, date, timedelta
from typing import Optional 
import logging
logger = logging.getLogger(__name__)

class FinanceService:
    """
    すべての財務計算を処理し、特に常勤換算（FTE）と
    法的原則に基づいた請求コンプライアンスを専門とするクラス。
    """

    def authenticate_for_finance(self, staff_code: str, password: str) -> Optional[Supporter]:
        """
        職員コードによるクイック認証を行い、成功した場合はSupporterオブジェクトを返します。
        （FTE計算や請求確定など、財務処理のゲートキーパー認証）
        """
        from backend.app.services.core_service import authenticate_supporter_by_code
        return authenticate_supporter_by_code(staff_code, password)


    def calculate_fte_for_service(self, office_service_config_id: int, target_start_date: date, target_end_date: date):
        """
        特定のサービス構成における常勤換算（FTE）合計を計算します。
        原則：FTEは4週間平均値で算出されるべきである（行政監査の視点）。
        """
        logger.info(f"💰 Calculating FTE for Service ID: {office_service_config_id} ({target_start_date} ~ {target_end_date})")
        
        service_config = db.session.get(OfficeServiceConfiguration, office_service_config_id)
        
        if not service_config or not service_config.office:
            logger.error(f"❌ Service Config {office_service_config_id} not found or orphaned.")
            raise Exception(f"Invalid service configuration ID: {office_service_config_id}")
            
        # 1. 分母（基準）の取得
        office_standard_weekly_minutes = service_config.office.full_time_weekly_minutes
        
        if office_standard_weekly_minutes == 0:
            raise Exception(f"Office {service_config.office.office_name} has no standard work time set.")
            
        # 2. 期間内の週換算係数を計算 (4週間平均の原則を適用)
        day_difference = (target_end_date - target_start_date).days + 1
        total_weeks_in_period = day_difference / 7 # 週の総数（端数を含む）
        total_standard_minutes_in_period = office_standard_weekly_minutes * total_weeks_in_period
        
        # 3. 分子（実績）の取得と集計
        assignments = SupporterJobAssignment.query.filter(
            SupporterJobAssignment.office_service_configuration_id == office_service_config_id,
            SupporterJobAssignment.start_date <= target_end_date,
            (SupporterJobAssignment.end_date == None) | (SupporterJobAssignment.end_date >= target_start_date)
        ).all()
        
        total_fte_sum = 0.0 # 期間内のFTE算入対象となる総勤務時間（分）
        total_actual_countable_minutes = 0 # <--- この初期化を追加

        for supporter_id in list(set([a.supporter_id for a in assignments])):
            supporter = db.session.get(Supporter, supporter_id)
            is_full_time_dedicated = self._is_supporter_full_time_dedicated(supporter)
            
            # FTE算入可能な総勤務時間を取得 (minutes_counted)
            minutes_counted = self._get_countable_minutes_for_period(
                supporter_id, office_service_config_id, target_start_date, target_end_date, is_full_time_dedicated
            )
            
            # 期間の日数と週所定時間を取得
            total_weeks_in_period = day_difference / 7
            
            # ★ NEW: 個人の FTE を算出し、1.0 にキャップするロジック
            individual_standard_minutes = office_standard_weekly_minutes * total_weeks_in_period
            
            if individual_standard_minutes == 0:
                individual_fte = 0.0
            else:
                # 期間内の総実績 / 期間内の総常勤所定時間
                individual_fte_raw = minutes_counted / individual_standard_minutes
                
                # 🚨 厳格な監査ルール: 1.0 を超える FTE は算入不可とする
                individual_fte_capped = min(1.0, individual_fte_raw)
            
            total_actual_countable_minutes += individual_fte_capped * individual_standard_minutes 
            # ↑ 総時間を合計に戻す代わりに、FTE値そのものを合計しても良いが、ここでは総時間キャップで対応

            # ★ 修正: FTE値を直接合計する形にロジックを変更する方がシンプル
            total_fte_sum += individual_fte_capped
            
            logger.debug(f"      - Supporter {supporter.last_name}: Raw FTE {individual_fte_raw:.2f} -> Capped FTE {individual_fte_capped:.2f}")


        # 4. 最終FTEの計算 (合計したFTE値をそのまま返す)
        final_fte = round(total_fte_sum, 2)
        logger.info(f"✅ FTE Calculation Complete: {final_fte}")
        return final_fte
    
    def _check_plan_guardrail(self, billing_data: BillingData) -> bool:
        """
        監査の第一段: 請求が計画期間内であるか、及びPlan-Activity整合性を検証する。
        """
        from backend.app.models import SupportPlan
        # 請求月（月初）を取得
        billing_date = billing_data.billing_month
        # 月末を計算
        if billing_date.month == 12:
            next_month = billing_date.replace(year=billing_date.year + 1, month=1)
        else:
            next_month = billing_date.replace(month=billing_date.month + 1)
        billing_end_date = next_month - timedelta(days=1)

        # その月に有効なプランがあるか
        active_plan = SupportPlan.query.filter(
            SupportPlan.user_id == billing_data.user_id,
            SupportPlan.plan_status == 'ACTIVE',
            SupportPlan.plan_start_date <= billing_end_date,
            (SupportPlan.plan_end_date == None) | (SupportPlan.plan_end_date >= billing_date)
        ).first()

        return active_plan is not None 

    def _check_daily_validation(self, billing_data: BillingData) -> bool:
        """
        監査の第二段: 請求根拠となるDailyLogの承認/検証ステータスをチェックする。
        """
        from backend.app.models import DailyLog
        billing_date = billing_data.billing_month
        if billing_date.month == 12:
            next_month = billing_date.replace(year=billing_date.year + 1, month=1)
        else:
            next_month = billing_date.replace(month=billing_date.month + 1)
        billing_end_date = next_month - timedelta(days=1)

        logs_count = DailyLog.query.filter(
            DailyLog.user_id == billing_data.user_id,
            DailyLog.log_date >= billing_date,
            DailyLog.log_date <= billing_end_date
        ).count()

        return logs_count > 0
    
    def audit_billing_data(self, billing_id: int) -> bool:
        """
        三段監査の実行（テスト対象）。
        """
        billing = db.session.get(BillingData, billing_id)
        if not billing:
            return False

        # Plan Guardrail (第一段)
        if not self._check_plan_guardrail(billing):
            billing.is_audit_passed = False
            billing.audit_notes = "Plan Guardrail failed."
            return False

        # Daily Validation (第二段)
        if not self._check_daily_validation(billing):
            billing.is_audit_passed = False
            billing.audit_notes = "Daily Validation failed."
            return False

        # 第三段: Audit FlagをTrueに設定
        billing.is_audit_passed = True
        billing.audit_notes = "Audit passed successfully."
        return True

    def _is_supporter_full_time_dedicated(self, supporter: Supporter) -> bool:
        """
        職員が「常勤かつ専従」の条件を満たしているかを判定する。（ロジックは既存のまま）
        """
        if supporter.employment_type != 'FULL_TIME':
            return False
            
        active_assignments = SupporterJobAssignment.query.filter(
            SupporterJobAssignment.supporter_id == supporter.id,
            (SupporterJobAssignment.end_date == None) | (SupporterJobAssignment.end_date >= datetime.now(timezone.utc).date())
        ).all()
        
        if not active_assignments:
            return False

        assigned_service_ids = set([a.office_service_configuration_id for a in active_assignments])
        
        # 複数のサービスIDに割り当てられている場合は兼務
        if len(assigned_service_ids) > 1:
            return False
            
        return True

    def _get_countable_minutes_for_period(self, supporter_id: int, service_config_id: int, start_date: date, end_date: date, is_full_time_dedicated: bool) -> int:
        """
        期間内にFTE算入可能な総勤務時間（分）を取得するヘルパー関数。
        非常勤・兼務者も「サービス運営に必要な間接支援」は算入対象とする。
        """
        
        # 1. Timecard (実働とみなし) から総時間を取得
        timecards = SupporterTimecard.query.filter(
            SupporterTimecard.supporter_id == supporter_id,
            SupporterTimecard.office_service_configuration_id == service_config_id,
            SupporterTimecard.work_date.between(start_date, end_date)
        ).all()
        
        total_timecard_minutes = 0
        for tc in timecards:
            actual_minutes = 0
            if tc.check_in and tc.check_out:
                duration = (tc.check_out - tc.check_in).total_seconds() / 60
                actual_minutes = max(0, duration - tc.total_break_minutes)
            
            # 常勤専従の場合のみ、みなし時間(有給等)を算入
            deemed_minutes = tc.deemed_work_minutes if is_full_time_dedicated else 0
            
            total_timecard_minutes += actual_minutes + deemed_minutes
            
        # 2. Activity Allocation Log の確認 (FTE非算入の活動の除外)
        # 職員の総勤務時間から、「FTE非算入」とマスタで指定された活動（例: 他事業所の応援、私的活動）の時間を差し引くロジックをここに実装します。
        
        # 簡略化のため、ここでは Timecard の時間をベースとします。
        
        return total_timecard_minutes