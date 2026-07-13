import uuid
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    dataset_id = Column(String, nullable=True)
    current_node = Column(String, default="UPLOAD")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    nodes = relationship("PipelineNode", back_populates="project", cascade="all, delete-orphan")


class PipelineNode(Base):
    __tablename__ = "pipeline_nodes"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    node_type = Column(String, nullable=False)  # UPLOAD, PROFILE, QUALITY, CLEANING, etc.
    status = Column(String, default="PENDING")  # PENDING, RUNNING, COMPLETED, FAILED
    input_meta = Column(JSON, default={})
    output_meta = Column(JSON, default={})
    logs = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    project = relationship("Project", back_populates="nodes")
