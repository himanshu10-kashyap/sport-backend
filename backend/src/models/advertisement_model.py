from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from src.config.base import Base


class Advertisement(Base):
    __tablename__ = "advertisements"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True,
    )

    title = Column(
        String(255),
        nullable=False,
    )

    description = Column(
        Text,
        nullable=True,
    )

    file = Column(
        String(255),
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
