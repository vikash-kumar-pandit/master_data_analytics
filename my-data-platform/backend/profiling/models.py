import uuid
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON
from datetime import datetime, timezone
from database import Base

class DatasetProfile(Base):
    __tablename__ = "dataset_profiles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String, index=True, nullable=False)
    rows = Column(Integer, nullable=False)
    columns = Column(Integer, nullable=False)
    memory = Column(Float, nullable=False)
    disk = Column(Float, nullable=False)
    schema_info = Column(JSON, nullable=False)
    warnings = Column(JSON, nullable=False)
    recommendations = Column(JSON, nullable=False)
    statistics = Column(JSON, nullable=False)
    story = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
