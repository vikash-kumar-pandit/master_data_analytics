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

from ml_engine import run_automl_stateless
from report_generator import generate_pdf_in_memory
from utils import analyze_dataframe, clean_dataframe, generate_cleaning_stats, read_csv_from_bytes
from worker import celery_app, async_clean_data, async_run_automl
from ai_engine import generate_business_insights
from pdf_generator import create_pdf_in_memory
from identifier import identify_dataset_semantics
from advanced_cleaner import advanced_data_cleaning
from ml_advanced import run_nocode_clustering, run_nocode_nlp
from security import sanitize_for_llm
from xai_engine import generate_shap_explanations
from auth import auth_router, require_role
from observability import setup_observability

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if origin.strip()],
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
    _: dict = Depends(require_role(["analyst", "admin"])),
):
    contents = await file.read()

    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        dataframe = read_csv_from_bytes(contents)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to parse CSV: {exc}") from exc

    analysis = analyze_dataframe(dataframe)
    semantics = identify_dataset_semantics(dataframe)
    analysis["domain_info"] = semantics

    return {
        "analysis": analysis,
        "grid_data": dataframe.to_dicts(),
        "sample_data": dataframe.head(10).to_dicts(),
    }


@app.post("/clean")
async def clean_file(
    file: UploadFile = File(...),
    _: dict = Depends(require_role(["analyst", "admin"])),
):
    contents = await file.read()

    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        dataframe = read_csv_from_bytes(contents)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to parse CSV: {exc}") from exc

    cleaned_dataframe = advanced_data_cleaning(dataframe)
    analysis = analyze_dataframe(cleaned_dataframe)
    semantics = identify_dataset_semantics(cleaned_dataframe)
    analysis["domain_info"] = semantics
    cleaning_stats = generate_cleaning_stats(dataframe, cleaned_dataframe)

    return {
        "analysis": analysis,
        "cleaning_stats": cleaning_stats,
        "grid_data": cleaned_dataframe.to_dicts(),
        "sample_data": cleaned_dataframe.head(10).to_dicts(),
        "cleaned_data": cleaned_dataframe.to_dicts(),
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
    _: dict = Depends(require_role(["analyst", "admin"])),
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

    return result


@app.post("/generate-insights")
async def generate_insights(
    payload: InsightRequest,
    _: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    client = build_openai_client()
    safe_summary = sanitize_for_llm(payload.data_summary)

    prompt = (
        "You are an expert data analyst. Review the dataset summary and provide 3 concise business insights "
        "and 3 practical recommendations in simple language. Focus on data quality issues, model implications, "
        "and business impact. Return plain text only. Dataset summary: "
        f"{safe_summary}"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You write clear, practical business analysis for non-technical users."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )
        return {"insights": response.choices[0].message.content or "", "pii_sanitized": True}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to generate insights: {exc}") from exc


@app.post("/api/clean-background")
async def clean_data_background(
    file: UploadFile = File(...),
    _: dict = Depends(require_role(["analyst", "admin"])),
):
    contents = await file.read()

    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    file_b64 = base64.b64encode(contents).decode("utf-8")
    task = async_clean_data.delay(file_b64)
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
    task = async_run_automl.delay(file_b64, target_column)
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
    _: dict = Depends(require_role(["analyst", "admin"])),
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

    return {
        "message": "Clustering applied",
        "columns": clustered.columns,
        "data": clustered.head(200).to_dicts(),
    }


@app.post("/api/apply-nlp")
async def apply_nlp_to_data(
    payload: NLPRequest,
    _: dict = Depends(require_role(["analyst", "admin"])),
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

    return {
        "message": "NLP Applied",
        "columns": categorized.columns,
        "data": categorized.head(200).to_dicts(),
    }


@app.post("/api/explain-automl")
async def explain_automl(
    payload: ExplainRequest,
    _: dict = Depends(require_role(["analyst", "admin"])),
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