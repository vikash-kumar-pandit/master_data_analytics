import os
import uuid
import logging
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from auth import require_role
from connectors import read_dataset_from_bytes
from utils import analyze_dataframe
from identifier import identify_dataset_semantics
from catalog import register_catalog_entry
from api.ws.monitor import broadcast_event
from upload_limits import preview_rows, read_upload_limited
from pipeline_engine.engine import PipelineManager

logger = logging.getLogger("datasets")
router = APIRouter()

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "storage", "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(["analyst", "admin"])),
):
    contents = await read_upload_limited(file)

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

    dataset_id = catalog_entry.get("id") if isinstance(catalog_entry, dict) else str(uuid.uuid4())
    file_ext = os.path.splitext(file.filename)[1].lower()
    local_path = os.path.join(UPLOAD_DIR, f"{dataset_id}{file_ext}")

    try:
        with open(local_path, "wb") as f:
            f.write(contents)
    except Exception as exc:
        logger.exception("Failed to write uploaded file to storage")

    # Automatically create a pipeline project so that the workspace, profiling, and prep screens are in sync!
    try:
        p_name = f"Project_{file.filename.split('.')[0]}_{uuid.uuid4().hex[:6]}"
        manager = PipelineManager(db)
        project = manager.create_project(name=p_name, dataset_id=dataset_id)

        # Update pipeline UPLOAD & PROFILE nodes status
        manager.update_node_status(
            project_id=project.id,
            node_type="UPLOAD",
            status="COMPLETED",
            output_meta={"filename": file.filename, "file_path": local_path, "dataset_id": dataset_id},
        )

        manager.update_node_status(
            project_id=project.id,
            node_type="PROFILE",
            status="COMPLETED",
            input_meta={"dataset_id": dataset_id},
            output_meta={"metadata": analysis, "execution_plan": {}},
        )
    except Exception as e:
        logger.exception(f"Failed to create pipeline project on upload: {e}")

    await broadcast_event(
        {
            "type": "catalog:activity",
            "payload": {
                "action": "upload",
                "dataset_name": file.filename,
                "rows": analysis.get("rows"),
                "cols": analysis.get("cols"),
                "catalog_id": dataset_id,
            },
        }
    )

    return {
        "analysis": analysis,
        "grid_data": preview_rows(dataframe),
        "sample_data": dataframe.head(10).to_dicts(),
        "total_rows": dataframe.height,
        "catalog_preview": {
            "dataset_name": file.filename,
            "summary": {
                "rows": analysis.get("rows"),
                "cols": analysis.get("cols"),
                "domain": semantics.get("domain"),
            },
        },
    }
