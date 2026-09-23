from sqlalchemy import Column, Integer, String, DateTime,Text
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy import Boolean

from src.config.base import Base

class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(Text, nullable=False)
    status = Column(
        String,
        default="ACTIVE"
    )
    role = Column(
        String,
        default="ADMIN"
    )
    token = Column(
        Text, nullable=True)
    
    is_reset = Column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False
    )    
    is_deleted = Column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False
    )    
    userid = Column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        unique=True,
        nullable=False
    )
    created_by = Column(
        UUID(as_uuid=True),
        nullable=True
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
 