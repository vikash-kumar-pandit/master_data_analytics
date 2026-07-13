import pytest
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import scheduled_exports
from scheduled_exports import (
    create_scheduled_export, get_schedule, list_schedules,
    update_schedule, record_run, delete_schedule,
    _load_schedules, _calculate_next_run
)

@pytest.fixture(autouse=True)
def setup_temp_schedules_path(tmp_path, monkeypatch):
    # Set a temp directory and temp schedules file for each test
    temp_file = tmp_path / "scheduled_exports.json"
    monkeypatch.setattr(scheduled_exports, "SCHEDULES_PATH", temp_file)
    yield temp_file
    if temp_file.exists():
        temp_file.unlink()

def test_load_schedules_invalid_json(setup_temp_schedules_path):
    temp_file = setup_temp_schedules_path
    temp_file.write_text("invalid-json", encoding="utf-8")
    assert _load_schedules() == []

def test_load_schedules_nonexistent():
    # If the file doesn't exist, should return empty list
    assert _load_schedules() == []

def test_create_scheduled_export_validation():
    # Name validation
    with pytest.raises(ValueError, match="name cannot be empty"):
        create_scheduled_export(name="", report_config={}, schedule_cron="* * * * *")
    
    # Cron validation
    with pytest.raises(ValueError, match="schedule_cron cannot be empty"):
        create_scheduled_export(name="Export", report_config={}, schedule_cron="")
        
    # Format validation
    with pytest.raises(ValueError, match="Invalid export_format"):
        create_scheduled_export(name="Export", report_config={}, schedule_cron="* * * * *", export_format="invalid")
        
    # Config validation
    with pytest.raises(ValueError, match="report_config must be a dictionary"):
        create_scheduled_export(name="Export", report_config="not a dict", schedule_cron="* * * * *")
        
    # Recipients validation
    with pytest.raises(ValueError, match="Invalid email format"):
        create_scheduled_export(name="Export", report_config={}, schedule_cron="* * * * *", recipients=["invalid-email"])

def test_create_scheduled_export_success():
    res = create_scheduled_export(
        name="Weekly Report",
        description="Weekly analytics backup",
        report_config={"project_id": "123"},
        schedule_cron="0 0 * * 0",
        export_format="pdf",
        recipients=["test@example.com"],
        created_by={"username": "user123"}
    )
    
    assert res["name"] == "Weekly Report"
    assert res["status"] == "created"
    
    # Load and verify
    jobs = _load_schedules()
    assert len(jobs) == 1
    assert jobs[0]["name"] == "Weekly Report"
    assert jobs[0]["export_format"] == "pdf"
    assert jobs[0]["enabled"] is True
    assert jobs[0]["created_by"] == "user123"

def test_get_schedule_validation():
    with pytest.raises(ValueError, match="schedule_id cannot be empty"):
        get_schedule("")

def test_get_schedule_not_found():
    assert get_schedule("nonexistent-id") is None

def test_get_schedule_success():
    res = create_scheduled_export(name="Report", report_config={}, schedule_cron="* * * * *")
    retrieved = get_schedule(res["id"])
    assert retrieved is not None
    assert retrieved["name"] == "Report"

def test_list_schedules():
    with pytest.raises(ValueError, match="limit must be between 1 and 100"):
        list_schedules(limit=0)
    with pytest.raises(ValueError, match="limit must be between 1 and 100"):
        list_schedules(limit=101)
        
    # Empty
    assert list_schedules() == []
    
    create_scheduled_export(name="R1", report_config={}, schedule_cron="* * * * *", created_by={"username": "user_a"})
    create_scheduled_export(name="R2", report_config={}, schedule_cron="* * * * *", created_by={"username": "user_a"})
    create_scheduled_export(name="R3", report_config={}, schedule_cron="* * * * *", created_by={"username": "user_b"})
    
    # Check listing all
    all_scheds = list_schedules()
    assert len(all_scheds) == 3
    assert all_scheds[0]["name"] == "R3" # Reversed
    
    # Filter by user
    user_a_scheds = list_schedules(username="user_a")
    assert len(user_a_scheds) == 2
    assert user_a_scheds[0]["name"] == "R2"
    
    # Empty user validation
    with pytest.raises(ValueError, match="username cannot be empty"):
        list_schedules(username=" ")

def test_update_schedule():
    with pytest.raises(ValueError, match="schedule_id cannot be empty"):
        update_schedule("", {})
    with pytest.raises(ValueError, match="updates must be a dictionary"):
        update_schedule("id", "not a dict")
        
    res = create_scheduled_export(name="Report", report_config={}, schedule_cron="* * * * *")
    sched_id = res["id"]
    
    # Invalid updates validation
    with pytest.raises(ValueError, match="Invalid export_format"):
        update_schedule(sched_id, {"export_format": "invalid"})
    with pytest.raises(ValueError, match="Invalid email format"):
        update_schedule(sched_id, {"recipients": ["invalid"]})
        
    # Valid update
    assert update_schedule(sched_id, {"name": "Updated Report", "export_format": "pptx"}) is True
    sched = get_schedule(sched_id)
    assert sched["name"] == "Updated Report"
    assert sched["export_format"] == "pptx"
    
    # Update nonexistent
    assert update_schedule("nonexistent-id", {"name": "test"}) is False

def test_record_run():
    with pytest.raises(ValueError, match="schedule_id cannot be empty"):
        record_run("", "success")
    with pytest.raises(ValueError, match="status cannot be empty"):
        record_run("id", "")
    with pytest.raises(ValueError, match="Invalid status"):
        record_run("id", "invalid")
        
    res = create_scheduled_export(name="Report", report_config={}, schedule_cron="* * * * *")
    sched_id = res["id"]
    
    record_run(sched_id, "success", "All good")
    sched = get_schedule(sched_id)
    assert sched["run_count"] == 1
    assert sched["last_status"] == "success"
    assert sched["last_run"] is not None

def test_delete_schedule():
    with pytest.raises(ValueError, match="schedule_id cannot be empty"):
        delete_schedule("")
        
    res = create_scheduled_export(name="Report", report_config={}, schedule_cron="* * * * *", created_by={"username": "user_a"})
    sched_id = res["id"]
    
    # Wrong user deletion
    assert delete_schedule(sched_id, username="user_b") is False
    assert get_schedule(sched_id) is not None
    
    # Correct user deletion
    assert delete_schedule(sched_id, username="user_a") is True
    assert get_schedule(sched_id) is None
    
    # Nonexistent deletion
    assert delete_schedule("nonexistent-id") is False

def test_calculate_next_run():
    # Predictive MON cron
    res_mon = _calculate_next_run("0 9 * * MON")
    assert res_mon is not None
    
    # daily cron
    res_daily = _calculate_next_run("daily")
    assert res_daily is not None
    
    # wildcard cron
    res_wildcard = _calculate_next_run("* * * * *")
    assert res_wildcard is not None
