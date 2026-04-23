"""
User model and related entities.
"""

import enum
import uuid

from sqlalchemy import ARRAY, TIMESTAMP, Column, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class RoleEnum(str, enum.Enum):
    user = "user"
    devops = "devops"
    admin = "admin"


class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    role = Column(Enum(RoleEnum, name="role"), nullable=False)
    agent_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=False, default=list)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    knowledge_bases = relationship("KnowledgeBase", back_populates="creator")
    guardrails = relationship("Guardrail", back_populates="creator")
