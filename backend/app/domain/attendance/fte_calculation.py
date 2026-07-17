# backend/app/domain/attendance/fte_calculation.py

class FteCalculationDomain:
    """
    人員配置基準（常勤換算）のための「みなし労働時間」を算出する純粋なドメインルール。
    この法則はUIやAPIの都合に左右されず、行政のルールに従う。
    """
    
    # 行政上、常勤のみなし労働時間として認められる休暇のリスト
    LEGAL_DEEMED_ABSENCE_TYPES = {
        'PAID_LEAVE',        # 有給休暇
        'REFRESH_LEAVE',     # リフレッシュ休暇
        'NURSING_LEAVE',     # 子の看病休暇
        'CARE_LEAVE',        # 介護休暇
        'BEREAVEMENT_LEAVE', # 慶弔休暇
    }

    @classmethod
    def calculate_deemed_minutes(
        cls, 
        employment_type: str, 
        absence_type: str, 
        scheduled_minutes: int
    ) -> int:
        """
        休暇時の「みなし時間(deemed_work_minutes)」を計算する法則。
        
        法則1: 常勤 ('FULL_TIME') かつ、法定休暇の場合、予定されていた労働時間をそのままみなし時間に加算する。
        法則2: それ以外（非常勤や、単なる欠勤）の場合、みなし時間は0となる。
        """
        if not absence_type:
            return 0
            
        is_full_time = employment_type == 'FULL_TIME'
        is_legal_leave = absence_type in cls.LEGAL_DEEMED_ABSENCE_TYPES
        
        if is_full_time and is_legal_leave:
            return scheduled_minutes
            
        return 0
