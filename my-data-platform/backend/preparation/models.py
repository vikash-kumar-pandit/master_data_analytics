import uuid
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON, ForeignKey
from datetime import datetime, timezone
from database import Base

class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, index=True, nullable=False)
    version_num = Column(Integer, nullable=False)
    file_path = Column(String, nullable=False)
    rows = Column(Integer, nullable=False)
    columns = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Transformation(Base):
    __tablename__ = "transformations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    operation_type = Column(String, nullable=False)
    parameters = Column(JSON, nullable=False)  # e.g. {"columns": ["val"], "method": "mean"}
    description = Column(Text, nullable=True)  # AI-generated natural explanation
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class TransformationHistory(Base):
    __tablename__ = "transformation_histories"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, index=True, nullable=False)
    version_id = Column(String, ForeignKey("dataset_versions.id"), nullable=False)
    transformation_id = Column(String, ForeignKey("transformations.id"), nullable=False)
    step_num = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class UndoRedoStack(Base):
    __tablename__ = "undo_redo_stacks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, index=True, unique=True, nullable=False)
    current_pointer = Column(Integer, default=0)
    max_pointer = Column(Integer, default=0)
