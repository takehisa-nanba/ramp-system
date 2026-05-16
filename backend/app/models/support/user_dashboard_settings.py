from backend.app.extensions import db
from sqlalchemy import Column, Integer, String, ForeignKey, JSON

class UserDailyLogSetting(db.Model):
    """
    事業所ごとの利用者日報の質問項目設定。
    """
    __tablename__ = 'user_daily_log_settings'
    
    id = Column(Integer, primary_key=True)
    office_id = Column(Integer, ForeignKey('office_settings.id'), nullable=False, unique=True)
    
    # JSONで項目を保持。
    config = Column(JSON, nullable=False, default=lambda: {
        "morning_fields": [
            {"id": "mood", "label": "今日の気分", "type": "score", "required": True}
        ],
        "evening_fields": [
            {"id": "review", "label": "今日頑張ったことや、明日の目標", "type": "text", "required": True}
        ]
    })

    
    office = db.relationship('OfficeSetting')
