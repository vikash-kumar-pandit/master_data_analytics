import logging
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from pipeline_engine.models import Project, PipelineNode

logger = logging.getLogger(__name__)

class PipelineManager:
    """Manages project state, pipeline nodes status, and project memory persistence."""

    def __init__(self, db: Session):
        self.db = db

    def create_project(self, name: str, dataset_id: str = None) -> Project:
        """Initializes a new project session memory."""
        project = Project(name=name, dataset_id=dataset_id)
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        
        # Pre-populate basic pipeline nodes
        node_types = [
            "UPLOAD", "PROFILE", "QUALITY", "CLEANING", 
            "TRANSFORMATION", "FEATURE_ENGINEERING", "EDA", 
            "VISUALIZATION", "AUTOML", "EXPLAINABILITY", 
            "INSIGHTS", "REPORT", "EXPORT"
        ]
        
        for nt in node_types:
            node = PipelineNode(
                project_id=project.id,
                node_type=nt,
                status="COMPLETED" if nt == "UPLOAD" and dataset_id else "PENDING"
            )
            self.db.add(node)
            
        self.db.commit()
        return project

    def get_project(self, project_id: str) -> Project:
        """Retrieves project memory state by ID."""
        return self.db.query(Project).filter(Project.id == project_id).first()

    def list_projects(self) -> list[Project]:
        """Lists all project memory sessions."""
        return self.db.query(Project).order_by(Project.created_at.desc()).all()

    def update_node_status(
        self, 
        project_id: str, 
        node_type: str, 
        status: str, 
        input_meta: dict = None, 
        output_meta: dict = None, 
        logs: str = None
    ) -> PipelineNode:
        """Updates pipeline node execution telemetry and logs."""
        node = self.db.query(PipelineNode).filter(
            PipelineNode.project_id == project_id,
            PipelineNode.node_type == node_type
        ).first()
        
        if not node:
            node = PipelineNode(project_id=project_id, node_type=node_type)
            self.db.add(node)

        node.status = status
        if input_meta is not None:
            node.input_meta = input_meta
        if output_meta is not None:
            node.output_meta = output_meta
        if logs is not None:
            node.logs = logs
            
        node.updated_at = datetime.now(timezone.utc)
        
        # Also update current project step
        project = self.get_project(project_id)
        if project:
            project.current_node = node_type
            
        self.db.commit()
        self.db.refresh(node)
        return node

    def get_pipeline_state(self, project_id: str) -> list[dict]:
        """Returns the full execution status array of all nodes in a pipeline."""
        nodes = self.db.query(PipelineNode).filter(
            PipelineNode.project_id == project_id
        ).all()
        
        # Sort in standard pipeline order
        node_order = [
            "UPLOAD", "PROFILE", "QUALITY", "CLEANING", 
            "TRANSFORMATION", "FEATURE_ENGINEERING", "EDA", 
            "VISUALIZATION", "AUTOML", "EXPLAINABILITY", 
            "INSIGHTS", "REPORT", "EXPORT"
        ]
        
        node_map = {n.node_type: n for n in nodes}
        
        state_list = []
        for nt in node_order:
            if nt in node_map:
                n = node_map[nt]
                state_list.append({
                    "id": n.id,
                    "node_type": n.node_type,
                    "status": n.status,
                    "input_meta": n.input_meta,
                    "output_meta": n.output_meta,
                    "logs": n.logs,
                    "updated_at": n.updated_at.isoformat() if n.updated_at else None
                })
        return state_list
