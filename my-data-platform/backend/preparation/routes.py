import os
import json
import logging
from datetime import datetime
from typing import Tuple
from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user
from pipeline_engine.models import Project, PipelineNode
from preparation.models import DatasetVersion, Transformation, TransformationHistory, UndoRedoStack
from preparation.service import DatasetPreparerService
import polars as pl

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/preparation", tags=["intelligent-preparation-studio"])


def _initialize_undo_redo_stack(db: Session, project_id: str, raw_file_path: str) -> Tuple[DatasetVersion, UndoRedoStack]:
    """Helper to register the initial version (v1) of the dataset if not already registered."""
    stack = db.query(UndoRedoStack).filter(UndoRedoStack.project_id == project_id).first()
    if stack:
        # Get active version
        active_ver = db.query(DatasetVersion).filter(
            DatasetVersion.project_id == project_id,
            DatasetVersion.version_num == stack.current_pointer
        ).first()
        if active_ver:
            return active_ver, stack

    # Determine dimensions
    try:
        if raw_file_path.endswith(".parquet"):
            df = pl.read_parquet(raw_file_path)
        else:
            # Fallback
            df = pl.read_csv(raw_file_path, ignore_errors=True)
        rows, cols = df.shape
    except Exception:
        rows, cols = 0, 0

    # Create v1 version record
    v1 = DatasetVersion(
        project_id=project_id,
        version_num=1,
        file_path=raw_file_path,
        rows=rows,
        columns=cols
    )
    db.add(v1)
    db.commit()
    db.refresh(v1)

    new_stack = UndoRedoStack(
        project_id=project_id,
        current_pointer=1,
        max_pointer=1
    )
    db.add(new_stack)
    db.commit()
    db.refresh(new_stack)

    # Add dummy initial transformation
    t = Transformation(
        operation_type="raw_ingestion",
        parameters={},
        description="Ingested original raw dataset."
    )
    db.add(t)
    db.commit()
    db.refresh(t)

    th = TransformationHistory(
        project_id=project_id,
        version_id=v1.id,
        transformation_id=t.id,
        step_num=1
    )
    db.add(th)
    db.commit()

    return v1, new_stack


@router.post("/run")
def run_transformation(
    project_id: str = Form(...),
    operation_type: str = Form(...),
    parameters_json: str = Form(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Executes a single data preparation step, updates history stack and records new dataset version."""
    try:
        # Parse params
        try:
            params = json.loads(parameters_json)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid parameters JSON payload.")

        # Find upload node file path
        upload_node = db.query(PipelineNode).filter(
            PipelineNode.project_id == project_id,
            PipelineNode.node_type == "UPLOAD"
        ).first()
        if not upload_node or not upload_node.output_meta:
            raise HTTPException(status_code=400, detail="No source dataset file uploaded for project.")

        raw_path = upload_node.output_meta.get("file_path")
        
        # Init version stack if empty
        active_ver, stack = _initialize_undo_redo_stack(db, project_id, raw_path)

        # Clear any redo steps (ahead of current pointer)
        if stack.current_pointer < stack.max_pointer:
            # Delete histories and versions ahead of pointer
            obsolete_histories = db.query(TransformationHistory).filter(
                TransformationHistory.project_id == project_id,
                TransformationHistory.step_num > stack.current_pointer
            ).all()
            for oh in obsolete_histories:
                db.delete(oh)
            
            obsolete_versions = db.query(DatasetVersion).filter(
                DatasetVersion.project_id == project_id,
                DatasetVersion.version_num > stack.current_pointer
            ).all()
            for ov in obsolete_versions:
                db.delete(ov)
            db.commit()

        next_version_num = stack.current_pointer + 1
        
        # Output version path
        project_dir = os.path.dirname(raw_path)
        output_file_name = f"version_{next_version_num}.parquet"
        output_path = os.path.join(project_dir, output_file_name)

        # Run preparation engine
        preparer = DatasetPreparerService(active_ver.file_path, output_path)
        comparison, ai_desc = preparer.execute_transform(operation_type, params)

        # Record new DatasetVersion
        new_ver = DatasetVersion(
            project_id=project_id,
            version_num=next_version_num,
            file_path=output_path,
            rows=comparison["rows_after"],
            columns=comparison["columns_after"]
        )
        db.add(new_ver)
        db.commit()
        db.refresh(new_ver)

        # Record Transformation
        trans = Transformation(
            operation_type=operation_type,
            parameters=params,
            description=ai_desc
        )
        db.add(trans)
        db.commit()
        db.refresh(trans)

        # Record History Step
        th = TransformationHistory(
            project_id=project_id,
            version_id=new_ver.id,
            transformation_id=trans.id,
            step_num=next_version_num
        )
        db.add(th)

        # Update stack pointers
        stack.current_pointer = next_version_num
        stack.max_pointer = next_version_num
        db.commit()

        # Update Project Active dataset info
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            project.dataset_id = f"{project_id}_v{next_version_num}"
            db.commit()

        # Generate a small preview of new version
        df_preview = pl.read_parquet(output_path).head(10)
        preview_data = df_preview.to_dicts()

        return {
            "success": True,
            "version_num": next_version_num,
            "comparison": comparison,
            "description": ai_desc,
            "preview_data": preview_data
        }

    except Exception as e:
        logger.exception("Failed to run data preparation operation")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
def get_transformation_history(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Retrieves applied transformation steps and active pointer for the project."""
    # Ensure raw is registered
    upload_node = db.query(PipelineNode).filter(
        PipelineNode.project_id == project_id,
        PipelineNode.node_type == "UPLOAD"
    ).first()
    if upload_node and upload_node.output_meta:
        raw_path = upload_node.output_meta.get("file_path")
        _initialize_undo_redo_stack(db, project_id, raw_path)

    stack = db.query(UndoRedoStack).filter(UndoRedoStack.project_id == project_id).first()
    if not stack:
        return {"current_pointer": 0, "steps": []}

    histories = db.query(TransformationHistory).filter(
        TransformationHistory.project_id == project_id
    ).order_by(TransformationHistory.step_num.asc()).all()

    steps = []
    for h in histories:
        trans = db.query(Transformation).filter(Transformation.id == h.transformation_id).first()
        ver = db.query(DatasetVersion).filter(DatasetVersion.id == h.version_id).first()
        if trans and ver:
            steps.append({
                "step_num": h.step_num,
                "operation_type": trans.operation_type,
                "description": trans.description,
                "rows": ver.rows,
                "columns": ver.columns,
                "version_num": ver.version_num
            })

    return {
        "current_pointer": stack.current_pointer,
        "max_pointer": stack.max_pointer,
        "steps": steps
    }


@router.post("/undo")
def undo_transformation(
    project_id: str = Form(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Reverts dataset version back by one step in history stack."""
    stack = db.query(UndoRedoStack).filter(UndoRedoStack.project_id == project_id).first()
    if not stack or stack.current_pointer <= 1:
        raise HTTPException(status_code=400, detail="Cannot undo. You are already at the initial raw dataset.")

    stack.current_pointer -= 1
    db.commit()

    active_ver = db.query(DatasetVersion).filter(
        DatasetVersion.project_id == project_id,
        DatasetVersion.version_num == stack.current_pointer
    ).first()

    return {
        "success": True,
        "current_pointer": stack.current_pointer,
        "version_num": active_ver.version_num,
        "rows": active_ver.rows,
        "columns": active_ver.columns
    }


@router.post("/redo")
def redo_transformation(
    project_id: str = Form(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Applies the next available forward transformation step in the stack."""
    stack = db.query(UndoRedoStack).filter(UndoRedoStack.project_id == project_id).first()
    if not stack or stack.current_pointer >= stack.max_pointer:
        raise HTTPException(status_code=400, detail="Cannot redo. You are at the latest transformation step.")

    stack.current_pointer += 1
    db.commit()

    active_ver = db.query(DatasetVersion).filter(
        DatasetVersion.project_id == project_id,
        DatasetVersion.version_num == stack.current_pointer
    ).first()

    return {
        "success": True,
        "current_pointer": stack.current_pointer,
        "version_num": active_ver.version_num,
        "rows": active_ver.rows,
        "columns": active_ver.columns
    }


@router.post("/rollback/{version}")
def rollback_version(
    version: int,
    project_id: str = Form(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Rolls back project state directly to a specific dataset version."""
    stack = db.query(UndoRedoStack).filter(UndoRedoStack.project_id == project_id).first()
    if not stack:
        raise HTTPException(status_code=404, detail="Undo redo stack not found.")

    target_ver = db.query(DatasetVersion).filter(
        DatasetVersion.project_id == project_id,
        DatasetVersion.version_num == version
    ).first()
    if not target_ver:
        raise HTTPException(status_code=404, detail=f"Version {version} not found in database.")

    stack.current_pointer = version
    db.commit()

    return {
        "success": True,
        "current_pointer": stack.current_pointer,
        "version_num": target_ver.version_num,
        "rows": target_ver.rows,
        "columns": target_ver.columns
    }


@router.get("/export")
def export_preparation_dataset(
    project_id: str,
    format: str = "csv",
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Streams download of the current active version dataset in selected format."""
    stack = db.query(UndoRedoStack).filter(UndoRedoStack.project_id == project_id).first()
    if not stack:
        raise HTTPException(status_code=404, detail="Dataset version stack not found.")

    active_ver = db.query(DatasetVersion).filter(
        DatasetVersion.project_id == project_id,
        DatasetVersion.version_num == stack.current_pointer
    ).first()

    if not active_ver or not os.path.exists(active_ver.file_path):
        raise HTTPException(status_code=404, detail="Dataset version file not found on disk.")

    if active_ver.file_path.endswith(".parquet"):
        df = pl.read_parquet(active_ver.file_path)
    else:
        df = pl.read_csv(active_ver.file_path, ignore_errors=True)

    import io
    buf = io.BytesIO()

    if format == "csv":
        df.write_csv(buf)
        buf.seek(0)
        return StreamingResponse(
            buf, media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=project_{project_id}_v{active_ver.version_num}.csv"}
        )
    elif format == "parquet":
        df.write_parquet(buf)
        buf.seek(0)
        return StreamingResponse(
            buf, media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename=project_{project_id}_v{active_ver.version_num}.parquet"}
        )
    elif format == "json":
        df.write_json(buf)
        buf.seek(0)
        return StreamingResponse(
            buf, media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=project_{project_id}_v{active_ver.version_num}.json"}
        )
    elif format == "sql":
        # Convert to light SQL script insert values
        columns_str = ", ".join(df.columns)
        sql_lines = []
        for row in df.head(100).to_dicts():
            vals = []
            for col in df.columns:
                v = row[col]
                if v is None:
                    vals.append("NULL")
                elif isinstance(v, str):
                    escaped = v.replace("'", "''")
                    vals.append(f"'{escaped}'")
                else:
                    vals.append(str(v))
            sql_lines.append(f"INSERT INTO dataset_table ({columns_str}) VALUES ({', '.join(vals)});")
        buf.write("\n".join(sql_lines).encode("utf-8"))
        buf.seek(0)
        return StreamingResponse(
            buf, media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename=project_{project_id}_v{active_ver.version_num}.sql"}
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported export format. Choose csv, parquet, json, or sql.")
