from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

SCHEDULES_PATH = Path(__file__).resolve().parent / "data" / "scheduled_exports.json"
SCHEDULES_PATH.parent.mkdir(parents=True, exist_ok=True)
SCHEDULE_LOCK = Lock()


def _load_schedules() -> list[dict[str, Any]]:
    if not SCHEDULES_PATH.exists():
        return []
    try:
        return json.loads(SCHEDULES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def _write_schedules(schedules: list[dict[str, Any]]) -> None:
    SCHEDULES_PATH.write_text(json.dumps(schedules, indent=2, default=str), encoding="utf-8")


def create_scheduled_export(
    *,
    name: str,
    description: str | None = None,
    report_config: dict[str, Any],
    schedule_cron: str,
    export_format: str = "pdf",
    recipients: list[str] | None = None,
    enabled: bool = True,
    created_by: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a scheduled export job."""
    # Validate inputs
    if not name or not name.strip():
        raise ValueError("name cannot be empty")
    if not schedule_cron or not schedule_cron.strip():
        raise ValueError("schedule_cron cannot be empty")
    if export_format not in ["pdf", "pptx", "csv", "bundle"]:
        raise ValueError(f"Invalid export_format: {export_format}")
    if not isinstance(report_config, dict):
        raise ValueError("report_config must be a dictionary")
    if recipients:
        for email in recipients:
            if not isinstance(email, str) or "@" not in email:
                raise ValueError(f"Invalid email format: {email}")
    
    schedule_id = str(uuid4())
    
    schedule = {
        "id": schedule_id,
        "name": name.strip(),
        "description": (description or "").strip(),
        "report_config": report_config,
        "schedule_cron": schedule_cron.strip(),  # e.g., "0 9 * * MON" for 9am every Monday
        "export_format": export_format,  # pdf, pptx, csv, bundle
        "recipients": recipients or [],
        "enabled": enabled,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": (created_by or {}).get("username"),
        "last_run": None,
        "next_run": _calculate_next_run(schedule_cron),
        "run_count": 0,
        "last_status": "pending",
    }
    
    with SCHEDULE_LOCK:
        schedules = _load_schedules()
        schedules.append(schedule)
        _write_schedules(schedules)
    
    return {
        "id": schedule_id,
        "name": name,
        "schedule_cron": schedule_cron,
        "next_run": schedule.get("next_run"),
        "status": "created",
    }


def get_schedule(schedule_id: str) -> dict[str, Any] | None:
    """Retrieve a schedule by ID."""
    if not schedule_id or not schedule_id.strip():
        raise ValueError("schedule_id cannot be empty")
    
    with SCHEDULE_LOCK:
        schedules = _load_schedules()
    
    for schedule in schedules:
        if schedule.get("id") == schedule_id:
            return schedule
    
    return None


def list_schedules(username: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    """List schedules, optionally filtered by creator."""
    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100")
    
    with SCHEDULE_LOCK:
        schedules = _load_schedules()
    
    if username:
        if not username.strip():
            raise ValueError("username cannot be empty if provided")
        schedules = [s for s in schedules if s.get("created_by") == username]
    
    return list(reversed(schedules))[:limit]


def update_schedule(schedule_id: str, updates: dict[str, Any]) -> bool:
    """Update a schedule."""
    if not schedule_id or not schedule_id.strip():
        raise ValueError("schedule_id cannot be empty")
    if not isinstance(updates, dict):
        raise ValueError("updates must be a dictionary")
    
    # Validate update values
    if "export_format" in updates and updates["export_format"] not in ["pdf", "pptx", "csv", "bundle"]:
        raise ValueError(f"Invalid export_format: {updates['export_format']}")
    if "recipients" in updates and updates["recipients"]:
        for email in updates["recipients"]:
            if not isinstance(email, str) or "@" not in email:
                raise ValueError(f"Invalid email format: {email}")
    
    with SCHEDULE_LOCK:
        schedules = _load_schedules()
        for schedule in schedules:
            if schedule.get("id") == schedule_id:
                schedule.update(updates)
                _write_schedules(schedules)
                return True
    
    return False


def record_run(schedule_id: str, status: str, message: str = "") -> None:
    """Record a run event."""
    if not schedule_id or not schedule_id.strip():
        raise ValueError("schedule_id cannot be empty")
    if not status or not status.strip():
        raise ValueError("status cannot be empty")
    if status not in ["success", "failed", "pending"]:
        raise ValueError(f"Invalid status: {status}")
    
    with SCHEDULE_LOCK:
        schedules = _load_schedules()
        for schedule in schedules:
            if schedule.get("id") == schedule_id:
                schedule["last_run"] = datetime.now(timezone.utc).isoformat()
                schedule["run_count"] = (schedule.get("run_count") or 0) + 1
                schedule["last_status"] = status
                schedule["next_run"] = _calculate_next_run(schedule.get("schedule_cron", ""))
                _write_schedules(schedules)
                break


def delete_schedule(schedule_id: str, username: str | None = None) -> bool:
    """Delete a schedule."""
    if not schedule_id or not schedule_id.strip():
        raise ValueError("schedule_id cannot be empty")
    
    with SCHEDULE_LOCK:
        schedules = _load_schedules()
        for i, schedule in enumerate(schedules):
            if schedule.get("id") == schedule_id:
                if username and schedule.get("created_by") != username:
                    return False
                schedules.pop(i)
                _write_schedules(schedules)
                return True
    
    return False


def _calculate_next_run(cron_expression: str) -> str:
    """Calculate next run time from cron expression (simplified)."""
    from datetime import timedelta
    
    now = datetime.now(timezone.utc)
    
    # Simplified: parse common patterns like "0 9 * * MON"
    if "MON" in cron_expression:
        # Next Monday at specified hour
        days_ahead = 0 - now.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        next_run = now + timedelta(days=days_ahead)
    elif "daily" in cron_expression.lower() or "* * *" in cron_expression:
        next_run = now + timedelta(days=1)
    else:
        # Default: next day
        next_run = now + timedelta(days=1)
    
    return next_run.isoformat()
