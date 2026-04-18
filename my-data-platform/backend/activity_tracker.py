from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

ACTIVITY_PATH = Path(__file__).resolve().parent / "data" / "activity_log.json"
ACTIVITY_PATH.parent.mkdir(parents=True, exist_ok=True)
ACTIVITY_LOCK = Lock()

ACTION_MAP = {
    "/upload": "upload",
    "/clean": "clean",
    "/arrange": "arrange",
    "/api/analytics/query": "question",
    "/api/analytics/forecast": "forecast",
    "/api/analytics/compare": "compare",
    "/api/analytics/report": "report",
    "/automl": "automl",
    "/api/clean-background": "clean_background",
    "/api/predict-background": "predict_background",
    "/generate-insights": "insights",
    "/api/export-results": "export",
    "/api/explain-automl": "explainability",
    "/api/run-clustering": "clustering",
    "/api/apply-nlp": "nlp",
    "/api/workflows": "workflow",
    "/api/catalog": "catalog",
}

ACTION_WEIGHTS = {
    "upload": 1,
    "clean": 2,
    "arrange": 2,
    "question": 2,
    "forecast": 3,
    "compare": 2,
    "report": 1,
    "clean_background": 2,
    "automl": 4,
    "predict_background": 4,
    "insights": 2,
    "export": 1,
    "explainability": 3,
    "clustering": 3,
    "nlp": 3,
    "workflow": 5,
    "catalog": 1,
    "other": 1,
}


def _load_activity() -> list[dict[str, Any]]:
    if not ACTIVITY_PATH.exists():
        return []
    try:
        return json.loads(ACTIVITY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def _write_activity(entries: list[dict[str, Any]]) -> None:
    ACTIVITY_PATH.write_text(json.dumps(entries, indent=2, default=str), encoding="utf-8")


def _infer_action(path: str) -> str:
    for prefix, action in ACTION_MAP.items():
        if path.startswith(prefix):
            return action
    return "other"


def _score_work(action: str, status_code: int) -> int:
    base = ACTION_WEIGHTS.get(action, 1)
    if status_code >= 400:
        return 0
    return base


def record_activity(
    *,
    username: str | None,
    role: str | None,
    method: str,
    path: str,
    status_code: int,
    duration_ms: int,
    client_ip: str,
) -> None:
    if method == "OPTIONS":
        return

    action = _infer_action(path)
    entry = {
        "id": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "username": username or "anonymous",
        "role": role or "guest",
        "method": method,
        "path": path,
        "action": action,
        "status_code": int(status_code),
        "duration_ms": int(duration_ms),
        "client_ip": client_ip,
        "work_units": _score_work(action, status_code),
    }

    with ACTIVITY_LOCK:
        entries = _load_activity()
        entries.append(entry)
        # Keep file bounded for local usage.
        if len(entries) > 10000:
            entries = entries[-10000:]
        _write_activity(entries)


def _parse_timestamp(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _filter_entries(entries: list[dict[str, Any]], *, days: int) -> list[dict[str, Any]]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(days, 1))
    filtered: list[dict[str, Any]] = []
    for entry in entries:
        ts = _parse_timestamp(str(entry.get("timestamp") or ""))
        if not ts:
            continue
        if ts >= cutoff:
            filtered.append(entry)
    return filtered


def build_activity_summary(*, current_user: dict[str, Any], days: int = 30, recent_limit: int = 20) -> dict[str, Any]:
    with ACTIVITY_LOCK:
        entries = _load_activity()

    filtered = _filter_entries(entries, days=days)
    is_admin = current_user.get("role") == "admin"
    visible_entries = filtered if is_admin else [
        entry for entry in filtered if entry.get("username") == current_user.get("username")
    ]

    role_counter: dict[str, dict[str, Any]] = {}
    user_counter: dict[str, dict[str, Any]] = {}
    daily_counter: dict[str, dict[str, Any]] = {}

    for entry in visible_entries:
        role = str(entry.get("role") or "guest")
        username = str(entry.get("username") or "anonymous")
        status_code = int(entry.get("status_code") or 0)
        duration_ms = int(entry.get("duration_ms") or 0)
        work_units = int(entry.get("work_units") or 0)
        action = str(entry.get("action") or "other")
        timestamp = str(entry.get("timestamp") or "")
        day_key = timestamp.split("T", 1)[0] if "T" in timestamp else timestamp

        role_bucket = role_counter.setdefault(
            role,
            {
                "role": role,
                "total_requests": 0,
                "successful_requests": 0,
                "duration_total_ms": 0,
                "work_units": 0,
                "last_activity_at": None,
                "actions": Counter(),
            },
        )
        role_bucket["total_requests"] += 1
        role_bucket["duration_total_ms"] += duration_ms
        role_bucket["work_units"] += work_units
        role_bucket["actions"][action] += 1
        if status_code < 400:
            role_bucket["successful_requests"] += 1
        if not role_bucket["last_activity_at"] or timestamp > role_bucket["last_activity_at"]:
            role_bucket["last_activity_at"] = timestamp

        user_bucket = user_counter.setdefault(
            username,
            {
                "username": username,
                "role": role,
                "total_requests": 0,
                "successful_requests": 0,
                "work_units": 0,
                "last_activity_at": None,
                "actions": Counter(),
            },
        )
        user_bucket["total_requests"] += 1
        user_bucket["work_units"] += work_units
        user_bucket["actions"][action] += 1
        if status_code < 400:
            user_bucket["successful_requests"] += 1
        if not user_bucket["last_activity_at"] or timestamp > user_bucket["last_activity_at"]:
            user_bucket["last_activity_at"] = timestamp

        day_bucket = daily_counter.setdefault(day_key, {"date": day_key, "total_requests": 0, "work_units": 0})
        day_bucket["total_requests"] += 1
        day_bucket["work_units"] += work_units

    role_items = []
    for role_bucket in role_counter.values():
        total_requests = max(int(role_bucket["total_requests"]), 1)
        role_items.append(
            {
                "role": role_bucket["role"],
                "total_requests": role_bucket["total_requests"],
                "successful_requests": role_bucket["successful_requests"],
                "avg_duration_ms": int(role_bucket["duration_total_ms"] / total_requests),
                "work_units": role_bucket["work_units"],
                "last_activity_at": role_bucket["last_activity_at"],
                "top_actions": role_bucket["actions"].most_common(4),
            }
        )

    user_items = []
    for user_bucket in user_counter.values():
        user_items.append(
            {
                "username": user_bucket["username"],
                "role": user_bucket["role"],
                "total_requests": user_bucket["total_requests"],
                "successful_requests": user_bucket["successful_requests"],
                "work_units": user_bucket["work_units"],
                "last_activity_at": user_bucket["last_activity_at"],
                "top_actions": user_bucket["actions"].most_common(4),
            }
        )

    user_items.sort(key=lambda item: (item["work_units"], item["total_requests"]), reverse=True)
    role_items.sort(key=lambda item: item["work_units"], reverse=True)

    visible_entries.sort(key=lambda entry: str(entry.get("timestamp") or ""), reverse=True)
    recent_entries = visible_entries[: max(1, min(recent_limit, 100))]

    current_username = current_user.get("username")
    current_stats = next((item for item in user_items if item["username"] == current_username), None)
    if not current_stats:
        current_stats = {
            "username": current_username,
            "role": current_user.get("role"),
            "total_requests": 0,
            "successful_requests": 0,
            "work_units": 0,
            "last_activity_at": None,
            "top_actions": [],
        }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "days": max(days, 1),
        "scope": "all_users" if is_admin else "self",
        "current_user": current_stats,
        "roles": role_items,
        "users": user_items,
        "daily": sorted(daily_counter.values(), key=lambda item: item["date"]),
        "recent": recent_entries,
    }
