from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.sql import func

from src.config.base import Base

RATE_LIMIT_DEFAULT_SECONDS = 2


class RateLimit(Base):
    __tablename__ = "rate_limit"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=False,
        default=1,
    )

    value = Column(
        Integer,
        nullable=False,
        default=RATE_LIMIT_DEFAULT_SECONDS,
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )