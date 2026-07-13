from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import polars as pl

from advanced_cleaner import advanced_data_arranging, advanced_data_cleaning
from catalog import register_catalog_entry
from database import SessionLocal
from identifier import identify_dataset_semantics
from models import WorkflowDefinition
from ml_advanced import run_nocode_clustering, run_nocode_nlp
from ml_engine import run_automl_stateless
from security import sanitize_for_llm
from utils import analyze_dataframe, generate_cleaning_stats
from xai_engine import generate_shap_explanations

ALLOWED_STEPS = ["profile", "arrange", "clean", "automl", "cluster", "nlp", "explain"]


def list_workflows() -> list[dict[str, Any]]:
    with SessionLocal() as db:
        workflows = db.query(WorkflowDefinition).order_by(WorkflowDefinition.created_at.desc()).all()
        return [{
            "id": wf.id,
            "name": wf.name,
            "description": wf.description,
            "steps": wf.steps,
            "created_by": wf.created_by,
            "created_at": wf.created_at.isoformat() if wf.created_at else None
        } for wf in workflows]


def get_workflow(workflow_id: str) -> dict[str, Any] | None:
    with SessionLocal() as db:
        wf = db.query(WorkflowDefinition).filter(WorkflowDefinition.id == workflow_id).first()
        if not wf:
            return None
        return {
            "id": wf.id,
            "name": wf.name,
            "description": wf.description,
            "steps": wf.steps,
            "created_by": wf.created_by,
            "created_at": wf.created_at.isoformat() if wf.created_at else None
        }


def save_workflow(workflow_data: dict):
    with SessionLocal() as db:
        wf = db.query(WorkflowDefinition).filter(WorkflowDefinition.id == workflow_data["id"]).first()
        if not wf:
            wf = WorkflowDefinition(
                id=workflow_data["id"],
                name=workflow_data.get("name"),
                description=workflow_data.get("description"),
                steps=workflow_data.get("steps", []),
                created_by=workflow_data.get("created_by")
            )
            db.add(wf)
        else:
            wf.name = workflow_data.get("name")
            wf.description = workflow_data.get("description")
            wf.steps = workflow_data.get("steps", [])
        db.commit()


def create_workflow_definition(payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name") or "Untitled Workflow").strip()
    steps = payload.get("steps") or []
    normalized_steps = []
    for step in steps:
        step_name = str(step).strip().lower()
        if step_name in ALLOWED_STEPS and step_name not in normalized_steps:
            normalized_steps.append(step_name)

    if not normalized_steps:
        raise ValueError("At least one valid workflow step is required")

    workflow = {
        "id": str(uuid.uuid4()),
        "name": name,
        "description": str(payload.get("description") or "").strip(),
        "steps": normalized_steps,
        "target_column": payload.get("target_column") or None,
        "text_column": payload.get("text_column") or None,
        "categories": [str(value).strip() for value in payload.get("categories") or [] if str(value).strip()],
        "num_clusters": int(payload.get("num_clusters") or 3),
        "sample_index": int(payload.get("sample_index") or 0),
        "top_k": int(payload.get("top_k") or 10),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return workflow


def execute_workflow(
    workflow: dict[str, Any],
    rows: list[dict[str, Any]],
    actor: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not rows:
        raise ValueError("No rows provided")

    current_dataframe = pl.from_dicts(rows)
    step_outputs: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}
    cleaning_stats: list[dict[str, Any]] = []
    ml_results: dict[str, Any] = {}
    semantics: dict[str, Any] = {}

    for step in workflow.get("steps", []):
        if step == "profile":
            analysis = analyze_dataframe(current_dataframe)
            semantics = identify_dataset_semantics(current_dataframe)
            analysis["domain_info"] = semantics
            step_outputs.append({"step": step, "rows": current_dataframe.height, "cols": current_dataframe.width})
            continue

        if step == "clean":
            before_dataframe = current_dataframe
            current_dataframe = advanced_data_cleaning(current_dataframe)
            analysis = analyze_dataframe(current_dataframe)
            semantics = identify_dataset_semantics(current_dataframe)
            analysis["domain_info"] = semantics
            cleaning_stats = generate_cleaning_stats(before_dataframe, current_dataframe)
            step_outputs.append({"step": step, "cleaned_rows": current_dataframe.height, "cleaned_cols": current_dataframe.width})
            continue

        if step == "arrange":
            before_dataframe = current_dataframe
            current_dataframe, arranging_notes = advanced_data_arranging(current_dataframe)
            analysis = analyze_dataframe(current_dataframe)
            semantics = identify_dataset_semantics(current_dataframe)
            analysis["domain_info"] = semantics
            cleaning_stats = generate_cleaning_stats(before_dataframe, current_dataframe)
            step_outputs.append(
                {
                    "step": step,
                    "arranged_rows": current_dataframe.height,
                    "arranged_cols": current_dataframe.width,
                    "notes": arranging_notes,
                }
            )
            continue

        if step == "automl":
            target_column = workflow.get("target_column")
            if not target_column:
                raise ValueError("target_column is required for AutoML")
            ml_results = run_automl_stateless(current_dataframe, target_column)
            step_outputs.append({"step": step, "target_column": target_column, "best_algorithm": ml_results.get("best_algorithm")})
            continue

        if step == "cluster":
            num_clusters = int(workflow.get("num_clusters") or 3)
            current_dataframe = run_nocode_clustering(current_dataframe, num_clusters=num_clusters)
            step_outputs.append({"step": step, "num_clusters": num_clusters, "columns": current_dataframe.columns})
            continue

        if step == "nlp":
            text_column = workflow.get("text_column")
            categories = workflow.get("categories") or []
            if not text_column:
                raise ValueError("text_column is required for NLP")
            if not categories:
                raise ValueError("categories are required for NLP")
            current_dataframe = run_nocode_nlp(current_dataframe, text_column, categories)
            step_outputs.append({"step": step, "text_column": text_column, "categories": categories})
            continue

        if step == "explain":
            target_column = workflow.get("target_column")
            if not target_column:
                raise ValueError("target_column is required for explainability")
            explanation = generate_shap_explanations(
                rows=current_dataframe.to_dicts(),
                target_column=target_column,
                sample_index=int(workflow.get("sample_index") or 0),
                top_k=int(workflow.get("top_k") or 10),
            )
            step_outputs.append({"step": step, "problem_type": explanation.get("problem_type"), "target_column": target_column})
            ml_results = {**ml_results, "explanation": explanation}
            continue

        raise ValueError(f"Unsupported workflow step: {step}")

    workflow_result = {
        "workflow_id": workflow.get("id"),
        "workflow_name": workflow.get("name"),
        "steps": workflow.get("steps", []),
        "step_outputs": step_outputs,
        "analysis": analysis,
        "cleaning_stats": cleaning_stats,
        "ml_results": ml_results,
        "final_columns": current_dataframe.columns,
        "data": current_dataframe.head(200).to_dicts(),
        "catalog_preview": {
            "name": workflow.get("name"),
            "steps": workflow.get("steps", []),
            "target_column": workflow.get("target_column"),
        },
    }

    register_catalog_entry(
        action="workflow",
        dataset_name=workflow.get("name"),
        analysis=analysis,
        cleaning_stats=cleaning_stats,
        ml_results=ml_results,
        rows=current_dataframe.head(50).to_dicts(),
        target_column=workflow.get("target_column"),
        source="workflow_builder",
        created_by=actor,
    )

    return workflow_result
