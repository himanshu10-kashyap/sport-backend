import enum

from sqlalchemy import Column, DateTime, Enum, Integer, String, Text
from sqlalchemy.sql import func

from src.config.base import Base


class AdvertisementStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class AdvertisementScreen(str, enum.Enum):
    HOME = "home"
    SERIES = "series"
    MATCHES = "matches"
    VIDEOS = "videos"
    NEWS = "news"


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

    link = Column(
        String(500),
        nullable=True,
    )

    screen = Column(
        String(50),
        nullable=False,
        index=True,
    )  # see AdvertisementScreen: "home", "series", "matches", "videos", "news"

    status = Column(
        Enum(AdvertisementStatus, name="advertisement_status"),
        nullable=False,
        default=AdvertisementStatus.ACTIVE,
        server_default=AdvertisementStatus.ACTIVE.name,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )