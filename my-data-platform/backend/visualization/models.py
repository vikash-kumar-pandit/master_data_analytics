import uuid
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON
from datetime import datetime, timezone
from database import Base

class DatasetVisualization(Base):
    __tablename__ = "dataset_visualizations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, index=True, nullable=False)
    chart_type = Column(String, nullable=False)  # e.g., "sales_trend", "correlation_heatmap"
    column_names = Column(JSON, nullable=False)   # e.g., ["sales", "date"]
    image_base64 = Column(Text, nullable=False)  # Embedded rendered plot string
    business_value = Column(Integer, nullable=False, default=3)  # Rating 1-5
    confidence = Column(Float, nullable=False, default=80.0)      # Score 0-100
    explanation = Column(Text, nullable=True)     # Technical explanation
    story = Column(Text, nullable=True)           # Business narrative insights
    stats_interpretation = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
