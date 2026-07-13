import os
import io
import json
import zipfile
import logging
from typing import List
from fastapi import APIRouter, Depends, Form, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user
from pipeline_engine.models import Project, PipelineNode
from copilot.routes import _load_active_dataset
from visualization.models import DatasetVisualization
from visualization.service import VisualizationIntelligenceService
import polars as pl

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/visualization", tags=["ai-visualization-intelligence"])


@router.post("/recommend")
def recommend_charts(
    project_id: str = Form(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Scans the active dataset schema and recommends useful visuals grouped by categories."""
    try:
        df = _load_active_dataset(db, project_id)
        service = VisualizationIntelligenceService(df)
        recs = service.recommend_visualizations()
        return recs
    except Exception as e:
        logger.exception("Failed to recommend visualizations")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
def generate_chart(
    project_id: str = Form(...),
    chart_type: str = Form(...),
    columns_json: str = Form(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Generates, stores in DB, and returns a single recommended chart."""
    try:
        columns = json.loads(columns_json)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid columns JSON list.")

    try:
        df = _load_active_dataset(db, project_id)
        service = VisualizationIntelligenceService(df)
        png_b64, svg_b64 = service.generate_chart_image(chart_type, columns)

        # Get default metadata from recommendation rules
        recs = service.recommend_visualizations()
        match = next((r for r in recs if r["chart_type"] == chart_type), None)
        
        value = match["business_value"] if match else 3
        conf = match["confidence"] if match else 80.0
        story = match["story"] if match else "Chart metric overview."
        stats = match["stats_interpretation"] if match else "Linear series plots."
        explanation = match["explanation"] if match else "Rendered plot representation."

        # Save to DB (override existing of same type in project)
        existing = db.query(DatasetVisualization).filter(
            DatasetVisualization.project_id == project_id,
            DatasetVisualization.chart_type == chart_type
        ).first()
        if existing:
            db.delete(existing)
            db.commit()

        new_viz = DatasetVisualization(
            project_id=project_id,
            chart_type=chart_type,
            column_names=columns,
            image_base64=png_b64,
            business_value=value,
            confidence=conf,
            explanation=explanation,
            story=story,
            stats_interpretation=stats
        )
        db.add(new_viz)
        db.commit()
        db.refresh(new_viz)

        return {
            "id": new_viz.id,
            "chart_type": new_viz.chart_type,
            "business_value": new_viz.business_value,
            "confidence": new_viz.confidence,
            "story": new_viz.story,
            "image_base64": new_viz.image_base64
        }
    except Exception as e:
        logger.exception("Failed to generate chart")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-all")
def generate_all_charts(
    project_id: str = Form(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Triggers generation of all recommended visualizations for the project."""
    try:
        df = _load_active_dataset(db, project_id)
        service = VisualizationIntelligenceService(df)
        recs = service.recommend_visualizations()

        generated_ids = []
        for r in recs:
            png_b64, svg_b64 = service.generate_chart_image(r["chart_type"], r["columns"])
            
            existing = db.query(DatasetVisualization).filter(
                DatasetVisualization.project_id == project_id,
                DatasetVisualization.chart_type == r["chart_type"]
            ).first()
            if existing:
                db.delete(existing)
                db.commit()

            new_viz = DatasetVisualization(
                project_id=project_id,
                chart_type=r["chart_type"],
                column_names=r["columns"],
                image_base64=png_b64,
                business_value=r["business_value"],
                confidence=r["confidence"],
                explanation=r["explanation"],
                story=r["story"],
                stats_interpretation=r["stats_interpretation"]
            )
            db.add(new_viz)
            db.commit()
            db.refresh(new_viz)
            generated_ids.append(new_viz.id)

        return {"success": True, "count": len(generated_ids), "ids": generated_ids}
    except Exception as e:
        logger.exception("Failed to generate all charts")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/project/{project_id}")
def get_project_charts(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Retrieves all pre-generated charts for the project workspace."""
    vizs = db.query(DatasetVisualization).filter(DatasetVisualization.project_id == project_id).all()
    return [
        {
            "id": v.id,
            "chart_type": v.chart_type,
            "column_names": v.column_names,
            "image_base64": v.image_base64,
            "business_value": v.business_value,
            "confidence": v.confidence,
            "explanation": v.explanation,
            "story": v.story,
            "stats_interpretation": v.stats_interpretation,
            "created_at": v.created_at
        } for v in vizs
    ]


@router.get("/export")
def export_visualizations(
    project_id: str,
    format: str = "zip",
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Downloads project visualizations as a PPTX presentation or packaged ZIP file."""
    vizs = db.query(DatasetVisualization).filter(DatasetVisualization.project_id == project_id).all()
    if not vizs:
        raise HTTPException(status_code=404, detail="No visualizations generated yet for this project.")

    df = _load_active_dataset(db, project_id)
    service = VisualizationIntelligenceService(df)

    if format == "pptx":
        charts_list = [
            {
                "chart_type": v.chart_type,
                "image_base64": v.image_base64,
                "business_value": v.business_value,
                "confidence": v.confidence,
                "story": v.story,
                "stats_interpretation": v.stats_interpretation
            } for v in vizs
        ]
        pptx_bytes = service.generate_pptx_slideshow(charts_list)
        return StreamingResponse(
            io.BytesIO(pptx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={"Content-Disposition": f"attachment; filename=visuals_storyboard_{project_id}.pptx"}
        )

    elif format == "zip":
        import base64
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            # Write PNGs
            for idx, v in enumerate(vizs):
                img_data = base64.b64decode(v.image_base64)
                zf.writestr(f"png/{idx+1}_{v.chart_type}.png", img_data)

            # Write Standalone HTML Dashboard
            html_str = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>AI Analytics Storyboard</title>
                <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
            </head>
            <body class="bg-gray-50 p-10 font-sans">
                <div class="max-w-6xl mx-auto space-y-8">
                    <h1 class="text-3xl font-black text-indigo-900 border-b pb-4">AI ANALYTICS STORYBOARD</h1>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
            """
            for v in vizs:
                stars = "★" * v.business_value
                html_str += f"""
                        <div class="bg-white p-6 rounded-2xl shadow-md border border-gray-150 flex flex-col gap-4">
                            <h2 class="text-lg font-bold text-gray-800">{v.chart_type.replace('_', ' ').title()}</h2>
                            <img src="data:image/png;base64,{v.image_base64}" class="w-full h-auto rounded-lg" />
                            <div class="text-sm">
                                <p class="text-red-500 font-bold">Business Value: {stars}</p>
                                <p class="text-indigo-600 font-bold mt-1">Confidence: {v.confidence}%</p>
                                <p class="text-gray-600 mt-2 italic">"{v.story}"</p>
                                <p class="text-xs text-gray-400 mt-2">{v.stats_interpretation}</p>
                            </div>
                        </div>
                """
            html_str += """
                    </div>
                </div>
            </body>
            </html>
            """
            zf.writestr("dashboard.html", html_str.encode("utf-8"))

        zip_buffer.seek(0)
        return StreamingResponse(
            zip_buffer,
            media_type="application/x-zip-compressed",
            headers={"Content-Disposition": f"attachment; filename=visuals_package_{project_id}.zip"}
        )

    else:
        raise HTTPException(status_code=400, detail="Unsupported export format. Choose zip or pptx.")
