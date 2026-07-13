from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from database import SessionLocal
from models import CatalogItem
from schemas import CompareRequest

router = APIRouter()

@router.post("/compare")
async def compare_models(request: CompareRequest):
    if len(request.model_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 models are required for comparison")

    with SessionLocal() as db:
        items = db.query(CatalogItem).filter(CatalogItem.id.in_(request.model_ids)).all()

        if not items:
            raise HTTPException(status_code=404, detail="Models not found")

        comparison_data = []
        for item in items:
            ml = item.ml_results or {}
            comparison_data.append({
                "id": item.id,
                "name": item.name,
                "type": item.type,
                "owner": item.owner,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "algorithm": ml.get("algorithm") or ml.get("best_algorithm") or item.summary.get("best_algorithm") or "N/A",
                "accuracy": ml.get("accuracy"),
                "r2": ml.get("r2"),
                "metrics": ml.get("metrics", {}),
                "confusion_matrix": ml.get("confusion_matrix"),
                "feature_importance": ml.get("feature_importance"),
                "classification_report": ml.get("classification_report"),
            })

    return {"comparison": comparison_data}

@router.get("/leaderboard")
async def get_leaderboard(limit: int = 10):
    with SessionLocal() as db:
        items = db.query(CatalogItem).filter(CatalogItem.type == "automl").order_by(CatalogItem.created_at.desc()).limit(limit).all()

        leaderboard = []
        for item in items:
            ml = item.ml_results or {}
            acc = ml.get("accuracy")
            if acc is not None:
                try:
                    acc = float(acc)
                except (TypeError, ValueError):
                    acc = None

            leaderboard.append({
                "id": item.id,
                "name": item.name,
                "algorithm": ml.get("algorithm") or ml.get("best_algorithm") or "N/A",
                "accuracy": acc,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            })

        leaderboard.sort(key=lambda x: (x["accuracy"] is not None, x["accuracy"] or 0), reverse=True)

    return {"leaderboard": leaderboard}
