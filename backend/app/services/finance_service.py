# 🚨 修正点: 'from backend.app.extensions' (絶対参照)
from backend.app.extensions import db
from backend.app.models import (
    Supporter, 
    SupporterTimecard, 
    SupporterJobAssignment, 
    OfficeSetting, 
    OfficeServiceConfiguration
)
from sqlalchemy import func, extract
# ★ 修正: timezone をインポート
from datetime import datetime, timezone, date, timezone
import logging

# ★ ロガーの取得
logger = logging.getLogger(__name__)

class FinanceService:
    """
    すべての財務計算を処理し、特に常勤換算（FTE）と
    法的原則に基づいた請求コンプライアンスを専門とするクラス。
    """

    def calculate_fte_for_service(self, office_service_config_id: int, target_start_date: date, target_end_date: date):
        """
        特定のサービス構成における常勤換算（FTE）合計を計算します。
        """
        logger.info(f"💰 Calculating FTE for Service ID: {office_service_config_id} ({target_start_date} ~ {target_end_date})")
        
        # 1. 分母（基準）の取得
        service_config = db.session.get(OfficeServiceConfiguration, office_service_config_id)
        
        if not service_config or not service_config.office:
            logger.error(f"❌ Service Config {office_service_config_id} not found or orphaned.")
            raise Exception(f"Invalid service configuration ID: {office_service_config_id}")
            
        office_standard_minutes = service_config.office.full_time_weekly_minutes
        if office_standard_minutes == 0:
            logger.error(f"❌ Standard work time is 0 for Office {service_config.office.id}.")
            raise Exception(f"Office {service_config.office.office_name} has no standard work time set.")
            
        logger.debug(f"   -> Standard (Denominator): {office_standard_minutes} min/week")

        # 2. 分子（事実）の取得
        assignments = SupporterJobAssignment.query.filter(
            SupporterJobAssignment.office_service_configuration_id == office_service_config_id,
            SupporterJobAssignment.start_date <= target_end_date,
            (SupporterJobAssignment.end_date == None) | (SupporterJobAssignment.end_date >= target_start_date)
        ).all()
        
        total_fte = 0.0
        supporter_ids = list(set([a.supporter_id for a in assignments]))
        logger.debug(f"   -> Found {len(supporter_ids)} assigned supporters.")

        for supporter_id in supporter_ids:
            supporter = db.session.get(Supporter, supporter_id)
            
            # 3. 法的ルールの適用
            timecards = SupporterTimecard.query.filter(
                SupporterTimecard.supporter_id == supporter_id,
                SupporterTimecard.office_service_configuration_id == office_service_config_id,
                SupporterTimecard.work_date.between(target_start_date, target_end_date)
            ).all()
            
            weekly_minutes_to_count = 0
            is_full_time_dedicated = self._is_supporter_full_time_dedicated(supporter)
            
            for tc in timecards:
                # A. 実働時間
                actual_minutes = 0
                if tc.check_in and tc.check_out:
                    duration = (tc.check_out - tc.check_in).total_seconds() / 60
                    actual_minutes = max(0, duration - tc.total_break_minutes)
                
                # B. みなし時間
                deemed_minutes = tc.deemed_work_minutes or 0
                
                # C. ルール適用
                if is_full_time_dedicated:
                    # 常勤・専従: 実働 + みなし
                    weekly_minutes_to_count += actual_minutes + deemed_minutes
                else:
                    # 非常勤・兼務: 実働のみ
                    weekly_minutes_to_count += actual_minutes
            
            # 個人ごとのFTE算出
            individual_fte = weekly_minutes_to_count / office_standard_minutes
            total_fte += individual_fte
            
            logger.debug(f"      - Supporter {supporter.last_name}: {weekly_minutes_to_count}min -> {individual_fte:.2f} FTE (Dedicated: {is_full_time_dedicated})")
            
        final_fte = round(total_fte, 2)
        logger.info(f"✅ FTE Calculation Complete: {final_fte}")
        return final_fte


    def _is_supporter_full_time_dedicated(self, supporter: Supporter) -> bool:
        """
        職員が「常勤かつ専従」の条件を満たしているかを判定する。
        """
        # 1. 契約身分
        if supporter.employment_type != 'FULL_TIME':
            return False
            
        # 2. 事業所間兼務
        active_assignments = SupporterJobAssignment.query.filter(
            SupporterJobAssignment.supporter_id == supporter.id,
            # ★ 修正: utcnow() -> now(timezone.utc)
            (SupporterJobAssignment.end_date == None) | (SupporterJobAssignment.end_date >= datetime.now(timezone.utc).date())
        ).all()
        
        if not active_assignments:
            return False

        assigned_service_ids = set([a.office_service_configuration_id for a in active_assignments])
        
        if len(assigned_service_ids) > 1:
            return False
            
        return True