"""Calendar-month eligibility shared by all retention entry points."""
from calendar import monthrange
from datetime import date
from backend.app.utils.timezone import get_jst_today


def retention_eligible_date(placement_date: date) -> date:
    month_index = placement_date.year * 12 + placement_date.month - 1 + 6
    year, month = divmod(month_index, 12)
    month += 1
    return date(year, month, min(placement_date.day, monthrange(year, month)[1]))


def is_retention_eligible(placement_date, separation_date=None, on_date=None):
    on_date = on_date or get_jst_today()
    return (retention_eligible_date(placement_date) <= on_date
            and (separation_date is None or separation_date > on_date))
