import os
import uuid
import logging
import polars as pl
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from database import get_db
from dataset_engine.engine import DatasetEngine
from problem_definition.analyzer import ProblemAnalyzer
from pipeline_engine.engine import PipelineManager
from pipeline_engine.models import PipelineNode
from auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["dataset-pipeline-engine"])

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "storage", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/datasets/ingest")
async def ingest_dataset(
    file: UploadFile = File(...),
    project_name: str = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Ingests dataset, profiles metadata, recommends target, and registers pipeline project memory."""
    try:
        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
            
        # Save file locally for chunk profiling & DuckDB integration
        dataset_id = str(uuid.uuid4())
        file_ext = os.path.splitext(file.filename)[1].lower()
        local_path = os.path.join(UPLOAD_DIR, f"{dataset_id}{file_ext}")
        
        with open(local_path, "wb") as f:
            f.write(contents)
            
        # Profile dataset using DatasetEngine
        engine = DatasetEngine(local_path, dataset_id=dataset_id)
        metadata = engine.load_metadata()
        
        # Analyze schema with ProblemAnalyzer
        analyzer = ProblemAnalyzer(metadata)
        exec_plan = analyzer.generate_execution_plan()
        
        # Initialize pipeline session memory
        p_name = project_name or f"Project_{file.filename.split('.')[0]}_{uuid.uuid4().hex[:6]}"
        manager = PipelineManager(db)
        project = manager.create_project(name=p_name, dataset_id=dataset_id)
        
        # Update pipeline UPLOAD & PROFILE nodes status
        manager.update_node_status(
            project_id=project.id,
            node_type="UPLOAD",
            status="COMPLETED",
            output_meta={"filename": file.filename, "file_path": local_path, "dataset_id": dataset_id}
        )
        
        manager.update_node_status(
            project_id=project.id,
            node_type="PROFILE",
            status="COMPLETED",
            input_meta={"dataset_id": dataset_id},
            output_meta={"metadata": metadata, "execution_plan": exec_plan}
        )
        
        return {
            "project_id": project.id,
            "dataset_id": dataset_id,
            "project_name": project.name,
            "metadata": metadata,
            "execution_plan": exec_plan
        }
        
    except Exception as e:
        logger.exception("Failed to ingest dataset")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.get("/projects")
def list_projects(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Lists all pipeline projects in session memory."""
    manager = PipelineManager(db)
    projects = manager.list_projects()
    return [{"id": p.id, "name": p.name, "dataset_id": p.dataset_id, "current_node": p.current_node, "created_at": p.created_at} for p in projects]


@router.get("/projects/{project_id}")
def get_project(project_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Retrieves a single project's current state."""
    manager = PipelineManager(db)
    project = manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "id": project.id,
        "name": project.name,
        "dataset_id": project.dataset_id,
        "current_node": project.current_node,
        "created_at": project.created_at,
        "updated_at": project.updated_at
    }


@router.get("/projects/{project_id}/pipeline")
def get_pipeline(project_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Gets status of all pipeline nodes for a project."""
    manager = PipelineManager(db)
    return manager.get_pipeline_state(project_id)


@router.post("/projects/{project_id}/nodes/{node_type}")
def update_node(
    project_id: str,
    node_type: str,
    status: str = Form(...),
    input_meta: str = Form(None),
    output_meta: str = Form(None),
    logs: str = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Updates status, input, output, or logs of a specific pipeline step."""
    import json
    manager = PipelineManager(db)
    
    in_dict = json.loads(input_meta) if input_meta else None
    out_dict = json.loads(output_meta) if output_meta else None
    
    node = manager.update_node_status(
        project_id=project_id,
        node_type=node_type,
        status=status,
        input_meta=in_dict,
        output_meta=out_dict,
        logs=logs
    )
    return {"status": "success", "node_type": node.node_type, "node_status": node.status}


@router.get("/projects/{project_id}/export/{node_type}")
def export_step(
    project_id: str,
    node_type: str,
    format: str = "csv",
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Exports processed dataset at any specific pipeline node in multiple formats."""
    manager = PipelineManager(db)
    project = manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    upload_node = db.query(PipelineNode).filter(
        PipelineNode.project_id == project_id,
        PipelineNode.node_type == "UPLOAD"
    ).first()
    
    if not upload_node or not upload_node.output_meta:
        raise HTTPException(status_code=400, detail="Source dataset has not been ingested yet")
        
    file_path = upload_node.output_meta.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Ingested source dataset file not found on disk")
        
    # In a real environment, we'd read processed data from this node if available.
    # Otherwise, read source file and export.
    try:
        engine = DatasetEngine(file_path)
        df = engine.read_chunk(limit=50000) # read first 50k rows for export
        
        format_lower = format.lower()
        
        if format_lower == "csv":
            import io
            buf = io.BytesIO()
            df.write_csv(buf)
            buf.seek(0)
            return StreamingResponse(
                buf, 
                media_type="text/csv", 
                headers={"Content-Disposition": f"attachment; filename={project.name}_{node_type}.csv"}
            )
            
        elif format_lower == "parquet":
            import io
            buf = io.BytesIO()
            df.write_parquet(buf)
            buf.seek(0)
            return StreamingResponse(
                buf, 
                media_type="application/octet-stream", 
                headers={"Content-Disposition": f"attachment; filename={project.name}_{node_type}.parquet"}
            )
            
        elif format_lower == "json":
            import io
            buf = io.BytesIO()
            df.write_json(buf, row_oriented=True)
            buf.seek(0)
            return StreamingResponse(
                buf, 
                media_type="application/json", 
                headers={"Content-Disposition": f"attachment; filename={project.name}_{node_type}.json"}
            )
            
        elif format_lower == "excel":
            import io
            buf = io.BytesIO()
            df.to_pandas().to_excel(buf, index=False)
            buf.seek(0)
            return StreamingResponse(
                buf, 
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                headers={"Content-Disposition": f"attachment; filename={project.name}_{node_type}.xlsx"}
            )
            
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported export format: {format}")
            
    except Exception as e:
        logger.exception("Failed to export step")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
