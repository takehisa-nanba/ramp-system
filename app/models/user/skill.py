# app/models/user/skill.py
from app.extensions import db
from datetime import datetime, timezone
from sqlalchemy.orm import relationship

class Qualification(db.Model):
    """
    利用者の資格情報モデル (利用者に1対多)
    """
    __tablename__ = 'qualifications'
    __table_args__ = ({"extend_existing": True},)
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    qualification_name = db.Column(db.String(150), nullable=False) # 資格名
    acquisition_date = db.Column(db.Date) # 取得年月日
    issuing_organization = db.Column(db.String(150), nullable=True) # 発行機関 (任意)
    
    # --- タイムスタンプ ---
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    remarks = db.Column(db.Text)

    # --- リレーションシップ ---
    user = db.relationship('User', back_populates='qualifications')

    def __repr__(self):
        return f'<Qualification {self.id} (User: {self.user_id})>'