from fastapi import APIRouter, Depends, HTTPException
from schemas import CreateScheduleRequest
from auth import require_role
from scheduled_exports import create_scheduled_export, get_schedule, list_schedules, delete_schedule
from catalog import register_catalog_entry

router = APIRouter()

@router.post("/api/schedule/create")
async def create_schedule(
    payload: CreateScheduleRequest,
    current_user: dict = Depends(require_role(["analyst", "admin"])),
):
    try:
        payload.validate_inputs()
        
        schedule = create_scheduled_export(
            name=payload.name,
            description=payload.description,
            report_config=payload.report_config,
            schedule_cron=payload.schedule_cron,
            export_format=payload.export_format,
            recipients=payload.recipients,
            enabled=payload.enabled,
            created_by=current_user,
        )
        register_catalog_entry(
            action="schedule",
            dataset_name=payload.name,
            analysis={"cron": payload.schedule_cron, "format": payload.export_format},
            rows=[],
            source="scheduled_export",
            created_by=current_user,
        )
        return schedule
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to create schedule: {str(exc)}")


@router.get("/api/schedule/my-schedules")
async def list_my_schedules(
    current_user: dict = Depends(require_role(["analyst", "admin"])),
):
    try:
        username = current_user.get("username")
        if not username:
            raise HTTPException(status_code=400, detail="User must be authenticated")
        
        schedules = list_schedules(username, limit=20)
        return {
            "schedules": [
                {
                    "id": s.get("id"),
                    "name": s.get("name"),
                    "schedule_cron": s.get("schedule_cron"),
                    "export_format": s.get("export_format"),
                    "enabled": s.get("enabled"),
                    "last_run": s.get("last_run"),
                    "next_run": s.get("next_run"),
                    "run_count": s.get("run_count"),
                    "last_status": s.get("last_status"),
                }
                for s in schedules
            ]
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to list schedules: {str(exc)}")


@router.get("/api/schedule/{schedule_id}")
async def get_schedule_endpoint(
    schedule_id: str,
    current_user: dict = Depends(require_role(["analyst", "admin"])),
):
    try:
        if not schedule_id or not schedule_id.strip():
            raise HTTPException(status_code=400, detail="schedule_id cannot be empty")
        
        schedule = get_schedule(schedule_id)
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found.")
        if schedule.get("created_by") != current_user.get("username"):
            raise HTTPException(status_code=403, detail="Not authorized to view this schedule.")
        return schedule
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to get schedule: {str(exc)}")


@router.delete("/api/schedule/{schedule_id}")
async def delete_schedule_endpoint(
    schedule_id: str,
    current_user: dict = Depends(require_role(["analyst", "admin"])),
):
    try:
        if not schedule_id or not schedule_id.strip():
            raise HTTPException(status_code=400, detail="schedule_id cannot be empty")
        
        username = current_user.get("username")
        success = delete_schedule(schedule_id, username)
        if not success:
            raise HTTPException(status_code=403, detail="Not authorized to delete this schedule.")
        return {"status": "deleted"}
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to delete schedule: {str(exc)}")
