from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str


class CatalogQuery(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)


class WorkflowCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    steps: list[str] = Field(..., min_length=1)
    target_column: str | None = None
    text_column: str | None = None
    categories: list[str] | None = None
    num_clusters: int = Field(default=3, ge=1, le=100)
    sample_index: int = Field(default=0, ge=0)
    top_k: int = Field(default=10, ge=1, le=100)


class WorkflowRunRequest(BaseModel):
    rows: list[dict[str, Any]] = Field(..., min_length=1)


class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    rows: list[dict[str, Any]] = Field(..., min_length=1)
    previous_rows: list[dict[str, Any]] | None = None
    analysis: dict[str, Any] | None = None


class ForecastRequest(BaseModel):
    rows: list[dict[str, Any]] = Field(..., min_length=1)
    metric_column: str | None = None
    date_column: str | None = None
    horizon: int = Field(default=7, ge=1, le=30)


class CompareRequest(BaseModel):
    before_rows: list[dict[str, Any]] = Field(..., min_length=1)
    after_rows: list[dict[str, Any]] = Field(..., min_length=1)


class StructuredReportRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    subtitle: str = Field(default="", max_length=1000)
    sections: list[Any] = Field(..., min_length=1)
    output_format: str = Field(default="pdf", pattern="^(pdf|pptx)$")


class InsightRequest(BaseModel):
    data_summary: dict[str, Any]


class ClusteringRequest(BaseModel):
    rows: list[dict[str, Any]] = Field(..., min_length=1)
    num_clusters: int = Field(default=3, ge=1, le=100)


class NLPRequest(BaseModel):
    rows: list[dict[str, Any]] = Field(..., min_length=1)
    text_column: str = Field(..., min_length=1)
    categories: list[str] = Field(..., min_length=1)


class ExplainRequest(BaseModel):
    rows: list[dict[str, Any]] = Field(..., min_length=1)
    target_column: str = Field(..., min_length=1)
    sample_index: int = Field(default=0, ge=0)
    top_k: int = Field(default=12, ge=1, le=100)


class CreateShareRequest(BaseModel):
    report_title: str = Field(..., min_length=1, max_length=500)
    report_data: dict[str, Any] = Field(..., min_length=1)
    expires_days: int = Field(default=30, ge=1, le=365)
    access_level: str = Field(default="view", pattern="^(view|download|edit)$")


class CreateScheduleRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    report_config: dict[str, Any] = Field(..., min_length=1)
    schedule_cron: str = Field(..., min_length=1, max_length=200)
    export_format: str = Field(default="pdf", pattern="^(pdf|pptx|csv|bundle)$")
    recipients: list[str] | None = None
    enabled: bool = True


class ExecutiveSummaryRequest(BaseModel):
    analysis: dict[str, Any] = Field(..., min_length=1)
    result: dict[str, Any] = Field(..., min_length=1)


class SearchRequest(BaseModel):
    query: str | None = Field(default=None, max_length=500)
    data_type: str | None = None
    owner: str | None = None
    tags: list[str] | None = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class DownloadRequest(BaseModel):
    rows: list[dict[str, Any]]
    analysis: dict[str, Any] = Field(default_factory=dict)
    target_column: str | None = None
    ai_insights: str | None = None


class ExportRequest(BaseModel):
    rows: list[dict[str, Any]] = Field(..., min_length=1)
    filename: str = Field(default="export", max_length=100)


class QualityScoreRequest(BaseModel):
    rows: list[dict[str, Any]] = Field(..., min_length=1)


class QualityReportRequest(BaseModel):
    rows: list[dict[str, Any]] = Field(..., min_length=1)


class AutoMLRequest(BaseModel):
    rows: list[dict[str, Any]] = Field(..., min_length=1)
    target_column: str = Field(..., min_length=1)


class ExportResultsRequest(BaseModel):
    cleaned_data: list[dict[str, Any]] = Field(..., min_length=1)
    cleaning_stats: list[dict[str, Any]] | None = None
    ml_results: dict[str, Any] | None = None
