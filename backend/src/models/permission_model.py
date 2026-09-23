from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime
)

from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy import Boolean

from src.config.base import Base


class Permission(Base):
    __tablename__ = "permissions"
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    adminid = Column(
        Integer,
        ForeignKey(
            "admins.id",  
            ondelete="CASCADE",
            onupdate="CASCADE"
        ),
        nullable=False,
        index=True
    )
    permission = Column(
        String(255),
        nullable=False
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )