# backend/app/utils/timezone.py
from datetime import datetime, timezone, timedelta

try:
    from zoneinfo import ZoneInfo
    JST = ZoneInfo("Asia/Tokyo")
except Exception:
    JST = timezone(timedelta(hours=9))

def get_jst_today():
    return datetime.now(JST).date()

def get_jst_now():
    return datetime.now(JST)

