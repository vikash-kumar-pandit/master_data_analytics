from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from activity_tracker import build_activity_summary
from catalog import list_catalog_entries_for_user


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _latest_entry_with_data(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    for entry in entries:
        summary = entry.get("summary") or {}
        if _safe_int(summary.get("rows")) > 0:
            return entry
    return entries[0] if entries else None


def _compute_quality_metrics(latest_entry: dict[str, Any] | None) -> dict[str, Any]:
    if not latest_entry:
        return {
            "score": 0,
            "grade": "N/A",
            "audit_issues": 0,
            "null_cells": 0,
            "duplicate_rows": 0,
        }

    analysis = latest_entry.get("analysis") or {}
    rows = _safe_int((latest_entry.get("summary") or {}).get("rows"))
    audit_errors = analysis.get("audit_errors") or []
    null_counts = (analysis.get("null_counts") or [{}])[0] if analysis.get("null_counts") else {}

    null_cells = sum(_safe_int(value) for value in (null_counts or {}).values())
    duplicate_rows = sum(1 for issue in audit_errors if "duplicate" in str(issue.get("issue") or "").lower())
    audit_issues = len(audit_errors)

    if rows <= 0:
        score = 0
    else:
        issue_ratio = audit_issues / max(rows, 1)
        null_ratio = null_cells / max(rows, 1)
        score = round(100 - min(85, (issue_ratio * 180) + (null_ratio * 12)))
        score = max(5, min(score, 100))

    if score >= 85:
        grade = "Excellent"
    elif score >= 70:
        grade = "Good"
    elif score >= 50:
        grade = "Fair"
    elif score > 0:
        grade = "Poor"
    else:
        grade = "N/A"

    return {
        "score": score,
        "grade": grade,
        "audit_issues": audit_issues,
        "null_cells": null_cells,
        "duplicate_rows": duplicate_rows,
    }


def _build_processing_history(
    *,
    activity_daily: list[dict[str, Any]],
    catalog_entries: list[dict[str, Any]],
    days: int,
) -> list[dict[str, Any]]:
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=max(days, 1) - 1)

    date_map: dict[str, dict[str, Any]] = {}
    for offset in range(max(days, 1)):
        day_key = (start_date + timedelta(days=offset)).isoformat()
        date_map[day_key] = {
            "date": day_key,
            "work_units": 0,
            "total_requests": 0,
            "saved_runs": 0,
        }

    for item in activity_daily:
        day_key = str(item.get("date") or "")
        if day_key in date_map:
            date_map[day_key]["work_units"] = _safe_int(item.get("work_units"))
            date_map[day_key]["total_requests"] = _safe_int(item.get("total_requests"))

    for entry in catalog_entries:
        created_at = _parse_iso(str(entry.get("created_at") or ""))
        if not created_at:
            continue
        day_key = created_at.date().isoformat()
        if day_key in date_map:
            date_map[day_key]["saved_runs"] += 1

    return list(date_map.values())


def _build_recent_runs(entries: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for entry in entries[: max(1, limit)]:
        summary = entry.get("summary") or {}
        items.append(
            {
                "id": entry.get("id"),
                "dataset_name": entry.get("dataset_name") or "Untitled Dataset",
                "action": entry.get("action") or "other",
                "created_at": entry.get("created_at"),
                "owner": (entry.get("created_by") or {}).get("username"),
                "summary": {
                    "rows": _safe_int(summary.get("rows")),
                    "cols": _safe_int(summary.get("cols")),
                    "domain": summary.get("domain") or "Unknown",
                },
            }
        )
    return items


def _build_audit_report(latest_entry: dict[str, Any] | None, limit: int) -> list[dict[str, Any]]:
    if not latest_entry:
        return []

    audit_errors = (latest_entry.get("analysis") or {}).get("audit_errors") or []
    report: list[dict[str, Any]] = []
    for issue in audit_errors[: max(1, limit)]:
        report.append(
            {
                "row": _safe_int(issue.get("row")),
                "col": issue.get("col") or "",
                "issue": issue.get("issue") or "Unknown issue",
                "severity": issue.get("severity") or "Medium",
            }
        )
    return report


def build_dashboard_summary(
    *,
    current_user: dict[str, Any],
    days: int = 30,
    recent_limit: int = 12,
    catalog_limit: int = 20,
) -> dict[str, Any]:
    bounded_days = max(1, min(days, 365))
    bounded_recent = max(1, min(recent_limit, 100))
    bounded_catalog = max(1, min(catalog_limit, 200))

    activity = build_activity_summary(
        current_user=current_user,
        days=bounded_days,
        recent_limit=bounded_recent,
    )
    catalog_entries = list_catalog_entries_for_user(current_user, limit=bounded_catalog)
    latest_entry = _latest_entry_with_data(catalog_entries)
    latest_summary = (latest_entry or {}).get("summary") or {}

    quality = _compute_quality_metrics(latest_entry)
    processing_history = _build_processing_history(
        activity_daily=activity.get("daily") or [],
        catalog_entries=catalog_entries,
        days=min(bounded_days, 30),
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": activity.get("scope"),
        "workspace": {
            "rows_loaded": _safe_int(latest_summary.get("rows")),
            "columns": _safe_int(latest_summary.get("cols")),
            "audit_issues": quality.get("audit_issues", 0),
            "saved_runs": len(catalog_entries),
            "latest_dataset_name": (latest_entry or {}).get("dataset_name") if latest_entry else None,
            "latest_action": (latest_entry or {}).get("action") if latest_entry else None,
            "latest_updated_at": (latest_entry or {}).get("created_at") if latest_entry else None,
        },
        "data_quality": quality,
        "processing_history": processing_history,
        "activity": activity,
        "recent_runs": _build_recent_runs(catalog_entries, bounded_recent),
        "audit_report": _build_audit_report(latest_entry, limit=25),
    }


def build_dashboard_trends(*, current_user: dict[str, Any], window_days: int = 7) -> dict[str, Any]:
    bounded_window = max(3, min(window_days, 90))
    span_days = bounded_window * 2

    activity = build_activity_summary(
        current_user=current_user,
        days=span_days,
        recent_limit=100,
    )
    catalog_entries = list_catalog_entries_for_user(current_user, limit=200)

    daily = activity.get("daily") or []
    recent_daily = daily[-bounded_window:]
    previous_daily = daily[-(bounded_window * 2):-bounded_window]

    def _sum(entries: list[dict[str, Any]], key: str) -> int:
        return sum(_safe_int(item.get(key)) for item in entries)

    current_requests = _sum(recent_daily, "total_requests")
    previous_requests = _sum(previous_daily, "total_requests")
    current_work_units = _sum(recent_daily, "work_units")
    previous_work_units = _sum(previous_daily, "work_units")

    def _delta(current: int, previous: int) -> dict[str, Any]:
        diff = current - previous
        pct_change = round((diff / previous) * 100, 2) if previous > 0 else (100.0 if current > 0 else 0.0)
        return {
            "current": current,
            "previous": previous,
            "diff": diff,
            "pct_change": pct_change,
        }

    action_mix: dict[str, int] = {}
    for entry in (activity.get("recent") or []):
        action = str(entry.get("action") or "other")
        action_mix[action] = action_mix.get(action, 0) + 1

    catalog_action_mix: dict[str, int] = {}
    for entry in catalog_entries:
        action = str(entry.get("action") or "other")
        catalog_action_mix[action] = catalog_action_mix.get(action, 0) + 1

    trend_points = [
        {
            "date": item.get("date"),
            "requests": _safe_int(item.get("total_requests")),
            "work_units": _safe_int(item.get("work_units")),
        }
        for item in recent_daily
    ]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": activity.get("scope"),
        "window_days": bounded_window,
        "requests": _delta(current_requests, previous_requests),
        "work_units": _delta(current_work_units, previous_work_units),
        "top_actions": sorted(action_mix.items(), key=lambda pair: pair[1], reverse=True)[:8],
        "catalog_action_mix": sorted(catalog_action_mix.items(), key=lambda pair: pair[1], reverse=True)[:8],
        "daily": trend_points,
    }
