import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    UUID,
    String,
    DateTime,
    PrimaryKeyConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from internal.extension.database_extension import db


class App(db.Model):
    """应用模型"""
    __tablename__ = "app"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_app_id"),
        Index("idx_app_account_id", "account_id")
    )

    id = Column(UUID, default=uuid.uuid4, nullable=False)
    account_id = Column(UUID, nullable=False)
    name = Column(String(255), default="", nullable=False)
    icon = Column(String(255), default="", nullable=False)
    config = Column(JSONB, nullable=False, default={})
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    def to_dict(self) -> dict:
        """模型转字典，用于接口响应/日志序列化（UUID、datetime 需转成 JSON 可序列化类型）"""
        return {
            "id": str(self.id) if self.id else None,
            "account_id": str(self.account_id) if self.account_id else None,
            "name": self.name,
            "icon": self.icon,
            "config": self.config,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }
