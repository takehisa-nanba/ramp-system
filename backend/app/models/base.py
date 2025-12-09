# backend/app/models/base.py (FINAL, Pylance Fix Applied)

from sqlalchemy.orm import DeclarativeBase, declared_attr, Mapped, mapped_column
from sqlalchemy import Integer, DateTime, func
from typing import Any
import datetime
import re

class Base(DeclarativeBase):
    """
    全てのORMモデルが継承する基底クラス。
    """
    __abstract__ = True 
    
    # 全てのモデルに共通の 'id' (主キー) を定義
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # 【テーブル命名規則】クラス名を全て小文字にして 's' を付与
    @declared_attr.directive
    def __tablename__(cls) -> str : # <-- ここ！ 型ヒント (-> str) を削除しました
        # 例: User -> users, Supporter -> supporters
        name = re.sub(r'(?<!^)(?=[A-Z])', '_', cls.__name__).lower()
        return name + "s"

# 共通のデバッグ表現
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id!r})"

# ====================================================================
# 2. Mix-in: TimestampMixin (作成日時・更新日時)
# ====================================================================
class TimestampMixin:
    """
    全てのモデルに作成日時 (created_at) と更新日時 (updated_at) を自動で追加するMix-in。
    """
    # created_at: 作成日時（DEFAULTで自動設定）
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        default=func.now()
    )
    
    # updated_at: 更新日時（DEFAULT/ONUPDATEで自動更新）
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        default=func.now(), 
        onupdate=func.now()
    )