import uuid
from sqlalchemy import Column, String, DateTime, Text, JSON, ForeignKey
from datetime import datetime, timezone
from database import Base

class CopilotSession(Base):
    __tablename__ = "copilot_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, index=True, nullable=False)
    title = Column(String, nullable=False, default="New Discussion")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class CopilotMessage(Base):
    __tablename__ = "copilot_messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("copilot_sessions.id"), nullable=False)
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    assets_meta = Column(JSON, nullable=True)  # Store generated charts/actions metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class CopilotMemory(Base):
    __tablename__ = "copilot_memories"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, index=True, nullable=False)
    key = Column(String, nullable=False)
    value = Column(Text, nullable=False)
    category = Column(String, nullable=True)  # e.g., "last_metric", "last_chart"
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
