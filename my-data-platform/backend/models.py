# backend/models.py
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Integer, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base

class User(Base):
    __tablename__ = "users"

    username = Column(String, primary_key=True, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    profile = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")


class Profile(Base):
    __tablename__ = "profiles"

    username = Column(String, ForeignKey("users.username", ondelete="CASCADE"), primary_key=True)
    full_name = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    avatar_url = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    location = Column(String, nullable=True)
    preferences = Column(JSON, default={})
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="profile")


class Token(Base):
    __tablename__ = "tokens"

    token_hash = Column(String, primary_key=True, index=True)
    username = Column(String, nullable=False)
    email = Column(String, nullable=False)
    type = Column(String, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False)
    username = Column(String, nullable=True)
    email = Column(String, nullable=True)
    client_ip = Column(String, nullable=True)
    status = Column(String, nullable=False)
    message = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


class CatalogItem(Base):
    __tablename__ = "catalog"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    name = Column(String, index=True)
    type = Column(String)
    owner = Column(String, index=True)
    visibility = Column(String, default="private")
    summary = Column(JSON, default={})
    preview_data = Column(JSON, default=[])
    ml_results = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class UserActivity(Base):
    __tablename__ = "user_activities"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True)
    action = Column(String)
    resource = Column(String, nullable=True)
    metadata_info = Column(JSON, default={})
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


class MLModelRecord(Base):
    __tablename__ = "ml_models"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_fingerprint = Column(String, index=True)
    target_column = Column(String)
    algorithm = Column(String)
    accuracy = Column(String)
    metrics = Column(JSON, default={})
    created_by = Column(String)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class WorkflowDefinition(Base):
    __tablename__ = "workflows"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    steps = Column(JSON, default=[])
    created_by = Column(String, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
