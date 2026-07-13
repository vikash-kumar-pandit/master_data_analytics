import pytest
import datetime
from datetime import datetime as dt, date
import uuid
from activity_tracker import _infer_action, record_activity, build_activity_summary, track_activity
from catalog import (
    _make_json_serializable,
    register_catalog_entry,
    get_catalog_entry,
    list_catalog_entries_for_user,
    is_catalog_entry_visible
)
from database import SessionLocal
from models import UserActivity, CatalogItem

def test_infer_action():
    assert _infer_action("/upload/file") == "upload"
    assert _infer_action("/api/analytics/query") == "question"
    assert _infer_action("/unknown/path") == "other"


def test_record_activity_options():
    # OPTIONS request should return immediately
    record_activity(
        username="user",
        role="viewer",
        method="OPTIONS",
        path="/upload",
        status_code=200,
        duration_ms=5,
        client_ip="127.0.0.1"
    )
    # Verify no activity recorded
    with SessionLocal() as db:
        act = db.query(UserActivity).filter(UserActivity.username == "user", UserActivity.action == "upload").first()
        assert act is None


def test_activity_tracker_and_summary():
    # Track some activities
    track_activity("user1", "upload", "data.csv", {"status_code": 200})
    track_activity("user2", "clean", "data2.csv", {"status_code": 200})
    track_activity("user1", "question", "insights", {"status_code": 200})

    # Test summary for user1 (non-admin)
    summary_user = build_activity_summary({"username": "user1", "role": "viewer"})
    assert summary_user["summary"]["total_actions_in_period"] >= 2
    # Ensure it only lists user1's activities
    for act in summary_user["recent_activity"]:
        assert act["username"] == "user1"

    # Test summary for admin (lists all activities)
    summary_admin = build_activity_summary({"username": "admin", "role": "admin"})
    assert summary_admin["summary"]["total_actions_in_period"] >= 3
    usernames = {act["username"] for act in summary_admin["recent_activity"]}
    assert "user2" in usernames


def test_make_json_serializable():
    now_dt = dt(2026, 1, 1, 12, 0, 0)
    now_date = date(2026, 1, 2)
    data = {
        "title": "Report",
        "dates": [now_dt, now_date],
        "nested": {"time": now_dt}
    }
    serialized = _make_json_serializable(data)
    assert serialized["dates"][0] == "2026-01-01T12:00:00"
    assert serialized["dates"][1] == "2026-01-02"
    assert serialized["nested"]["time"] == "2026-01-01T12:00:00"


def test_catalog_lifecycle():
    user = {"username": "owner_user", "role": "analyst"}
    admin = {"username": "admin_user", "role": "admin"}
    other = {"username": "other_user", "role": "viewer"}

    # 1. Register entry
    entry = register_catalog_entry(
        action="upload",
        dataset_name="sales.csv",
        analysis={"rows": 100, "cols": 5},
        rows=[{"col1": "val1"}],
        source="upload_api",
        created_by=user,
        ml_results={"r2": 0.85}
    )
    entry_id = entry["id"]
    assert entry_id is not None
    assert entry["name"] == "sales.csv"

    # 2. Get entry
    item = get_catalog_entry(entry_id)
    assert item is not None
    assert item["owner"] == "owner_user"
    assert item["ml_results"] == {"r2": 0.85}

    # Get non-existent
    assert get_catalog_entry("non-existent-id") is None

    # 3. List entries for user
    items_owner = list_catalog_entries_for_user(user)
    assert len(items_owner) >= 1
    for it in items_owner:
        if it["id"] == entry_id:
            assert it["owner"] == "owner_user"

    # List entries for admin
    items_admin = list_catalog_entries_for_user(admin)
    assert len(items_admin) >= 1

    # 4. Visibility rules
    # Visible to owner
    assert is_catalog_entry_visible(item, user) is True
    # Visible to admin
    assert is_catalog_entry_visible(item, admin) is True
    # Invisible to other
    assert is_catalog_entry_visible(item, other) is False
