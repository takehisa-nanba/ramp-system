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
from datetime import datetime, date

class FinanceService:
    """
    すべての財務計算を処理し、特に常勤換算（FTE）と
    法的原則に基づいた請求コンプライアンスを専門とするクラス。
    このサービスは、原理3（会計の正確性）における「唯一の信頼できる情報源」です。
    """

    def calculate_fte_for_service(self, office_service_config_id: int, target_start_date: date, target_end_date: date):
        """
        特定のサービス構成（事業所番号）における、指定期間（通常は週または月）の
        常勤換算（FTE）合計を計算します。
        """
        
        # 1. 分母（基準）の取得
        # ----------------------------------------------------------------
        # LegacyAPIWarning回避: db.session.getを使用
        service_config = db.session.get(OfficeServiceConfiguration, office_service_config_id)
        
        if not service_config or not service_config.office:
            raise Exception(f"Invalid service configuration ID: {office_service_config_id}")
            
        # 基準（分母）を取得 (例: 2400分/週)
        office_standard_minutes = service_config.office.full_time_weekly_minutes
        if office_standard_minutes == 0:
            raise Exception(f"Office {service_config.office.office_name} has no standard work time set.")
            
        # ---
        # 2. 分子（事実）の取得: 職員ごとの稼働積み上げ
        # ----------------------------------------------------------------
        
        # 指定期間中に、このサービスに「割り当て」られている全ての職務履歴を取得
        assignments = SupporterJobAssignment.query.filter(
            SupporterJobAssignment.office_service_configuration_id == office_service_config_id,
            SupporterJobAssignment.start_date <= target_end_date,
            (SupporterJobAssignment.end_date == None) | (SupporterJobAssignment.end_date >= target_start_date)
        ).all()
        
        total_fte = 0.0
        
        # 重複を除いた職員IDリスト
        supporter_ids = list(set([a.supporter_id for a in assignments]))

        for supporter_id in supporter_ids:
            supporter = db.session.get(Supporter, supporter_id)
            
            # --- 3. 法的ルールの適用（ロジック）: みなし時間の判定 ---
            
            # この職員の、このサービス（事業所番号）における勤怠記録を取得
            timecards = SupporterTimecard.query.filter(
                SupporterTimecard.supporter_id == supporter_id,
                SupporterTimecard.office_service_configuration_id == office_service_config_id,
                SupporterTimecard.work_date.between(target_start_date, target_end_date)
            ).all()
            
            weekly_minutes_to_count = 0
            
            # この職員が「常勤・専従」の要件（有給算入可）を満たすか判定する
            is_full_time_dedicated = self._is_supporter_full_time_dedicated(supporter)

            for tc in timecards:
                # A. 実働時間の計算
                actual_minutes = 0
                if tc.check_in and tc.check_out:
                    # 秒単位の差分を分に変換
                    duration = (tc.check_out - tc.check_in).total_seconds() / 60
                    # 休憩時間を引く
                    actual_minutes = max(0, duration - tc.total_break_minutes)
                
                # B. みなし時間（有給休暇など）の確認
                deemed_minutes = tc.deemed_work_minutes or 0
                
                # C. ルールの適用（原理1, 3）
                if is_full_time_dedicated:
                    # '常勤・専従' の場合: 実働 + みなし時間（有給）を算入
                    weekly_minutes_to_count += actual_minutes + deemed_minutes
                else:
                    # '非常勤' または '常勤・兼務' の場合: 実働時間のみ算入（有給は0分扱い）
                    weekly_minutes_to_count += actual_minutes
            
            # この職員の貢献分（週の合計分数 / 事業所の常勤基準）を全体のFTEに加算
            total_fte += (weekly_minutes_to_count / office_standard_minutes)
            
        # 最終的な常勤換算数を小数点第2位で丸めて返す
        return round(total_fte, 2)


    def _is_supporter_full_time_dedicated(self, supporter: Supporter) -> bool:
        """
        職員が「常勤かつ専従」の条件を満たしているかを判定するヘルパー関数。
        """
        
        # 1. 契約身分の確認
        # 法令上の「常勤」か？ (時短職員 'SHORTENED_FT' は「常勤」ではない)
        if supporter.employment_type != 'FULL_TIME':
            return False
            
        # 2. 事業所間兼務の確認
        # この職員の有効な「職務割り当て」が、複数のサービス(事業所番号)にまたがっていないか？
        active_assignments = SupporterJobAssignment.query.filter(
            SupporterJobAssignment.supporter_id == supporter.id,
            (SupporterJobAssignment.end_date == None) | (SupporterJobAssignment.end_date >= datetime.utcnow().date())
        ).all()
        
        if not active_assignments:
            return False # 有効な割り当てがない

        # この職員が割り当てられているユニークなサービス構成IDを取得
        assigned_service_ids = set([a.office_service_configuration_id for a in active_assignments])
        
        # 複数のサービスIDに割り当てられていれば「兼務（事業所間兼務）」であり、「専従」ではない
        if len(assigned_service_ids) > 1:
            return False
            
        # 全てのチェックを通過: 「常勤・専従」である
        return True