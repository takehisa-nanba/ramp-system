# 🚨 修正点: 'from backend.app.extensions' (絶対参照)
from backend.app.extensions import db
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime, Text, func

# ====================================================================
# 1. UserSkill (利用者のスキル・アセスメント)
# ====================================================================
class UserSkill(db.Model):
    """
    利用者のスキル（訓練・アセスメントの対象）。
    SkillMasterに基づき、職員の評価と共に履歴管理する。
    """
    __tablename__ = 'user_skills'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # どのスキルか (SkillMasterを参照)
    skill_master_id = Column(Integer, ForeignKey('skill_master.id'), nullable=False)
    
    # --- 評価（原理2） ---
    assessment_notes = Column(Text) # 職員の客観的な評価や観察記録
    training_evaluation_score = Column(Integer) # 訓練評価スコア
    
    # --- 履歴管理（原理1） ---
    acquisition_date = Column(Date) # 取得日または評価日
    
    user = relationship('User', back_populates='skills')
    skill_master = relationship('SkillMaster', back_populates='user_skills')

# ====================================================================
# 2. UserDocument (源泉文書の管理)
# ====================================================================
class UserDocument(db.Model):
    """
    利用者関連文書（履歴書、職務経歴書など）。
    「訓練の成果物」または「監査証憑」として管理する。
    """
    __tablename__ = 'user_documents'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # どの種別の文書か (DocumentTypeMasterを参照)
    document_type_master_id = Column(Integer, ForeignKey('document_type_master.id'), nullable=False)
    
    # --- 証憑（原理1） ---
    document_url = Column(String(500), nullable=False) # 書類ファイルそのもののURL
    uploaded_at = Column(DateTime, default=func.now()) # システム登録日
    
    # --- 訓練としての評価（原理2） ---
    # 職員がWordの体裁などを評価・フィードバックする欄
    assessment_notes_by_staff = Column(Text) 
    
    user = relationship('User', back_populates='documents')
    document_type_master = relationship('DocumentTypeMaster', back_populates='user_documents')