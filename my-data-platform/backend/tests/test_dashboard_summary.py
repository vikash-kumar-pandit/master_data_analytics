import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from dashboard_summary import (
    _safe_int, _parse_iso, _latest_entry_with_data,
    _compute_quality_metrics, _build_processing_history,
    _build_recent_runs, _build_audit_report,
    build_dashboard_summary, build_dashboard_trends
)

def test_helpers():
    # _safe_int
    assert _safe_int(123) == 123
    assert _safe_int("456") == 456
    assert _safe_int("abc") == 0
    assert _safe_int(None) == 0
    
    # _parse_iso
    assert _parse_iso(None) is None
    assert _parse_iso("invalid") is None
    dt = _parse_iso("2026-07-13T12:00:00")
    assert isinstance(dt, datetime)
    assert dt.year == 2026

    # _latest_entry_with_data
    assert _latest_entry_with_data([]) is None
    entry_empty = {"summary": {"rows": 0}}
    entry_with_rows = {"summary": {"rows": 100}}
    assert _latest_entry_with_data([entry_empty, entry_with_rows]) == entry_with_rows
    assert _latest_entry_with_data([entry_empty]) == entry_empty


def test_compute_quality_metrics():
    # None entry
    res = _compute_quality_metrics(None)
    assert res["score"] == 0
    assert res["grade"] == "N/A"
    
    # Empty summary / 0 rows
    res_zero = _compute_quality_metrics({"summary": {"rows": 0}})
    assert res_zero["score"] == 0
    assert res_zero["grade"] == "N/A"
    
    # Good quality
    latest = {
        "summary": {"rows": 1000},
        "analysis": {
            "audit_errors": [
                {"issue": "duplicate row found"},
                {"issue": "missing column value"}
            ],
            "null_counts": [{"col1": 5, "col2": 10}]
        }
    }
    res_good = _compute_quality_metrics(latest)
    assert res_good["score"] > 0
    assert res_good["audit_issues"] == 2
    assert res_good["duplicate_rows"] == 1
    assert res_good["null_cells"] == 15
    
    # Excellent quality (no issues)
    res_exc = _compute_quality_metrics({"summary": {"rows": 100}, "analysis": {}})
    assert res_exc["score"] == 100
    assert res_exc["grade"] == "Excellent"


def test_build_processing_history():
    activity_daily = [
        {"date": "2026-07-10", "work_units": 10, "total_requests": 50},
        {"date": "2026-07-11", "work_units": 20, "total_requests": 80}
    ]
    catalog_entries = [
        {"created_at": "2026-07-10T12:00:00"},
        {"created_at": "2026-07-10T15:00:00"}
    ]
    
    # We patch datetime in the function or pass values. 
    # Let's mock datetime.now to return a fixed date to keep test stable.
    fixed_now = datetime(2026, 7, 12, tzinfo=timezone.utc)
    with patch("dashboard_summary.datetime") as mock_dt:
        mock_dt.now.return_value = fixed_now
        mock_dt.fromisoformat.side_effect = datetime.fromisoformat
        
        history = _build_processing_history(
            activity_daily=activity_daily,
            catalog_entries=catalog_entries,
            days=3
        )
        
        # 3 days: 2026-07-10, 2026-07-11, 2026-07-12
        assert len(history) == 3
        # 2026-07-10 has 10 work_units, 50 requests, 2 saved runs
        h10 = [h for h in history if h["date"] == "2026-07-10"][0]
        assert h10["work_units"] == 10
        assert h10["total_requests"] == 50
        assert h10["saved_runs"] == 2


def test_build_recent_runs():
    entries = [
        {
            "id": "e1",
            "dataset_name": "DS1",
            "action": "clean",
            "created_at": "2026-07-10T12:00:00",
            "created_by": {"username": "alice"},
            "summary": {"rows": 100, "cols": 5, "domain": "sales"}
        }
    ]
    res = _build_recent_runs(entries, limit=5)
    assert len(res) == 1
    assert res[0]["dataset_name"] == "DS1"
    assert res[0]["owner"] == "alice"
    assert res[0]["summary"]["domain"] == "sales"
    
    # empty/default checks
    res_empty = _build_recent_runs([{}], limit=5)
    assert res_empty[0]["dataset_name"] == "Untitled Dataset"
    assert res_empty[0]["owner"] is None


def test_build_audit_report():
    assert _build_audit_report(None, 5) == []
    
    latest = {
        "analysis": {
            "audit_errors": [
                {"row": 5, "col": "c1", "issue": "Missing", "severity": "High"}
            ]
        }
    }
    report = _build_audit_report(latest, 5)
    assert len(report) == 1
    assert report[0]["row"] == 5
    assert report[0]["issue"] == "Missing"


@patch("dashboard_summary.build_activity_summary")
@patch("dashboard_summary.list_catalog_entries_for_user")
def test_build_dashboard_summary(mock_list_catalog, mock_build_activity):
    mock_build_activity.return_value = {
        "scope": "user",
        "daily": [{"date": "2026-07-12", "work_units": 5, "total_requests": 10}]
    }
    mock_list_catalog.return_value = [
        {
            "id": "1",
            "dataset_name": "D1",
            "action": "profile",
            "created_at": "2026-07-12T12:00:00",
            "summary": {"rows": 10, "cols": 2}
        }
    ]
    
    user = {"username": "test_user"}
    res = build_dashboard_summary(current_user=user, days=5, recent_limit=5, catalog_limit=5)
    
    assert res["scope"] == "user"
    assert res["workspace"]["rows_loaded"] == 10
    assert res["workspace"]["saved_runs"] == 1
    assert len(res["processing_history"]) > 0


@patch("dashboard_summary.build_activity_summary")
@patch("dashboard_summary.list_catalog_entries_for_user")
def test_build_dashboard_trends(mock_list_catalog, mock_build_activity):
    # Mocking activity summary daily data: 14 points
    daily_data = [
        {"date": f"2026-07-{i:02d}", "work_units": 10, "total_requests": 20}
        for i in range(1, 15)
    ]
    mock_build_activity.return_value = {
        "scope": "global",
        "daily": daily_data,
        "recent": [{"action": "profile"}, {"action": "clean"}]
    }
    mock_list_catalog.return_value = [{"action": "profile"}]
    
    user = {"username": "test_user"}
    res = build_dashboard_trends(current_user=user, window_days=7)
    
    assert res["scope"] == "global"
    assert res["window_days"] == 7
    assert "requests" in res
    assert res["requests"]["current"] == 140
    assert res["requests"]["previous"] == 140
    assert res["requests"]["pct_change"] == 0.0
    
    assert len(res["top_actions"]) == 2
    assert res["top_actions"][0][0] == "profile"
