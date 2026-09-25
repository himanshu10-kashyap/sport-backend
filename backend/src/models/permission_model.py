from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.config.base import Base


class Permission(Base):

    __tablename__ = "permissions"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    userid = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "admins.userid",
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
        DateTime,
        server_default=func.now()
    )

    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )

    admin = relationship(
        "Admin",
        back_populates="permissions",
        primaryjoin="Admin.userid == Permission.userid",
    )