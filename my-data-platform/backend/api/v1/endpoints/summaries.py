from fastapi import APIRouter, Depends, HTTPException
from schemas import ExecutiveSummaryRequest
from auth import require_role
from activity_tracker import build_activity_summary
from dashboard_summary import build_dashboard_summary, build_dashboard_trends
from executive_summary import generate_executive_summary
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/api/activity/summary")
async def get_activity_summary(
    days: int = 30,
    recent_limit: int = 20,
    current_user: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    try:
        return build_activity_summary(
            current_user=current_user,
            days=max(1, min(days, 365)),
            recent_limit=max(5, min(recent_limit, 100)),
        )
    except Exception as exc:
        logger.exception("Failed to build activity summary: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve activity summary. Please try again later."
        )


@router.get("/api/dashboard/summary")
async def get_dashboard_summary_endpoint(
    days: int = 30,
    recent_limit: int = 12,
    catalog_limit: int = 20,
    current_user: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    try:
        return build_dashboard_summary(
            current_user=current_user,
            days=days,
            recent_limit=recent_limit,
            catalog_limit=catalog_limit,
        )
    except Exception as exc:
        logger.exception("Failed to build dashboard summary: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve dashboard summary. Please try again later."
        )


@router.get("/api/dashboard/trends")
async def get_dashboard_trends_endpoint(
    window_days: int = 7,
    current_user: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    try:
        return build_dashboard_trends(
            current_user=current_user,
            window_days=window_days,
        )
    except Exception as exc:
        logger.exception("Failed to build dashboard trends: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve dashboard trends. Please try again later."
        )


@router.post("/api/summary/executive")
async def generate_summary(
    payload: ExecutiveSummaryRequest,
    current_user: dict = Depends(require_role(["viewer", "analyst", "admin"])),
):
    try:
        payload.validate_inputs()
        
        summary = generate_executive_summary(analysis=payload.analysis, result=payload.result)
        return summary
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(exc)}")


@router.get("/api/admin-stats")
async def admin_stats(_: dict = Depends(require_role(["admin"]))):
    try:
        return {
            "status": "ok",
            "message": "Welcome Admin",
            "capabilities": ["user_management", "system_configuration", "audit_access"],
        }
    except Exception as exc:
        logger.exception("Admin stats check failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve admin statistics."
        )
