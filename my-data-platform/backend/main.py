import io
import os
# Add GTK+ DLL directory for WeasyPrint on Windows
if os.name == 'nt':
    for sd in [
        r"C:\Program Files\GTK3-Runtime Win64\bin",
        r"C:\Program Files\GTK3-Runtime\bin",
        r"C:\Program Files (x86)\GTK3-Runtime Win64\bin",
        r"C:\Program Files (x86)\GTK3-Runtime\bin",
    ]:
        if os.path.exists(sd):
            try:
                os.add_dll_directory(sd)
                break
            except Exception:
                pass

import json
import logging
import dotenv
dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
import zipfile
import base64
from datetime import datetime, timezone
from typing import Any
import asyncio

from fastapi import FastAPI, UploadFile, File, HTTPException, Body, Form, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import polars as pl
from celery.result import AsyncResult

from ml_engine import run_automl_stateless
from report_generator import generate_pdf_in_memory
from utils import analyze_dataframe, generate_cleaning_stats
from worker import celery_app, async_clean_data, async_run_automl
from ai_engine import generate_business_insights
from pdf_generator import create_pdf_in_memory
from identifier import identify_dataset_semantics
from advanced_cleaner import advanced_data_arranging, advanced_data_cleaning
from ml_advanced import run_nocode_clustering, run_nocode_nlp
from security import sanitize_for_llm
from xai_engine import generate_shap_explanations
from auth import auth_router, require_role
import auth as auth_module
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
from scheduled_exports import create_scheduled_export, get_schedule, list_schedules, delete_schedule
from data_quality import calculate_data_quality_metrics, get_quality_report
from feature_engineer import auto_feature_engineer

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# Initialize Sentry if configured
try:
    import sentry_sdk
    SENTRY_DSN = os.getenv('SENTRY_DSN') or os.getenv('SENTRY_DSN_URL')
    if SENTRY_DSN:
        sentry_sdk.init(dsn=SENTRY_DSN, traces_sample_rate=float(os.getenv('SENTRY_TRACES', 0.1)))
except Exception:
    # If sentry not installed or init fails, continue without crashing
    pass


from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app_context: FastAPI):
    """Spawn a daemon thread that runs audit log cleanup once per day.

    Controlled via `AUDIT_LOG_RETENTION_DAYS` (days to keep, default 90) and
    `AUDIT_LOG_CLEANUP_INTERVAL_SECONDS` (interval between runs, default 86400).
    """
    import threading
    import time
    import logging

    retention = int(os.getenv("AUDIT_LOG_RETENTION_DAYS", "90"))
    interval = int(os.getenv("AUDIT_LOG_CLEANUP_INTERVAL_SECONDS", str(24 * 60 * 60)))

    def _cleanup_loop():
        logger = logging.getLogger("audit")
        logger.info("Starting audit cleanup thread: retention=%s days interval=%s seconds", retention, interval)
        try:
            while True:
                try:
                    deleted = auth_module.db.cleanup_old_audit_logs(auth_module.DB_PATH, retention)
                    logger.info("Scheduled audit cleanup removed %d rows older than %d days", deleted, retention)
                except Exception as exc:
                    logger.exception("Scheduled audit cleanup failed: %s", exc)
                time.sleep(interval)
        except Exception as exc:
            logger.exception("Audit cleanup thread terminated unexpectedly: %s", exc)

    thread = threading.Thread(target=_cleanup_loop, name="audit-cleanup", daemon=True)
    thread.start()
    yield


app = FastAPI(title="Stateless No-Code Big Data Platform", lifespan=lifespan)
app.include_router(auth_router, prefix="/api/auth")
from pipeline_routes import router as pipeline_router
app.include_router(pipeline_router)
from profiling.routes import router as profiling_router
app.include_router(profiling_router)
from preparation.routes import router as preparation_router
app.include_router(preparation_router)
from copilot.routes import router as copilot_router
app.include_router(copilot_router)
from visualization.routes import router as visualization_router
app.include_router(visualization_router)
setup_observability(app)

from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import JSONResponse

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    logger.error(f"HTTP exception: {exc.detail} (status code: {exc.status_code})")
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "detail": exc.detail}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logger.error(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"status": "error", "detail": "Invalid request fields", "errors": exc.errors()}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.exception(f"Unhandled server exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"status": "error", "detail": "An unexpected error occurred. Please contact the administrator."}
    )


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send welcome event immediately on connect
        await websocket.send_json({
            "type": "system:connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "message": "Real-time monitor connected",
                "active_connections": len(manager.active_connections),
            }
        })

        # Seed with recent activity from DB (last 10 events)
        try:
            from database import SessionLocal
            from models import UserActivity
            with SessionLocal() as db:
                recent = db.query(UserActivity).order_by(
                    UserActivity.timestamp.desc()
                ).limit(10).all()
            for act in reversed(recent):
                await websocket.send_json({
                    "type": "activity:history",
                    "timestamp": act.timestamp.isoformat() if act.timestamp else datetime.now(timezone.utc).isoformat(),
                    "payload": {
                        "action": act.action,
                        "username": act.username,
                        "resource": act.resource,
                        "status": act.metadata_info.get("status_code", 200) if act.metadata_info else 200,
                        "duration_ms": act.metadata_info.get("duration_ms", 0) if act.metadata_info else 0,
                    }
                })
        except Exception as seed_exc:
            logger.warning(f"Could not seed activity on WS connect: {seed_exc}")

        # Heartbeat loop — ping every 10 seconds
        tick = 0
        while True:
            await asyncio.sleep(10)
            tick += 1
            await websocket.send_json({
                "type": "system:heartbeat",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {
                    "tick": tick,
                    "active_connections": len(manager.active_connections),
                }
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

async def broadcast_event(event: dict):
    await manager.broadcast(event)



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
    sections: list[Any]
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

    catalog_entry = register_catalog_entry(
        action="upload",
        dataset_name=file.filename,
        analysis=analysis,
        rows=dataframe.head(50).to_dicts(),
        source="file_upload",
        created_by=current_user,
    )

    await broadcast_event({
        "type": "catalog:activity",
        "payload": {
            "action": "upload",
            "dataset_name": file.filename,
            "rows": analysis.get("rows"),
            "cols": analysis.get("cols"),
            "catalog_id": catalog_entry.get("id") if isinstance(catalog_entry, dict) else None,
        },
    })

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
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Validate payload
        if not payload:
            raise ValueError("Request payload is missing")
        
        # Validate question
        question = str(payload.question or "").strip()
        if not question:
            raise ValueError("Question cannot be empty")
        
        # Validate rows
        if not isinstance(payload.rows, list):
            raise ValueError("rows must be a list")
        
        if not payload.rows:
            raise ValueError("No data provided")
        
        # Validate row structure
        for i, row in enumerate(payload.rows):
            if not isinstance(row, dict):
                raise ValueError(f"Row {i} is not a dictionary")
        
        # Validate previous_rows if provided
        if payload.previous_rows is not None and not isinstance(payload.previous_rows, list):
            raise ValueError("previous_rows must be a list or None")
        
        result = build_question_fallback(question, payload.rows, payload.previous_rows)
        
        if not result:
            raise ValueError("Failed to generate analysis result")

        try:
            register_catalog_entry(
                action="question",
                dataset_name=None,
                analysis={
                    "rows": len(payload.rows),
                    "cols": len(payload.rows[0]) if payload.rows else 0,
                    "question": question,
                    "intent": result.get("intent"),
                },
                rows=payload.rows[:50],
                source="question_answering",
                created_by=current_user,
            )
        except Exception as reg_exc:
            logger.warning(f"Failed to register catalog entry: {reg_exc}")
            # Continue anyway, catalog registration is non-critical

        return result
    
    except ValueError as ve:
        logger.error(f"Validation error in analytics_query: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        logger.exception(f"Error in analytics_query: {exc}")
        # Return fallback result
        return {
            "intent": "descriptive",
            "question": str(payload.question or "Unknown"),
            "answer": f"Analysis failed: {str(exc)[:100]}",
            "report_title": "Analysis Failed",
            "report_sections": [],
            "recommendations": ["Please check your data format and try again."],
            "chart_data": [],
            "error": str(exc),
        }


@app.post("/api/analytics/forecast")
async def analytics_forecast(
    payload: ForecastRequest,
    current_user: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Validate payload
        if not payload:
            raise ValueError("Request payload is missing")
        
        # Validate rows
        if not isinstance(payload.rows, list):
            raise ValueError("rows must be a list")
        
        if not payload.rows:
            raise ValueError("No data provided for forecasting")
        
        # Validate horizon
        horizon = payload.horizon or 7
        if not isinstance(horizon, int) or horizon < 1:
            horizon = 7
        horizon = max(1, min(horizon, 30))  # Limit to 1-30 range
        
        try:
            result = forecast_metric(
                rows=payload.rows,
                metric_column=payload.metric_column,
                date_column=payload.date_column,
                horizon=horizon,
            )
        except Exception as forecast_exc:
            logger.exception(f"Forecasting failed: {forecast_exc}")
            raise HTTPException(status_code=400, detail=f"Forecasting failed: {str(forecast_exc)[:200]}") from forecast_exc

        try:
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
        except Exception as reg_exc:
            logger.warning(f"Failed to register catalog entry for forecast: {reg_exc}")
            # Continue anyway, catalog registration is non-critical

        return result
    
    except ValueError as ve:
        logger.error(f"Validation error in forecast: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"Unexpected error in analytics_forecast: {exc}")
        raise HTTPException(status_code=500, detail=f"Forecasting failed: {str(exc)[:200]}")


@app.post("/api/analytics/compare")
async def analytics_compare(
    payload: CompareRequest,
    current_user: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Validate payload
        if not payload:
            raise ValueError("Request payload is missing")
        
        # Validate before_rows
        if not isinstance(payload.before_rows, list):
            raise ValueError("before_rows must be a list")
        
        if not payload.before_rows:
            raise ValueError("before_rows cannot be empty")
        
        # Validate after_rows
        if not isinstance(payload.after_rows, list):
            raise ValueError("after_rows must be a list")
        
        if not payload.after_rows:
            raise ValueError("after_rows cannot be empty")
        
        try:
            result = compare_versions(before_rows=payload.before_rows, after_rows=payload.after_rows)
        except Exception as compare_exc:
            logger.exception(f"Comparison failed: {compare_exc}")
            raise HTTPException(status_code=400, detail=f"Comparison failed: {str(compare_exc)[:200]}") from compare_exc

        try:
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
        except Exception as reg_exc:
            logger.warning(f"Failed to register catalog entry for comparison: {reg_exc}")
            # Continue anyway, catalog registration is non-critical

        return result
    
    except ValueError as ve:
        logger.error(f"Validation error in compare: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"Unexpected error in analytics_compare: {exc}")
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(exc)[:200]}")


@app.post("/api/analytics/report")
async def analytics_report_pdf(
    payload: StructuredReportRequest,
    _: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Validate payload
        if not payload:
            raise ValueError("Request payload is missing")
        
        # Validate title and subtitle
        title = str(payload.title or "Report").strip()
        if not title:
            title = "Analytics Report"
        
        subtitle = str(payload.subtitle or "").strip()
        
        # Validate sections
        if payload.sections is None:
            sections = []
        elif isinstance(payload.sections, list):
            sections = payload.sections
        else:
            raise ValueError("sections must be a list")
        
        # Validate section format
        validated_sections = []
        for i, section in enumerate(sections):
            if not isinstance(section, dict):
                logger.warning(f"Section {i} is not a dict, skipping")
                continue
            validated_sections.append(section)
        
        # Validate output format
        output_format = (payload.output_format or "pdf").strip().lower()
        if output_format not in ["pdf", "pptx"]:
            output_format = "pdf"
        
        try:
            if output_format == "pptx":
                file_bytes = generate_structured_report_pptx(
                    title=title,
                    subtitle=subtitle,
                    sections=validated_sections,
                )
                media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                filename = "analytics_report.pptx"
            else:
                file_bytes = generate_structured_report_pdf(
                    title=title,
                    subtitle=subtitle,
                    sections=validated_sections,
                )
                media_type = "application/pdf"
                filename = "analytics_report.pdf"
            
            if not file_bytes:
                raise ValueError("Report generation returned empty content")
            
            buffer = io.BytesIO(file_bytes)
            return StreamingResponse(
                buffer,
                media_type=media_type,
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
        except ValueError as ve:
            logger.error(f"Validation error in report generation: {ve}")
            raise HTTPException(status_code=400, detail=f"Invalid report data: {str(ve)}")
        except Exception as inner_exc:
            logger.exception(f"Error generating report: {inner_exc}")
            raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(inner_exc)[:200]}")
    
    except HTTPException:
        raise
    except ValueError as ve:
        logger.error(f"Input validation error: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        logger.exception(f"Unexpected error in analytics_report_pdf: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(exc)[:200]}")




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
    cleaned_dataframe, engineering_notes = auto_feature_engineer(cleaned_dataframe)
    analysis = analyze_dataframe(cleaned_dataframe)
    semantics = identify_dataset_semantics(cleaned_dataframe)
    analysis["domain_info"] = semantics
    cleaning_stats = generate_cleaning_stats(dataframe, cleaned_dataframe)
    if engineering_notes:
        if not cleaning_stats:
            cleaning_stats = {}
        cleaning_stats["engineering_notes"] = engineering_notes

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
        if isinstance(automl_summary, dict) and "target_column" not in automl_summary:
            automl_summary["target_column"] = target_column
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
    try:
        return {"items": list_catalog_entries_for_user(current_user, limit=max(1, min(limit, 100)))}
    except Exception as exc:
        logger.exception("Failed to list catalog entries: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve dataset catalog. Please try again later."
        )


@app.get("/api/catalog/{entry_id}")
async def get_catalog_detail(
    entry_id: str,
    current_user: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    try:
        entry = get_catalog_entry(entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Catalog entry not found")
        if not is_catalog_entry_visible(entry, current_user):
            raise HTTPException(status_code=404, detail="Catalog entry not found")
        return entry
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to retrieve catalog entry detail: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve dataset details. Please try again later."
        )


@app.get("/api/activity/summary")
async def get_activity_summary(
    days: int = 30,
    recent_limit: int = 20,
    current_user: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    try:
        return build_activity_summary(
            current_user=current_user,
            days=max(1, min(days, 365)),
            recent_limit=max(5, min(recent_limit, 100)),
        )
    except Exception as exc:
        logger.exception("Failed to build activity summary: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve activity summary. Please try again later."
        )


@app.get("/api/dashboard/summary")
async def get_dashboard_summary(
    days: int = 30,
    recent_limit: int = 12,
    catalog_limit: int = 20,
    current_user: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    try:
        return build_dashboard_summary(
            current_user=current_user,
            days=days,
            recent_limit=recent_limit,
            catalog_limit=catalog_limit,
        )
    except Exception as exc:
        logger.exception("Failed to build dashboard summary: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve dashboard summary. Please try again later."
        )


@app.get("/api/dashboard/trends")
async def get_dashboard_trends(
    window_days: int = 7,
    current_user: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    try:
        return build_dashboard_trends(
            current_user=current_user,
            window_days=window_days,
        )
    except Exception as exc:
        logger.exception("Failed to build dashboard trends: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve dashboard trends. Please try again later."
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


@app.post("/api/quality/score")
async def score_data_quality(
    payload: dict = Body(...),
    _: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    """Calculate comprehensive data quality metrics for a dataset."""
    try:
        rows = payload.get("rows", [])
        
        if not rows:
            raise HTTPException(status_code=400, detail="No data to score")
        
        dataframe = pl.from_dicts(rows)
        metrics = calculate_data_quality_metrics(dataframe)
        
        return {
            "status": "success",
            "metrics": metrics,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quality scoring failed: {str(e)}")


@app.post("/api/quality/report")
async def generate_quality_report(
    payload: dict = Body(...),
    _: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    """Generate a human-readable data quality report."""
    try:
        rows = payload.get("rows", [])
        
        if not rows:
            raise HTTPException(status_code=400, detail="No data to analyze")
        
        dataframe = pl.from_dicts(rows)
        report = get_quality_report(dataframe)
        
        return {
            "status": "success",
            "report": report,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


@app.get("/api/workflows")
async def get_workflows(_: dict = Depends(require_role(["viewer", "analyst", "admin"]))):
    try:
        return {"items": list_workflows()}
    except Exception as exc:
        logger.exception("Failed to list workflows: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve workflows. Please try again later."
        )


@app.post("/api/workflows")
async def create_workflow(
    payload: WorkflowCreateRequest,
    _: dict = Depends(require_role(["analyst", "admin"])),
):
    try:
        workflow = create_workflow_definition(payload.model_dump())
        save_workflow(workflow)
        return {"workflow": workflow}
    except Exception as exc:
        logger.exception("Failed to create workflow: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to save workflow definition. Please check inputs."
        )


@app.get("/api/workflows/{workflow_id}")
async def get_workflow_detail(
    workflow_id: str,
    _: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    try:
        workflow = get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return workflow
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to retrieve workflow details: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve workflow details. Please try again later."
        )


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

    try:
        dataframe = pl.from_dicts(raw_data)
        ai_summary = generate_business_insights(cleaning_stats, ml_results)
        target_column = None
        if isinstance(ml_results, dict):
            target_column = ml_results.get("target_column") or ml_results.get("target")
        pdf_bytes = create_pdf_in_memory(ai_summary, dataframe, target_column=target_column)
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
    except Exception as exc:
        logger.exception("Failed to generate export ZIP: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to generate results export. Please try again later."
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
    current_user: dict = Depends(require_role(["analyst", "admin"])),
):
    contents = await file.read()

    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    file_b64 = base64.b64encode(contents).decode("utf-8")
    try:
        user_dict = {"username": current_user["username"], "role": current_user["role"]}
        task = async_clean_data.delay(file_b64, file.filename, user_dict)
        await broadcast_event({
            "type": "task:update",
            "payload": {
                "task_id": task.id,
                "status": "started",
                "payload": {"action": "clean", "file_name": file.filename},
            },
        })
    except Exception as exc:
        logger.exception("Failed to dispatch background clean task")
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
    current_user: dict = Depends(require_role(["analyst", "admin"])),
):
    contents = await file.read()

    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    file_b64 = base64.b64encode(contents).decode("utf-8")
    try:
        user_dict = {"username": current_user["username"], "role": current_user["role"]}
        task = async_run_automl.delay(file_b64, file.filename, target_column, user_dict)
        await broadcast_event({
            "type": "task:update",
            "payload": {
                "task_id": task.id,
                "status": "started",
                "payload": {"action": "automl", "target_column": target_column, "file_name": file.filename},
            },
        })
    except Exception as exc:
        logger.warning(f"Background worker unavailable, falling back to sync AutoML: {exc}")
        try:
            file_bytes = base64.b64decode(file_b64)
            from connectors import read_dataset_from_bytes
            dataframe = read_dataset_from_bytes(file_bytes, file.filename)
            ml_result = run_automl_stateless(dataframe, target_column)
            task_id = "sync-" + base64.b64encode(f"{target_column}:{datetime.now(timezone.utc).isoformat()}".encode()).decode()[:16]
            return {
                "task_id": task_id,
                "message": "AutoML completed synchronously (worker unavailable).",
                "sync_result": ml_result,
            }
        except Exception as sync_exc:
            logger.exception("Sync AutoML fallback failed")
            raise HTTPException(
                status_code=503,
                detail=(
                    "AutoML process failed both in background and fallback modes. "
                    "Verify target column exists and is valid."
                ),
            ) from sync_exc
    return {"task_id": task.id, "message": "AutoML process started in background."}


@app.get("/api/task-status/{task_id}")
async def get_task_status(
    task_id: str,
    _: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    try:
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
            payload = {
                "task_id": task_id,
                "status": "completed",
                "payload": task_result.result or {},
                "ts": datetime.now(timezone.utc).isoformat(),
            }
            await broadcast_event({
                "type": "task:update",
                "payload": payload
            })
            return {"state": task_result.state, "result": task_result.result}

        if task_result.state == "REVOKED":
            payload = {
                "task_id": task_id,
                "status": "revoked",
                "payload": {"status": "Task was cancelled by user."},
                "ts": datetime.now(timezone.utc).isoformat(),
            }
            await broadcast_event({
                "type": "task:update",
                "payload": payload
            })
            return {"state": task_result.state, "status": "Task was cancelled by user."}

        payload = {
            "task_id": task_id,
            "status": "failed" if task_result.state == "FAILURE" else task_result.state,
            "payload": {"info": str(task_result.info)},
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        await broadcast_event({
            "type": "task:update",
            "payload": payload
        })
        return {
            "state": task_result.state,
            "status": str(task_result.info),
        }
    except Exception as exc:
        logger.exception("Failed to query task status: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to query background task status. Verify connection to task worker."
        )


@app.post("/api/revoke-task/{task_id}")
def revoke_task(
    task_id: str,
    _: dict = Depends(require_role(["analyst", "admin"])),
):
    try:
        celery_app.control.revoke(task_id, terminate=True, signal="SIGTERM")
        return {"message": f"Task {task_id} has been cancelled."}
    except Exception as exc:
        logger.exception("Failed to revoke task: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to cancel background task. Verify worker status."
        )


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
    try:
        return {
            "status": "ok",
            "message": "Welcome Admin",
            "capabilities": ["user_management", "system_configuration", "audit_access"],
        }
    except Exception as exc:
        logger.exception("Admin stats check failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve admin statistics."
        )


@app.post("/api/data-insights")
async def data_insights(
    payload: dict = Body(...),
    _: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    """Generate comprehensive data insights from uploaded dataset rows."""
    try:
        rows = payload.get("rows", [])
        if not rows:
            raise HTTPException(status_code=400, detail="No data provided for insights")

        df = pl.from_dicts(rows)
        total_rows = df.height
        total_cols = df.width

        # ── 1. Column-level statistics ──
        column_stats = []
        numeric_cols = []
        categorical_cols = []

        for col_name in df.columns:
            col = df[col_name]
            dtype_str = str(col.dtype)
            null_count = col.null_count()
            null_pct = round((null_count / total_rows) * 100, 2) if total_rows > 0 else 0
            unique_count = col.n_unique()

            stat = {
                "name": col_name,
                "dtype": dtype_str,
                "null_count": int(null_count),
                "null_pct": null_pct,
                "unique_count": int(unique_count),
                "completeness": round(100 - null_pct, 2),
            }

            # Check if numeric
            is_numeric = col.dtype in (pl.Float32, pl.Float64, pl.Int8, pl.Int16, pl.Int32, pl.Int64, pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64)

            if not is_numeric:
                # Try casting string to numeric
                try:
                    casted = col.cast(pl.Float64, strict=False).drop_nulls()
                    if casted.len() > total_rows * 0.5:  # >50% are numeric
                        is_numeric = True
                        col = casted
                except Exception:
                    pass

            if is_numeric:
                numeric_cols.append(col_name)
                try:
                    num_col = col.cast(pl.Float64, strict=False).drop_nulls()
                    if num_col.len() > 0:
                        stat["mean"] = round(float(num_col.mean()), 4)
                        stat["median"] = round(float(num_col.median()), 4)
                        stat["std"] = round(float(num_col.std()), 4) if num_col.len() > 1 else 0
                        stat["min"] = round(float(num_col.min()), 4)
                        stat["max"] = round(float(num_col.max()), 4)
                        q1 = float(num_col.quantile(0.25))
                        q3 = float(num_col.quantile(0.75))
                        iqr = q3 - q1
                        lower = q1 - 1.5 * iqr
                        upper = q3 + 1.5 * iqr
                        outlier_count = int(num_col.filter((num_col < lower) | (num_col > upper)).len())
                        stat["q1"] = round(q1, 4)
                        stat["q3"] = round(q3, 4)
                        stat["iqr"] = round(iqr, 4)
                        stat["outlier_count"] = outlier_count
                        stat["outlier_pct"] = round((outlier_count / num_col.len()) * 100, 2) if num_col.len() > 0 else 0
                        stat["type"] = "numeric"

                        # Histogram bins (5 buckets)
                        try:
                            mn, mx = float(num_col.min()), float(num_col.max())
                            if mn < mx:
                                step = (mx - mn) / 5
                                bins = []
                                for i in range(5):
                                    lo = mn + i * step
                                    hi = mn + (i + 1) * step
                                    cnt = int(num_col.filter((num_col >= lo) & (num_col < hi)).len()) if i < 4 else int(num_col.filter((num_col >= lo) & (num_col <= hi)).len())
                                    bins.append({"range": f"{lo:.1f}-{hi:.1f}", "count": cnt})
                                stat["distribution"] = bins
                        except Exception:
                            pass
                except Exception:
                    stat["type"] = "numeric"
            else:
                categorical_cols.append(col_name)
                stat["type"] = "categorical"
                # Top 5 values
                try:
                    vc = col.drop_nulls().cast(pl.Utf8).value_counts(sort=True)
                    top5 = vc.head(5).to_dicts()
                    stat["top_values"] = [{"value": str(r.get(col_name, r.get("value", ""))), "count": int(r.get("count", r.get("counts", 0)))} for r in top5]
                except Exception:
                    stat["top_values"] = []

            column_stats.append(stat)

        # ── 2. Data type distribution ──
        type_counts = {}
        for s in column_stats:
            t = s.get("type", "other")
            type_counts[t] = type_counts.get(t, 0) + 1

        # ── 3. Correlation matrix (top numeric columns, max 10) ──
        correlation_data = []
        top_numeric = numeric_cols[:10]
        if len(top_numeric) >= 2:
            try:
                num_df = df.select([pl.col(c).cast(pl.Float64, strict=False) for c in top_numeric]).drop_nulls()
                if num_df.height > 2:
                    for i, c1 in enumerate(top_numeric):
                        for j, c2 in enumerate(top_numeric):
                            if i < j:
                                try:
                                    corr_val = float(num_df[c1].pearson_corr(num_df[c2]))
                                    if abs(corr_val) > 0.3:
                                        correlation_data.append({
                                            "col1": c1, "col2": c2,
                                            "correlation": round(corr_val, 4),
                                            "strength": "Strong" if abs(corr_val) > 0.7 else "Moderate"
                                        })
                                except Exception:
                                    pass
            except Exception:
                pass

        # Sort by absolute correlation
        correlation_data.sort(key=lambda x: abs(x["correlation"]), reverse=True)

        # ── 4. Missing data summary ──
        missing_cols = [s for s in column_stats if s["null_count"] > 0]
        missing_cols.sort(key=lambda x: x["null_pct"], reverse=True)
        total_null_cells = sum(s["null_count"] for s in column_stats)
        total_cells = total_rows * total_cols

        # ── 5. Duplicate detection ──
        dup_count = int(df.filter(df.is_duplicated()).height)

        # ── 6. Auto-generated key findings ──
        findings = []

        # Data size
        findings.append({
            "type": "info",
            "title": "Dataset Size",
            "detail": f"{total_rows:,} rows × {total_cols} columns ({total_rows * total_cols:,} total cells)"
        })

        # Missing data
        if total_null_cells > 0:
            miss_pct = round((total_null_cells / total_cells) * 100, 2)
            severity = "warning" if miss_pct > 5 else "info"
            findings.append({
                "type": severity,
                "title": "Missing Data",
                "detail": f"{total_null_cells:,} missing cells ({miss_pct}%) across {len(missing_cols)} column(s)"
            })
        else:
            findings.append({"type": "success", "title": "No Missing Data", "detail": "All cells are complete — excellent data quality"})

        # Duplicates
        if dup_count > 0:
            findings.append({
                "type": "warning",
                "title": "Duplicate Rows",
                "detail": f"{dup_count:,} duplicate rows found ({round(dup_count/total_rows*100,1)}%)"
            })
        else:
            findings.append({"type": "success", "title": "No Duplicates", "detail": "All rows are unique"})

        # Outliers
        total_outliers = sum(s.get("outlier_count", 0) for s in column_stats)
        if total_outliers > 0:
            findings.append({
                "type": "warning",
                "title": "Outliers Detected",
                "detail": f"{total_outliers:,} outlier values across numeric columns (IQR method)"
            })

        # Strong correlations
        strong_corrs = [c for c in correlation_data if abs(c["correlation"]) > 0.7]
        if strong_corrs:
            pairs = ", ".join([f"{c['col1']}↔{c['col2']} ({c['correlation']:.2f})" for c in strong_corrs[:3]])
            findings.append({
                "type": "info",
                "title": "Strong Correlations",
                "detail": f"Found {len(strong_corrs)} strongly correlated pair(s): {pairs}"
            })

        # High cardinality categoricals
        high_card = [s for s in column_stats if s.get("type") == "categorical" and s["unique_count"] > total_rows * 0.5]
        if high_card:
            findings.append({
                "type": "info",
                "title": "High Cardinality",
                "detail": f"{len(high_card)} categorical column(s) have >50% unique values: {', '.join(c['name'] for c in high_card[:3])}"
            })

        return {
            "status": "success",
            "overview": {
                "total_rows": total_rows,
                "total_cols": total_cols,
                "total_cells": total_cells,
                "total_null_cells": total_null_cells,
                "null_pct": round((total_null_cells / total_cells) * 100, 2) if total_cells > 0 else 0,
                "duplicate_rows": dup_count,
                "numeric_cols": len(numeric_cols),
                "categorical_cols": len(categorical_cols),
            },
            "column_stats": column_stats,
            "type_distribution": type_counts,
            "correlations": correlation_data[:20],
            "missing_summary": [{"name": c["name"], "null_count": c["null_count"], "null_pct": c["null_pct"]} for c in missing_cols[:20]],
            "findings": findings,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Data insights generation failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Insights generation failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    import os

    # Allow toggling debug/reload/log level via environment variables
    debug_flag = os.getenv('DEBUG', os.getenv('DEBUG_MODE', 'false')).lower() in ('1', 'true', 'yes')
    reload_flag = os.getenv('RELOAD', 'false').lower() in ('1', 'true', 'yes') or debug_flag
    log_level = os.getenv('LOG_LEVEL', os.getenv('LOGLEVEL', 'info')).lower()

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv('PORT', 8000)),
        reload=reload_flag,
        log_level=log_level,
    )