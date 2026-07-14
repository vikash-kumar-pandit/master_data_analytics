import io
import os
import json
import base64
import logging
import zipfile
from datetime import datetime, timezone
from typing import Any
import asyncio

from fastapi import APIRouter, Depends, HTTPException, Body, Form, UploadFile, File
from fastapi.responses import StreamingResponse
import polars as pl
from celery.result import AsyncResult

from ml_engine import run_automl_stateless
from report_generator import generate_pdf_in_memory, generate_structured_report_pdf, generate_structured_report_pptx
from utils import analyze_dataframe, generate_cleaning_stats
from worker import celery_app, async_clean_data, async_run_automl
from ai_engine import generate_business_insights
from pdf_generator import create_pdf_in_memory
from identifier import identify_dataset_semantics
from advanced_cleaner import advanced_data_arranging, advanced_data_cleaning
from ml_advanced import run_nocode_clustering, run_nocode_nlp
from security import sanitize_for_llm
from xai_engine import generate_shap_explanations
from auth import require_role
from catalog import get_catalog_entry, is_catalog_entry_visible, list_catalog_entries_for_user, register_catalog_entry
from connectors import read_dataset_from_bytes
from workflows import create_workflow_definition, execute_workflow, get_workflow, list_workflows, save_workflow
from analytics_engine import analyze_question, compare_versions, forecast_metric
from data_quality import calculate_data_quality_metrics, get_quality_report
from feature_engineer import auto_feature_engineer
from api.ws.monitor import broadcast_event

# schemas
from schemas import (
    InsightRequest, ClusteringRequest, NLPRequest, ExplainRequest,
    CatalogQuery, WorkflowCreateRequest, WorkflowRunRequest, QuestionRequest,
    ForecastRequest, CompareRequest, StructuredReportRequest, SearchRequest
)

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

logger = logging.getLogger(__name__)

router = APIRouter()


# ── HELPERS ──

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


# ── ROUTES ──

@router.post("/api/analytics/query")
async def analytics_query(
    payload: QuestionRequest,
    current_user: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    try:
        if not payload:
            raise ValueError("Request payload is missing")
        
        question = str(payload.question or "").strip()
        if not question:
            raise ValueError("Question cannot be empty")
        
        if not isinstance(payload.rows, list):
            raise ValueError("rows must be a list")
        
        if not payload.rows:
            raise ValueError("No data provided")
        
        for i, row in enumerate(payload.rows):
            if not isinstance(row, dict):
                raise ValueError(f"Row {i} is not a dictionary")
        
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

        return result
    
    except ValueError as ve:
        logger.error(f"Validation error in analytics_query: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        logger.exception(f"Error in analytics_query: {exc}")
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


@router.post("/api/analytics/forecast")
async def analytics_forecast(
    payload: ForecastRequest,
    current_user: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    try:
        if not payload:
            raise ValueError("Request payload is missing")
        
        if not isinstance(payload.rows, list):
            raise ValueError("rows must be a list")
        
        if not payload.rows:
            raise ValueError("No data provided for forecasting")
        
        horizon = payload.horizon or 7
        if not isinstance(horizon, int) or horizon < 1:
            horizon = 7
        horizon = max(1, min(horizon, 30))
        
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

        return result
    
    except ValueError as ve:
        logger.error(f"Validation error in forecast: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"Unexpected error in analytics_forecast: {exc}")
        raise HTTPException(status_code=500, detail=f"Forecasting failed: {str(exc)[:200]}")


@router.post("/api/analytics/compare")
async def analytics_compare(
    payload: CompareRequest,
    current_user: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    try:
        if not payload:
            raise ValueError("Request payload is missing")
        
        if not isinstance(payload.before_rows, list):
            raise ValueError("before_rows must be a list")
        
        if not payload.before_rows:
            raise ValueError("before_rows cannot be empty")
        
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

        return result
    
    except ValueError as ve:
        logger.error(f"Validation error in compare: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"Unexpected error in analytics_compare: {exc}")
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(exc)[:200]}")


@router.post("/api/analytics/report")
async def analytics_report_pdf(
    payload: StructuredReportRequest,
    _: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    try:
        if not payload:
            raise ValueError("Request payload is missing")
        
        title = str(payload.title or "Report").strip()
        if not title:
            title = "Analytics Report"
        
        subtitle = str(payload.subtitle or "").strip()
        
        if payload.sections is None:
            sections = []
        elif isinstance(payload.sections, list):
            sections = payload.sections
        else:
            raise ValueError("sections must be a list")
        
        validated_sections = []
        for i, section in enumerate(sections):
            if not isinstance(section, dict):
                logger.warning(f"Section {i} is not a dict, skipping")
                continue
            validated_sections.append(section)
        
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


@router.post("/clean")
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


@router.post("/arrange")
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


@router.post("/download")
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


@router.get("/api/catalog")
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


@router.get("/api/catalog/{entry_id}")
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


@router.post("/api/search/catalog")
async def search_catalog(
    search_req: SearchRequest,
    current_user: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    try:
        limit = max(1, min(search_req.limit, 100))
        offset = max(0, search_req.offset)
        
        all_entries = list_catalog_entries_for_user(current_user, limit=1000)
        
        if search_req.query:
            query_lower = search_req.query.lower()
            all_entries = [
                e for e in all_entries
                if query_lower in (e.get("name", "") or "").lower()
                or query_lower in (e.get("description", "") or "").lower()
            ]
        
        if search_req.data_type:
            all_entries = [e for e in all_entries if e.get("type") == search_req.data_type]
        
        if search_req.owner:
            all_entries = [e for e in all_entries if e.get("owner") == search_req.owner]
        
        if search_req.tags:
            all_entries = [
                e for e in all_entries
                if any(tag in (e.get("tags", []) or []) for tag in search_req.tags)
            ]
        
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


@router.post("/api/quality/score")
async def score_data_quality(
    payload: dict = Body(...),
    _: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
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


@router.post("/api/quality/report")
async def generate_quality_report(
    payload: dict = Body(...),
    _: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
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


@router.get("/api/workflows")
async def get_workflows(_: dict = Depends(require_role(["viewer", "analyst", "admin"]))):
    try:
        return {"items": list_workflows()}
    except Exception as exc:
        logger.exception("Failed to list workflows: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve workflows. Please try again later."
        )


@router.post("/api/workflows")
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


@router.get("/api/workflows/{workflow_id}")
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


@router.post("/api/workflows/{workflow_id}/run")
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


@router.post("/api/export-results")
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


@router.post("/automl")
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


@router.post("/generate-insights")
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


@router.post("/api/clean-background")
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


@router.post("/api/predict-background")
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


@router.get("/api/task-status/{task_id}")
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


@router.post("/api/revoke-task/{task_id}")
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


@router.post("/api/explain-automl")
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


@router.post("/api/run-clustering")
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


@router.post("/api/apply-nlp")
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


@router.post("/api/data-insights")
async def data_insights(
    payload: dict = Body(...),
    _: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    try:
        rows = payload.get("rows", [])
        if not rows:
            raise HTTPException(status_code=400, detail="No data provided for insights")

        df = pl.from_dicts(rows)
        total_rows = df.height
        total_cols = df.width

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

            is_numeric = col.dtype in (pl.Float32, pl.Float64, pl.Int8, pl.Int16, pl.Int32, pl.Int64, pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64)

            if not is_numeric:
                try:
                    casted = col.cast(pl.Float64, strict=False).drop_nulls()
                    if casted.len() > total_rows * 0.5:
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
                try:
                    vc = col.drop_nulls().cast(pl.Utf8).value_counts(sort=True)
                    top5 = vc.head(5).to_dicts()
                    stat["top_values"] = [{"value": str(r.get(col_name, r.get("value", ""))), "count": int(r.get("count", r.get("counts", 0)))} for r in top5]
                except Exception:
                    stat["top_values"] = []

            column_stats.append(stat)

        type_counts = {}
        for s in column_stats:
            t = s.get("type", "other")
            type_counts[t] = type_counts.get(t, 0) + 1

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

        correlation_data.sort(key=lambda x: abs(x["correlation"]), reverse=True)

        missing_cols = [s for s in column_stats if s["null_count"] > 0]
        missing_cols.sort(key=lambda x: x["null_pct"], reverse=True)
        total_null_cells = sum(s["null_count"] for s in column_stats)
        total_cells = total_rows * total_cols

        dup_count = int(df.filter(df.is_duplicated()).height)

        findings = []

        findings.append({
            "type": "info",
            "title": "Dataset Size",
            "detail": f"{total_rows:,} rows × {total_cols} columns ({total_rows * total_cols:,} total cells)"
        })

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

        if dup_count > 0:
            findings.append({
                "type": "warning",
                "title": "Duplicate Rows",
                "detail": f"{dup_count:,} duplicate rows found ({round(dup_count/total_rows*100,1)}%)"
            })
        else:
            findings.append({"type": "success", "title": "No Duplicates", "detail": "All rows are unique"})

        total_outliers = sum(s.get("outlier_count", 0) for s in column_stats)
        if total_outliers > 0:
            findings.append({
                "type": "warning",
                "title": "Outliers Detected",
                "detail": f"{total_outliers:,} outlier values across numeric columns (IQR method)"
            })

        strong_corrs = [c for c in correlation_data if abs(c["correlation"]) > 0.7]
        if strong_corrs:
            pairs = ", ".join([f"{c['col1']}↔{c['col2']} ({c['correlation']:.2f})" for c in strong_corrs[:3]])
            findings.append({
                "type": "info",
                "title": "Strong Correlations",
                "detail": f"Found {len(strong_corrs)} strongly correlated pair(s): {pairs}"
            })

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


@router.post("/api/export/excel")
async def export_to_excel(
    payload: dict = Body(...),
    _: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    try:
        rows = payload.get("rows", [])
        filename = payload.get("filename", "export") or "export"
        filename = filename.replace(" ", "_")[:50]
        
        if not rows:
            raise HTTPException(status_code=400, detail="No data to export")
        
        dataframe = pl.from_dicts(rows)
        excel_buffer = io.BytesIO()
        dataframe.write_excel(excel_buffer)
        excel_buffer.seek(0)
        
        return StreamingResponse(
            excel_buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}.xlsx"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.post("/api/export/parquet")
async def export_to_parquet(
    payload: dict = Body(...),
    _: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    try:
        rows = payload.get("rows", [])
        filename = payload.get("filename", "export") or "export"
        filename = filename.replace(" ", "_")[:50]
        
        if not rows:
            raise HTTPException(status_code=400, detail="No data to export")
        
        dataframe = pl.from_dicts(rows)
        parquet_buffer = io.BytesIO()
        dataframe.write_parquet(parquet_buffer)
        parquet_buffer.seek(0)
        
        return StreamingResponse(
            parquet_buffer,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={filename}.parquet"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.post("/api/export/json")
async def export_to_json(
    payload: dict = Body(...),
    _: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    try:
        rows = payload.get("rows", [])
        filename = payload.get("filename", "export") or "export"
        filename = filename.replace(" ", "_")[:50]
        
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
