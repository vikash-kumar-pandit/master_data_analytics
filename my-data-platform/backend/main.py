import io
import os
import json
import zipfile
import base64

from fastapi import FastAPI, UploadFile, File, HTTPException, Body, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import polars as pl
from celery.result import AsyncResult
from fastapi.responses import StreamingResponse

from ml_engine import run_automl_stateless
from report_generator import generate_pdf_in_memory
from utils import analyze_dataframe, clean_dataframe, generate_cleaning_stats, read_csv_from_bytes
from worker import celery_app, async_clean_data, async_run_automl
from ai_engine import generate_business_insights
from pdf_generator import create_pdf_in_memory
from identifier import identify_dataset_semantics
from advanced_cleaner import advanced_data_arranging, advanced_data_cleaning
from ml_advanced import run_nocode_clustering, run_nocode_nlp
from security import sanitize_for_llm
from xai_engine import generate_shap_explanations
from auth import auth_router, require_role
from observability import setup_observability
from catalog import get_catalog_entry, is_catalog_entry_visible, list_catalog_entries_for_user, register_catalog_entry
from connectors import read_dataset_from_bytes
from workflows import create_workflow_definition, execute_workflow, get_workflow, list_workflows, save_workflow
from activity_tracker import build_activity_summary
from dashboard_summary import build_dashboard_summary, build_dashboard_trends
from analytics_engine import analyze_question, compare_versions, forecast_metric
from report_generator import generate_structured_report_pdf, generate_structured_report_pptx
from share_manager import create_share_link, get_share, increment_view_count, record_download, list_my_shares, revoke_share
from executive_summary import generate_executive_summary
from scheduled_exports import create_scheduled_export, get_schedule, list_schedules, update_schedule, record_run, delete_schedule

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


app = FastAPI(title="Stateless No-Code Big Data Platform")
app.include_router(auth_router, prefix="/api/auth")
setup_observability(app)


class InsightRequest(BaseModel):
    data_summary: dict


class ClusteringRequest(BaseModel):
    rows: list[dict]
    num_clusters: int = 3


class NLPRequest(BaseModel):
    rows: list[dict]
    text_column: str
    categories: list[str]


class ExplainRequest(BaseModel):
    rows: list[dict]
    target_column: str
    sample_index: int = 0
    top_k: int = 12

class CatalogQuery(BaseModel):
    limit: int = 20


class WorkflowCreateRequest(BaseModel):
    name: str
    description: str | None = None
    steps: list[str]
    target_column: str | None = None
    text_column: str | None = None
    categories: list[str] | None = None
    num_clusters: int = 3
    sample_index: int = 0
    top_k: int = 10


class WorkflowRunRequest(BaseModel):
    rows: list[dict]


class QuestionRequest(BaseModel):
    question: str
    rows: list[dict]
    previous_rows: list[dict] | None = None
    analysis: dict | None = None


class ForecastRequest(BaseModel):
    rows: list[dict]
    metric_column: str | None = None
    date_column: str | None = None
    horizon: int = 7


class CompareRequest(BaseModel):
    before_rows: list[dict]
    after_rows: list[dict]


class StructuredReportRequest(BaseModel):
    title: str
    subtitle: str
    sections: list[dict]
    output_format: str = "pdf"


class CreateShareRequest(BaseModel):
    report_title: str
    report_data: dict
    expires_days: int = 30
    access_level: str = "view"
    
    def validate_inputs(self):
        """Validate share request inputs."""
        if not self.report_title or not self.report_title.strip():
            raise ValueError("report_title cannot be empty")
        if not isinstance(self.report_data, dict) or not self.report_data:
            raise ValueError("report_data must be a non-empty dictionary")
        if self.expires_days < 1 or self.expires_days > 365:
            raise ValueError("expires_days must be between 1 and 365")
        if self.access_level not in ["view", "download", "edit"]:
            raise ValueError("access_level must be 'view', 'download', or 'edit'")


class CreateScheduleRequest(BaseModel):
    name: str
    description: str | None = None
    report_config: dict
    schedule_cron: str
    export_format: str = "pdf"
    recipients: list[str] | None = None
    enabled: bool = True
    
    def validate_inputs(self):
        """Validate schedule request inputs."""
        if not self.name or not self.name.strip():
            raise ValueError("name cannot be empty")
        if not self.schedule_cron or not self.schedule_cron.strip():
            raise ValueError("schedule_cron cannot be empty")
        if self.export_format not in ["pdf", "pptx", "csv", "bundle"]:
            raise ValueError("export_format must be 'pdf', 'pptx', 'csv', or 'bundle'")
        if self.recipients:
            for email in self.recipients:
                if not isinstance(email, str) or "@" not in email:
                    raise ValueError(f"Invalid email format: {email}")


class ExecutiveSummaryRequest(BaseModel):
    analysis: dict
    result: dict
    
    def validate_inputs(self):
        """Validate summary request inputs."""
        if not self.analysis:
            raise ValueError("analysis cannot be empty")
        if not self.result:
            raise ValueError("result cannot be empty")


def build_openai_client() -> OpenAI:
    if OpenAI is None:
        raise HTTPException(
            status_code=400,
            detail="OpenAI package is not installed. Run `pip install openai` to enable AI insights.",
        )

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="OPENAI_API_KEY is not set. Add it to your environment to generate AI insights.",
        )

    return OpenAI(api_key=api_key)


def build_fallback_insights(summary: dict) -> str:
    analysis = summary.get("analysis") or {}
    automl = summary.get("automl") or {}
    row_count = summary.get("row_count", analysis.get("rows", "unknown"))
    columns = summary.get("columns") or analysis.get("column_info") or []
    audit_count = summary.get("audit_count", len(analysis.get("audit_errors", [])))
    accuracy = automl.get("accuracy")

    if isinstance(accuracy, (int, float)):
        model_line = (
            f"Model insight: {automl.get('best_algorithm', 'Selected model')} reached "
            f"{accuracy * 100:.2f}% accuracy on current dataset."
        )
    else:
        model_line = "Model insight: AutoML summary is limited right now; validate target quality and class balance."

    return (
        "Business Insights (Fallback):\n"
        f"1. Dataset contains {row_count} rows across {len(columns)} columns.\n"
        f"2. Data quality review flagged approximately {audit_count} issue(s), so cleaning should be prioritized before decisions.\n"
        f"3. {model_line}\n"
        "Recommendations:\n"
        "1. Resolve null/duplicate records first, then retrain to improve reliability.\n"
        "2. Review high-impact columns and confirm they match business definitions.\n"
        "3. Track model performance over time and re-run quality checks after each upload."
    )


def build_question_fallback(question: str, rows: list[dict], previous_rows: list[dict] | None = None) -> dict:
    try:
        return analyze_question(question=question, rows=rows, previous_rows=previous_rows)
    except Exception as exc:
        return {
            "intent": "descriptive",
            "question": question,
            "answer": f"Unable to answer the question automatically: {exc}",
            "report_title": "Question Analysis Report",
            "report_subtitle": "Fallback response",
            "report_sections": [
                {"heading": "Question", "rows": [{"label": "Question", "value": question}]},
            ],
            "recommendations": ["Try rephrasing the question or upload a cleaner dataset."],
            "chart_data": [],
            "forecast": [],
            "comparison": None,
            "metrics": [],
            "top_breakdown": [],
            "error": str(exc),
        }

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
        if origin.strip()
    ],
    allow_origin_regex=os.getenv(
        "CORS_ORIGIN_REGEX",
        r"^https?://(localhost|127\.0\.0\.1):\d+$",
    ),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_role(["analyst", "admin"])),
):
    contents = await file.read()

    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        dataframe = read_dataset_from_bytes(contents, file.filename)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to parse dataset: {exc}") from exc

    analysis = analyze_dataframe(dataframe)
    semantics = identify_dataset_semantics(dataframe)
    analysis["domain_info"] = semantics

    register_catalog_entry(
        action="upload",
        dataset_name=file.filename,
        analysis=analysis,
        rows=dataframe.head(50).to_dicts(),
        source="file_upload",
        created_by=current_user,
    )

    return {
        "analysis": analysis,
        "grid_data": dataframe.to_dicts(),
        "sample_data": dataframe.head(10).to_dicts(),
        "catalog_preview": {
            "dataset_name": file.filename,
            "summary": {
                "rows": analysis.get("rows"),
                "cols": analysis.get("cols"),
                "domain": semantics.get("domain"),
            },
        },
    }


@app.post("/api/analytics/query")
async def analytics_query(
    payload: QuestionRequest,
    current_user: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    result = build_question_fallback(payload.question, payload.rows, payload.previous_rows)

    register_catalog_entry(
        action="question",
        dataset_name=None,
        analysis={
            "rows": len(payload.rows),
            "cols": len(payload.rows[0]) if payload.rows else 0,
            "question": payload.question,
            "intent": result.get("intent"),
        },
        rows=payload.rows[:50],
        source="question_answering",
        created_by=current_user,
    )

    return result


@app.post("/api/analytics/forecast")
async def analytics_forecast(
    payload: ForecastRequest,
    current_user: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    try:
        result = forecast_metric(
            rows=payload.rows,
            metric_column=payload.metric_column,
            date_column=payload.date_column,
            horizon=max(1, min(payload.horizon, 30)),
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Forecasting failed: {exc}") from exc

    register_catalog_entry(
        action="forecast",
        dataset_name=None,
        analysis={
            "rows": len(payload.rows),
            "cols": len(payload.rows[0]) if payload.rows else 0,
            "metric_column": payload.metric_column,
            "date_column": payload.date_column,
        },
        rows=payload.rows[:50],
        source="forecasting",
        created_by=current_user,
    )

    return result


@app.post("/api/analytics/compare")
async def analytics_compare(
    payload: CompareRequest,
    current_user: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    result = compare_versions(before_rows=payload.before_rows, after_rows=payload.after_rows)

    register_catalog_entry(
        action="compare",
        dataset_name=None,
        analysis={
            "rows": len(payload.after_rows),
            "cols": len(payload.after_rows[0]) if payload.after_rows else 0,
            "before_rows": len(payload.before_rows),
        },
        rows=payload.after_rows[:50],
        source="version_comparison",
        created_by=current_user,
    )

    return result


@app.post("/api/analytics/report")
async def analytics_report_pdf(
    payload: StructuredReportRequest,
    _: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    try:
        output_format = (payload.output_format or "pdf").strip().lower()
        if output_format == "pptx":
            file_bytes = generate_structured_report_pptx(
                title=payload.title,
                subtitle=payload.subtitle,
                sections=payload.sections,
            )
            media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            filename = "analytics_report.pptx"
        else:
            file_bytes = generate_structured_report_pdf(
                title=payload.title,
                subtitle=payload.subtitle,
                sections=payload.sections,
            )
            media_type = "application/pdf"
            filename = "analytics_report.pdf"

        buffer = io.BytesIO(file_bytes)
        return StreamingResponse(
            buffer,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(exc)}")


@app.post("/api/share/create")
async def create_share(
    payload: CreateShareRequest,
    current_user: dict = Depends(require_role(["analyst", "admin"])),
):
    try:
        payload.validate_inputs()
        
        share = create_share_link(
            report_title=payload.report_title,
            report_data=payload.report_data,
            created_by=current_user,
            expires_days=payload.expires_days,
            access_level=payload.access_level,
        )
        register_catalog_entry(
            action="share",
            dataset_name=payload.report_title,
            analysis={"access_level": payload.access_level},
            rows=[],
            source="report_sharing",
            created_by=current_user,
        )
        return share
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to create share: {str(exc)}")


@app.get("/api/share/my-shares")
async def list_my_shares_endpoint(
    current_user: dict = Depends(require_role(["analyst", "admin"])),
):
    try:
        username = current_user.get("username")
        if not username:
            raise HTTPException(status_code=400, detail="User must be authenticated")
        
        shares = list_my_shares(username, limit=20)
        return {
            "shares": [
                {
                    "token": s.get("token"),
                    "report_title": s.get("report_title"),
                    "created_at": s.get("created_at"),
                    "expires_at": s.get("expires_at"),
                    "view_count": s.get("view_count"),
                    "downloads_count": len(s.get("downloads", [])),
                }
                for s in shares
            ]
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to list shares: {str(exc)}")


@app.get("/api/share/{token}")
async def view_share(token: str):
    try:
        if not token or not token.strip():
            raise HTTPException(status_code=400, detail="token cannot be empty")
        
        share = get_share(token)
        if not share:
            raise HTTPException(status_code=404, detail="Share not found or has expired.")
        
        increment_view_count(token)
        return {
            "report_title": share.get("report_title"),
            "report_data": share.get("report_data"),
            "created_at": share.get("created_at"),
            "access_level": share.get("access_level"),
            "view_count": share.get("view_count"),
        }
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve share: {str(exc)}")


@app.post("/api/share/{token}/download")
async def download_share(token: str, format: str = "pdf"):
    try:
        if not token or not token.strip():
            raise HTTPException(status_code=400, detail="token cannot be empty")
        if not format or not format.strip():
            format = "pdf"
        
        format = format.lower()
        if format not in ["pdf", "pptx"]:
            raise HTTPException(status_code=400, detail="format must be 'pdf' or 'pptx'")
        
        share = get_share(token)
        if not share:
            raise HTTPException(status_code=404, detail="Share not found or has expired.")
        
        if share.get("access_level") not in ["download", "edit"]:
            raise HTTPException(status_code=403, detail="Download not allowed for this share.")
        
        record_download(token, format)
        report_data = share.get("report_data") or {}
        
        if format == "pptx":
            file_bytes = generate_structured_report_pptx(
                title=report_data.get("title", "Report"),
                subtitle=report_data.get("subtitle", ""),
                sections=report_data.get("sections", []),
            )
            media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            filename = "shared_report.pptx"
        else:
            file_bytes = generate_structured_report_pdf(
                title=report_data.get("title", "Report"),
                subtitle=report_data.get("subtitle", ""),
                sections=report_data.get("sections", []),
            )
            media_type = "application/pdf"
            filename = "shared_report.pdf"
        
        buffer = io.BytesIO(file_bytes)
        return StreamingResponse(
            buffer,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(exc)}")


@app.delete("/api/share/{token}")
async def revoke_share_endpoint(
    token: str,
    current_user: dict = Depends(require_role(["analyst", "admin"])),
):
    try:
        if not token or not token.strip():
            raise HTTPException(status_code=400, detail="token cannot be empty")
        
        username = current_user.get("username")
        success = revoke_share(token, username)
        if not success:
            raise HTTPException(status_code=403, detail="Not authorized to revoke this share.")
        return {"status": "revoked"}
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to revoke share: {str(exc)}")


@app.post("/api/summary/executive")
async def generate_summary(
    payload: ExecutiveSummaryRequest,
    current_user: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    try:
        payload.validate_inputs()
        
        summary = generate_executive_summary(analysis=payload.analysis, result=payload.result)
        return summary
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(exc)}")


@app.post("/api/schedule/create")
async def create_schedule(
    payload: CreateScheduleRequest,
    current_user: dict = Depends(require_role(["analyst", "admin"])),
):
    try:
        payload.validate_inputs()
        
        schedule = create_scheduled_export(
            name=payload.name,
            description=payload.description,
            report_config=payload.report_config,
            schedule_cron=payload.schedule_cron,
            export_format=payload.export_format,
            recipients=payload.recipients,
            enabled=payload.enabled,
            created_by=current_user,
        )
        register_catalog_entry(
            action="schedule",
            dataset_name=payload.name,
            analysis={"cron": payload.schedule_cron, "format": payload.export_format},
            rows=[],
            source="scheduled_export",
            created_by=current_user,
        )
        return schedule
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to create schedule: {str(exc)}")


@app.get("/api/schedule/my-schedules")
async def list_my_schedules(
    current_user: dict = Depends(require_role(["analyst", "admin"])),
):
    try:
        username = current_user.get("username")
        if not username:
            raise HTTPException(status_code=400, detail="User must be authenticated")
        
        schedules = list_schedules(username, limit=20)
        return {
            "schedules": [
                {
                    "id": s.get("id"),
                    "name": s.get("name"),
                    "schedule_cron": s.get("schedule_cron"),
                    "export_format": s.get("export_format"),
                    "enabled": s.get("enabled"),
                    "last_run": s.get("last_run"),
                    "next_run": s.get("next_run"),
                    "run_count": s.get("run_count"),
                    "last_status": s.get("last_status"),
                }
                for s in schedules
            ]
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to list schedules: {str(exc)}")


@app.get("/api/schedule/{schedule_id}")
async def get_schedule_endpoint(
    schedule_id: str,
    current_user: dict = Depends(require_role(["analyst", "admin"])),
):
    try:
        if not schedule_id or not schedule_id.strip():
            raise HTTPException(status_code=400, detail="schedule_id cannot be empty")
        
        schedule = get_schedule(schedule_id)
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found.")
        if schedule.get("created_by") != current_user.get("username"):
            raise HTTPException(status_code=403, detail="Not authorized to view this schedule.")
        return schedule
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to get schedule: {str(exc)}")


@app.delete("/api/schedule/{schedule_id}")
async def delete_schedule_endpoint(
    schedule_id: str,
    current_user: dict = Depends(require_role(["analyst", "admin"])),
):
    try:
        if not schedule_id or not schedule_id.strip():
            raise HTTPException(status_code=400, detail="schedule_id cannot be empty")
        
        username = current_user.get("username")
        success = delete_schedule(schedule_id, username)
        if not success:
            raise HTTPException(status_code=403, detail="Not authorized to delete this schedule.")
        return {"status": "deleted"}
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to delete schedule: {str(exc)}")


@app.post("/clean")
async def clean_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_role(["analyst", "admin"])),
):
    contents = await file.read()

    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        dataframe = read_dataset_from_bytes(contents, file.filename)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to parse dataset: {exc}") from exc

    cleaned_dataframe = advanced_data_cleaning(dataframe)
    analysis = analyze_dataframe(cleaned_dataframe)
    semantics = identify_dataset_semantics(cleaned_dataframe)
    analysis["domain_info"] = semantics
    cleaning_stats = generate_cleaning_stats(dataframe, cleaned_dataframe)

    register_catalog_entry(
        action="clean",
        dataset_name=file.filename,
        analysis=analysis,
        cleaning_stats=cleaning_stats,
        rows=cleaned_dataframe.head(50).to_dicts(),
        source="file_upload",
        created_by=current_user,
    )

    return {
        "analysis": analysis,
        "cleaning_stats": cleaning_stats,
        "grid_data": cleaned_dataframe.to_dicts(),
        "sample_data": cleaned_dataframe.head(10).to_dicts(),
        "cleaned_data": cleaned_dataframe.to_dicts(),
        "catalog_preview": {
            "dataset_name": file.filename,
            "summary": {
                "rows": analysis.get("rows"),
                "cols": analysis.get("cols"),
                "domain": semantics.get("domain"),
            },
        },
    }


@app.post("/arrange")
async def arrange_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_role(["analyst", "admin"])),
):
    contents = await file.read()

    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        dataframe = read_dataset_from_bytes(contents, file.filename)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to parse dataset: {exc}") from exc

    arranged_dataframe, arranging_notes = advanced_data_arranging(dataframe)
    analysis = analyze_dataframe(arranged_dataframe)
    semantics = identify_dataset_semantics(arranged_dataframe)
    analysis["domain_info"] = semantics
    cleaning_stats = generate_cleaning_stats(dataframe, arranged_dataframe)

    register_catalog_entry(
        action="arrange",
        dataset_name=file.filename,
        analysis=analysis,
        cleaning_stats=cleaning_stats,
        rows=arranged_dataframe.head(50).to_dicts(),
        source="file_upload",
        created_by=current_user,
    )

    return {
        "analysis": analysis,
        "arranging_notes": arranging_notes,
        "cleaning_stats": cleaning_stats,
        "grid_data": arranged_dataframe.to_dicts(),
        "sample_data": arranged_dataframe.head(10).to_dicts(),
        "arranged_data": arranged_dataframe.to_dicts(),
        "catalog_preview": {
            "dataset_name": file.filename,
            "summary": {
                "rows": analysis.get("rows"),
                "cols": analysis.get("cols"),
                "domain": semantics.get("domain"),
            },
        },
    }


@app.post("/download")
async def download_results(
    payload: dict = Body(...),
    _: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    rows = payload.get("rows", [])
    analysis = payload.get("analysis", {})
    target_column = payload.get("target_column")
    ai_insights = payload.get("ai_insights")

    dataframe = pl.from_dicts(rows)
    zip_buffer = io.BytesIO()
    report_summary = dict(analysis)

    automl_summary = None
    if target_column:
        try:
            automl_summary = run_automl_stateless(dataframe, target_column)
        except Exception as exc:
            automl_summary = {"error": str(exc)}

    if automl_summary:
        report_summary["automl"] = automl_summary

    if ai_insights:
        report_summary["ai_insights"] = ai_insights

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("cleaned_data.csv", dataframe.write_csv())
        zip_file.writestr("analysis_report.json", json.dumps(report_summary, indent=2, default=str))
        zip_file.writestr("analysis_report.pdf", generate_pdf_in_memory(dataframe, report_summary))

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=analysis_results.zip"},
    )


@app.get("/api/catalog")
async def get_catalog(
    limit: int = 20,
    current_user: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    return {"items": list_catalog_entries_for_user(current_user, limit=max(1, min(limit, 100)))}


@app.get("/api/catalog/{entry_id}")
async def get_catalog_detail(
    entry_id: str,
    current_user: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    entry = get_catalog_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Catalog entry not found")
    if not is_catalog_entry_visible(entry, current_user):
        raise HTTPException(status_code=404, detail="Catalog entry not found")
    return entry


@app.get("/api/activity/summary")
async def get_activity_summary(
    days: int = 30,
    recent_limit: int = 20,
    current_user: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    return build_activity_summary(
        current_user=current_user,
        days=max(1, min(days, 365)),
        recent_limit=max(5, min(recent_limit, 100)),
    )


@app.get("/api/dashboard/summary")
async def get_dashboard_summary(
    days: int = 30,
    recent_limit: int = 12,
    catalog_limit: int = 20,
    current_user: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    return build_dashboard_summary(
        current_user=current_user,
        days=days,
        recent_limit=recent_limit,
        catalog_limit=catalog_limit,
    )


@app.get("/api/dashboard/trends")
async def get_dashboard_trends(
    window_days: int = 7,
    current_user: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    return build_dashboard_trends(
        current_user=current_user,
        window_days=window_days,
    )


@app.post("/api/export/excel")
async def export_to_excel(
    payload: dict = Body(...),
    _: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    """Export data to Excel format with formatting."""
    try:
        rows = payload.get("rows", [])
        filename = payload.get("filename", "export") or "export"
        filename = filename.replace(" ", "_")[:50]  # sanitize filename
        
        if not rows:
            raise HTTPException(status_code=400, detail="No data to export")
        
        dataframe = pl.from_dicts(rows)
        excel_buffer = io.BytesIO()
        
        # Use Polars' Excel writer via pyarrow
        dataframe.write_excel(excel_buffer)
        excel_buffer.seek(0)
        
        return StreamingResponse(
            excel_buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}.xlsx"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@app.post("/api/export/parquet")
async def export_to_parquet(
    payload: dict = Body(...),
    _: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    """Export data to Parquet format for efficient storage."""
    try:
        rows = payload.get("rows", [])
        filename = payload.get("filename", "export") or "export"
        filename = filename.replace(" ", "_")[:50]  # sanitize filename
        
        if not rows:
            raise HTTPException(status_code=400, detail="No data to export")
        
        dataframe = pl.from_dicts(rows)
        parquet_buffer = io.BytesIO()
        
        # Write to Parquet format
        dataframe.write_parquet(parquet_buffer)
        parquet_buffer.seek(0)
        
        return StreamingResponse(
            parquet_buffer,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={filename}.parquet"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@app.post("/api/export/json")
async def export_to_json(
    payload: dict = Body(...),
    _: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    """Export data to JSON format."""
    try:
        rows = payload.get("rows", [])
        filename = payload.get("filename", "export") or "export"
        filename = filename.replace(" ", "_")[:50]  # sanitize filename
        
        if not rows:
            raise HTTPException(status_code=400, detail="No data to export")
        
        json_buffer = io.BytesIO()
        json_buffer.write(json.dumps(rows, indent=2, default=str).encode())
        json_buffer.seek(0)
        
        return StreamingResponse(
            json_buffer,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}.json"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


class SearchRequest(BaseModel):
    query: str | None = None
    data_type: str | None = None  # "dataset", "report", "workflow"
    owner: str | None = None
    tags: list[str] | None = None
    limit: int = 20
    offset: int = 0


@app.post("/api/search/catalog")
async def search_catalog(
    search_req: SearchRequest,
    current_user: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    """Advanced search across catalog with filtering."""
    try:
        limit = max(1, min(search_req.limit, 100))
        offset = max(0, search_req.offset)
        
        all_entries = list_catalog_entries_for_user(current_user, limit=1000)
        
        # Filter by query (case-insensitive search in name/description)
        if search_req.query:
            query_lower = search_req.query.lower()
            all_entries = [
                e for e in all_entries
                if query_lower in (e.get("name", "") or "").lower()
                or query_lower in (e.get("description", "") or "").lower()
            ]
        
        # Filter by data_type
        if search_req.data_type:
            all_entries = [e for e in all_entries if e.get("type") == search_req.data_type]
        
        # Filter by owner
        if search_req.owner:
            all_entries = [e for e in all_entries if e.get("owner") == search_req.owner]
        
        # Filter by tags (match any tag)
        if search_req.tags:
            all_entries = [
                e for e in all_entries
                if any(tag in (e.get("tags", []) or []) for tag in search_req.tags)
            ]
        
        # Pagination
        total_count = len(all_entries)
        paginated = all_entries[offset : offset + limit]
        
        return {
            "items": paginated,
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total_count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/api/workflows")
async def get_workflows(_: dict = Depends(require_role(["viewer", "analyst", "admin"]))):
    return {"items": list_workflows()}


@app.post("/api/workflows")
async def create_workflow(
    payload: WorkflowCreateRequest,
    _: dict = Depends(require_role(["analyst", "admin"])),
):
    workflow = create_workflow_definition(payload.model_dump())
    save_workflow(workflow)
    return {"workflow": workflow}


@app.get("/api/workflows/{workflow_id}")
async def get_workflow_detail(
    workflow_id: str,
    _: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    workflow = get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@app.post("/api/workflows/{workflow_id}/run")
async def run_saved_workflow(
    workflow_id: str,
    payload: WorkflowRunRequest,
    current_user: dict = Depends(require_role(["analyst", "admin"])),
):
    workflow = get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    try:
        result = execute_workflow(workflow, payload.rows, actor=current_user)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Workflow execution failed: {exc}") from exc

    return result


@app.post("/api/export-results")
async def export_results(
    payload: dict = Body(...),
    _: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    raw_data = payload.get("cleaned_data") or []
    cleaning_stats = payload.get("cleaning_stats")
    ml_results = payload.get("ml_results")

    if not raw_data:
        raise HTTPException(status_code=400, detail="No data provided")

    dataframe = pl.from_dicts(raw_data)

    ai_summary = generate_business_insights(cleaning_stats, ml_results)
    pdf_bytes = create_pdf_in_memory(ai_summary, dataframe)
    csv_string = dataframe.write_csv()

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("cleaned_data.csv", csv_string)
        zip_file.writestr("AI_Analysis_Report.pdf", pdf_bytes)
        zip_file.writestr(
            "analysis_payload.json",
            json.dumps(
                {
                    "cleaning_stats": cleaning_stats,
                    "ml_results": ml_results,
                    "ai_summary": ai_summary,
                    "pii_sanitized": True,
                },
                indent=2,
                default=str,
            ),
        )

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=Analysis_Export.zip"},
    )


@app.post("/automl")
async def run_automl(
    payload: dict = Body(...),
    current_user: dict = Depends(require_role(["analyst", "admin"])),
):
    rows = payload.get("rows", [])
    target_column = payload.get("target_column")

    if not rows:
        raise HTTPException(status_code=400, detail="No rows available for AutoML")
    if not target_column:
        raise HTTPException(status_code=400, detail="Target column is required")

    dataframe = pl.from_dicts(rows)

    try:
        result = run_automl_stateless(dataframe, target_column)
    except ImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"AutoML failed: {exc}") from exc

    register_catalog_entry(
        action="automl",
        dataset_name=None,
        ml_results=result,
        rows=dataframe.head(50).to_dicts(),
        target_column=target_column,
        source="manual_prediction",
        created_by=current_user,
    )

    return result


@app.post("/generate-insights")
async def generate_insights(
    payload: InsightRequest,
    _: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    safe_summary = sanitize_for_llm(payload.data_summary)

    prompt = (
        "You are an expert data analyst. Review the dataset summary and provide 3 concise business insights "
        "and 3 practical recommendations in simple language. Focus on data quality issues, model implications, "
        "and business impact. Return plain text only. Dataset summary: "
        f"{safe_summary}"
    )

    try:
        client = build_openai_client()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You write clear, practical business analysis for non-technical users."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )
        return {
            "insights": response.choices[0].message.content or "",
            "pii_sanitized": True,
            "source": "openai",
        }
    except HTTPException as exc:
        fallback = build_fallback_insights(safe_summary if isinstance(safe_summary, dict) else {})
        return {
            "insights": fallback,
            "pii_sanitized": True,
            "source": "fallback",
            "note": str(exc.detail),
        }
    except Exception as exc:
        fallback = build_fallback_insights(safe_summary if isinstance(safe_summary, dict) else {})
        return {
            "insights": fallback,
            "pii_sanitized": True,
            "source": "fallback",
            "note": f"OpenAI unavailable: {exc}",
        }


@app.post("/api/clean-background")
async def clean_data_background(
    file: UploadFile = File(...),
    _: dict = Depends(require_role(["analyst", "admin"])),
):
    contents = await file.read()

    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    file_b64 = base64.b64encode(contents).decode("utf-8")
    try:
        task = async_clean_data.delay(file_b64)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Background worker is unavailable. Ensure Redis and Celery worker are running, "
                "or use synchronous /clean endpoint for now."
            ),
        ) from exc
    return {"task_id": task.id, "message": "Data cleaning started in background."}


@app.post("/api/predict-background")
async def predict_background(
    target_column: str = Form(...),
    file: UploadFile = File(...),
    _: dict = Depends(require_role(["analyst", "admin"])),
):
    contents = await file.read()

    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    file_b64 = base64.b64encode(contents).decode("utf-8")
    try:
        task = async_run_automl.delay(file_b64, target_column)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Background worker is unavailable. Ensure Redis and Celery worker are running, "
                "or use synchronous /automl endpoint for now."
            ),
        ) from exc
    return {"task_id": task.id, "message": "AutoML started in background."}


@app.get("/api/task-status/{task_id}")
def get_task_status(
    task_id: str,
    _: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    task_result = AsyncResult(task_id, app=celery_app)

    if task_result.state == "PENDING":
        return {"state": task_result.state, "status": "Waiting in queue..."}

    if task_result.state in {"STARTED", "PROGRESS"}:
        info = task_result.info or {}
        return {
            "state": task_result.state,
            "status": info.get("status", "Processing..."),
            "progress": info.get("progress", None),
        }

    if task_result.state == "SUCCESS":
        return {"state": task_result.state, "result": task_result.result}

    if task_result.state == "REVOKED":
        return {"state": task_result.state, "status": "Task was cancelled by user."}

    return {
        "state": task_result.state,
        "status": str(task_result.info),
    }


@app.post("/api/revoke-task/{task_id}")
def revoke_task(
    task_id: str,
    _: dict = Depends(require_role(["analyst", "admin"])),
):
    celery_app.control.revoke(task_id, terminate=True, signal="SIGTERM")
    return {"message": f"Task {task_id} has been cancelled."}


@app.post("/api/run-clustering")
async def apply_clustering(
    payload: ClusteringRequest,
    current_user: dict = Depends(require_role(["analyst", "admin"])),
):
    if not payload.rows:
        raise HTTPException(status_code=400, detail="No data provided")
    if payload.num_clusters < 2:
        raise HTTPException(status_code=400, detail="num_clusters must be at least 2")

    dataframe = pl.from_dicts(payload.rows)

    try:
        clustered = run_nocode_clustering(dataframe, num_clusters=payload.num_clusters)
    except ImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Clustering failed: {exc}") from exc

    register_catalog_entry(
        action="clustering",
        dataset_name=None,
        rows=payload.rows[:50],
        source="manual_prediction",
        created_by=current_user,
    )

    return {
        "message": "Clustering applied",
        "columns": clustered.columns,
        "data": clustered.head(200).to_dicts(),
    }


@app.post("/api/apply-nlp")
async def apply_nlp_to_data(
    payload: NLPRequest,
    current_user: dict = Depends(require_role(["analyst", "admin"])),
):
    if not payload.rows:
        raise HTTPException(status_code=400, detail="No data provided")

    categories = [value.strip() for value in payload.categories if value.strip()]
    if not categories:
        raise HTTPException(status_code=400, detail="At least one valid category is required")

    dataframe = pl.from_dicts(payload.rows)

    try:
        categorized = run_nocode_nlp(dataframe, payload.text_column, categories)
    except (ImportError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"NLP processing failed: {exc}") from exc

    register_catalog_entry(
        action="nlp",
        dataset_name=None,
        rows=payload.rows[:50],
        source="manual_prediction",
        target_column=payload.text_column,
        created_by=current_user,
    )

    return {
        "message": "NLP Applied",
        "columns": categorized.columns,
        "data": categorized.head(200).to_dicts(),
    }


@app.post("/api/explain-automl")
async def explain_automl(
    payload: ExplainRequest,
    current_user: dict = Depends(require_role(["analyst", "admin"])),
):
    if not payload.rows:
        raise HTTPException(status_code=400, detail="No data provided")
    if not payload.target_column:
        raise HTTPException(status_code=400, detail="target_column is required")
    if payload.top_k < 1:
        raise HTTPException(status_code=400, detail="top_k must be at least 1")

    try:
        explanation = generate_shap_explanations(
            rows=payload.rows,
            target_column=payload.target_column,
            sample_index=payload.sample_index,
            top_k=payload.top_k,
        )
    except (ValueError, ImportError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Explainability failed: {exc}") from exc

    register_catalog_entry(
        action="explainability",
        dataset_name=None,
        rows=payload.rows[:50],
        target_column=payload.target_column,
        ml_results=explanation,
        source="manual_prediction",
        created_by=current_user,
    )

    return explanation


@app.get("/api/admin-stats")
async def admin_stats(_: dict = Depends(require_role(["admin"]))):
    return {
        "status": "ok",
        "message": "Welcome Admin",
        "capabilities": ["user_management", "system_configuration", "audit_access"],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)