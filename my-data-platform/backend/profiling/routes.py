import os
import json
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user
from pipeline_engine.models import Project, PipelineNode
from pipeline_engine.engine import PipelineManager
from profiling.models import DatasetProfile
from profiling.service import DatasetProfilerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/profile", tags=["universal-profiling-engine"])


@router.post("/run")
def run_profile(
    project_id: str = Form(...),
    target_column: str = Form(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Triggers the advanced universal profiling engine on the project's dataset."""
    try:
        manager = PipelineManager(db)
        project = manager.get_project(project_id)
        if not project or not project.dataset_id:
            raise HTTPException(status_code=404, detail="Project or dataset not found")

        # Get uploaded file path from node
        upload_node = db.query(PipelineNode).filter(
            PipelineNode.project_id == project_id,
            PipelineNode.node_type == "UPLOAD"
        ).first()

        if not upload_node or not upload_node.output_meta:
            raise HTTPException(status_code=400, detail="Upload node has no uploaded file metadata")

        file_path = upload_node.output_meta.get("file_path")
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Dataset file not found on disk")

        # Run profiling
        profiler = DatasetProfilerService(file_path)
        profile_data = profiler.run_profiling(target_column=target_column)

        # Update or create DatasetProfile record in DB
        existing_profile = db.query(DatasetProfile).filter(
            DatasetProfile.dataset_id == project.dataset_id
        ).first()

        if existing_profile:
            db.delete(existing_profile)
            db.commit()

        new_profile = DatasetProfile(
            dataset_id=project.dataset_id,
            rows=profile_data["rows"],
            columns=profile_data["columns"],
            memory=float(profile_data["memory_usage_bytes"]),
            disk=float(profile_data["file_size"]),
            schema_info=profile_data["schema"],
            warnings=profile_data["warnings"],
            recommendations=profile_data["recommendations"],
            statistics=profile_data["statistics"],
            story=profile_data["story"],
            summary=profile_data["summary"]
        )
        db.add(new_profile)
        db.commit()
        db.refresh(new_profile)

        # Update Pipeline nodes status
        manager.update_node_status(
            project_id=project_id,
            node_type="PROFILE",
            status="COMPLETED",
            output_meta={"profile_id": new_profile.id, "summary": profile_data["summary"]}
        )

        quality_score = max(0, 100 - len(profile_data["warnings"]) * 10)
        manager.update_node_status(
            project_id=project_id,
            node_type="QUALITY",
            status="COMPLETED",
            output_meta={"quality_score": f"{quality_score}%", "warnings_count": len(profile_data["warnings"])}
        )

        return {
            "profile_id": new_profile.id,
            "dataset_id": project.dataset_id,
            "data": profile_data
        }

    except Exception as e:
        logger.exception("Failed to run profiling pipeline")
        raise HTTPException(status_code=500, detail=f"Profiling run failed: {str(e)}")


@router.get("/{dataset_id}")
def get_profile(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Retrieves an existing profiling run from memory database."""
    profile = db.query(DatasetProfile).filter(DatasetProfile.dataset_id == dataset_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="No profile run matches this dataset ID")
        
    return {
        "id": profile.id,
        "dataset_id": profile.dataset_id,
        "rows": profile.rows,
        "columns": profile.columns,
        "memory": profile.memory,
        "disk": profile.disk,
        "schema": profile.schema_info,
        "warnings": profile.warnings,
        "recommendations": profile.recommendations,
        "statistics": profile.statistics,
        "story": profile.story,
        "summary": profile.summary,
        "created_at": profile.created_at
    }


@router.get("/export/json")
def export_profile_json(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Downloads profiling summary as JSON file."""
    profile = db.query(DatasetProfile).filter(DatasetProfile.dataset_id == dataset_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    import io
    buf = io.BytesIO()
    payload = {
        "dataset_id": profile.dataset_id,
        "rows": profile.rows,
        "columns": profile.columns,
        "memory": profile.memory,
        "disk": profile.disk,
        "schema": profile.schema_info,
        "warnings": profile.warnings,
        "recommendations": profile.recommendations,
        "statistics": profile.statistics,
        "story": profile.story,
        "summary": profile.summary
    }
    buf.write(json.dumps(payload, indent=2).encode("utf-8"))
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=profile_{dataset_id}.json"}
    )


@router.get("/export/html")
def export_profile_html(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Downloads profiling dashboard as standalone HTML page."""
    profile = db.query(DatasetProfile).filter(DatasetProfile.dataset_id == dataset_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    html_str = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Data Profile Summary Report</title>
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    </head>
    <body class="bg-gray-50 text-gray-800 font-sans p-10">
        <div class="max-w-5xl mx-auto bg-white shadow-xl rounded-2xl p-8 border border-gray-200">
            <h1 class="text-3xl font-extrabold text-indigo-900 border-b pb-4 mb-6 uppercase">Universal Data Profile</h1>
            
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                <div class="p-4 bg-indigo-50 border border-indigo-150 rounded-xl">
                    <span class="text-xs text-indigo-500 font-bold uppercase">Rows Count</span>
                    <p class="text-2xl font-black text-indigo-900">{profile.rows:,}</p>
                </div>
                <div class="p-4 bg-indigo-50 border border-indigo-150 rounded-xl">
                    <span class="text-xs text-indigo-500 font-bold uppercase">Columns Count</span>
                    <p class="text-2xl font-black text-indigo-900">{profile.columns}</p>
                </div>
                <div class="p-4 bg-indigo-50 border border-indigo-150 rounded-xl">
                    <span class="text-xs text-indigo-500 font-bold uppercase">Memory Size</span>
                    <p class="text-xl font-bold text-indigo-900">{profile.memory / 1024:.1f} KB</p>
                </div>
                <div class="p-4 bg-indigo-50 border border-indigo-150 rounded-xl">
                    <span class="text-xs text-indigo-500 font-bold uppercase">Disk Weight</span>
                    <p class="text-xl font-bold text-indigo-900">{profile.disk / 1024:.1f} KB</p>
                </div>
            </div>

            <h2 class="text-xl font-bold text-gray-700 mb-4">AI generated Narrative</h2>
            <div class="p-6 bg-yellow-50 border-l-4 border-yellow-500 rounded-r-xl text-gray-800 italic mb-8">
                {profile.story}
            </div>

            <h2 class="text-xl font-bold text-gray-700 mb-4">Column Types Heuristics</h2>
            <div class="border rounded-xl overflow-hidden mb-8">
                <table class="w-full text-left text-sm">
                    <thead class="bg-gray-100 border-b">
                        <tr>
                            <th class="p-4 font-semibold text-gray-700">Column Name</th>
                            <th class="p-4 font-semibold text-gray-700">Type Detected</th>
                            <th class="p-4 font-semibold text-gray-700">Missing Ratio</th>
                            <th class="p-4 font-semibold text-gray-700">Unique Counts</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    for col, stat in profile.statistics.items():
        html_str += f"""
                        <tr class="border-b hover:bg-gray-50">
                            <td class="p-4 font-mono">{col}</td>
                            <td class="p-4 font-bold text-indigo-600">{stat.get('category', 'unknown')}</td>
                            <td class="p-4">{stat.get('missing_pct')}%</td>
                            <td class="p-4">{stat.get('unique_count')}</td>
                        </tr>
        """
    html_str += """
                    </tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_str, headers={"Content-Disposition": f"attachment; filename=profile_{dataset_id}.html"})


@router.get("/export/pdf")
def export_profile_pdf(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Compiles profile statistics to WeasyPrint PDF layout."""
    profile = db.query(DatasetProfile).filter(DatasetProfile.dataset_id == dataset_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

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

    from weasyprint import HTML

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Dataset Profiling PDF Report</title>
        <style>
            @page {{
                size: A4;
                margin: 20mm;
                @bottom-right {{
                    content: "Page " counter(page) " of " counter(pages);
                    font-family: 'Helvetica Neue', Arial, sans-serif;
                    font-size: 8pt;
                    color: #718096;
                }}
            }}
            body {{
                font-family: 'Georgia', serif;
                color: #2d3748;
                line-height: 1.6;
            }}
            h1 {{
                font-family: 'Helvetica Neue', Arial, sans-serif;
                color: #1a365d;
                border-bottom: 2px solid #2b6cb0;
                padding-bottom: 10px;
                text-transform: uppercase;
                letter-spacing: -0.5px;
            }}
            .summary-box {{
                background-color: #ebf8ff;
                border-left: 4px solid #3182ce;
                padding: 15px;
                margin-bottom: 20px;
                border-radius: 0 6px 6px 0;
            }}
            .table-stats {{
                width: 100%;
                border-collapse: collapse;
                font-size: 9pt;
                margin-top: 15px;
            }}
            .table-stats th {{
                background-color: #2b6cb0;
                color: white;
                font-family: 'Helvetica Neue', Arial, sans-serif;
                padding: 6px 8px;
                text-align: left;
                border: 1px solid #cbd5e0;
            }}
            .table-stats td {{
                padding: 6px 8px;
                border: 1px solid #e2e8f0;
            }}
        </style>
    </head>
    <body>
        <h1>Enterprise Data Profile Summary</h1>
        <div class="summary-box">
            <p><strong>Dataset ID:</strong> {profile.dataset_id}</p>
            <p><strong>Total Observations:</strong> {profile.rows:,} Rows &bull; {profile.columns} Columns</p>
            <p><strong>File Size:</strong> {profile.disk / 1024:.1f} KB</p>
        </div>

        <h3>AI Narrative & Recommendations</h3>
        <p>{profile.story}</p>

        <h3>Column Summary</h3>
        <table class="table-stats">
            <thead>
                <tr>
                    <th>Column</th>
                    <th>Type</th>
                    <th>Nulls</th>
                    <th>Unique</th>
                    <th>Mean</th>
                </tr>
            </thead>
            <tbody>
    """
    for col, stat in profile.statistics.items():
        mean_val = stat.get("mean", "N/A")
        html_content += f"""
                <tr>
                    <td style="font-family: monospace;">{col}</td>
                    <td>{stat.get('category', 'unknown')}</td>
                    <td>{stat.get('null_count')} ({stat.get('missing_pct')}%)</td>
                    <td>{stat.get('unique_count')}</td>
                    <td>{mean_val}</td>
                </tr>
        """
    html_content += """
            </tbody>
        </table>
    </body>
    </html>
    """
    try:
        pdf_bytes = HTML(string=html_content).write_pdf()
        import io
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=profile_{dataset_id}.pdf"}
        )
    except Exception as e:
        logger.exception("Failed to compile profile PDF")
        raise HTTPException(status_code=500, detail=f"WeasyPrint compile failed: {e}")
