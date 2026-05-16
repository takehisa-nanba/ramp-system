import sys
import os
import datetime
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app import create_app
from backend.app.extensions import db
from backend.app.models import User, AttendanceRecord, DailyLog
from sqlalchemy import func

app = create_app()
with app.app_context():
    user = User.query.filter_by(user_code='USR001').first()
    if user:
        today = datetime.date.today()
        # 今日の打刻を削除 (今日の日付のものだけ)
        # SQLiteの場合は func.date(timestamp) で比較可能
        AttendanceRecord.query.filter_by(user_id=user.id).filter(func.date(AttendanceRecord.timestamp) == today).delete()
        
        # 今日の日報を削除
        DailyLog.query.filter_by(user_id=user.id, log_date=today).delete()
        
        db.session.commit()
        print(f"✅ Reset status for {user.display_name} for today ({today}).")
    else:
        print("❌ User not found.")
