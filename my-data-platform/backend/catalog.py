from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

CATALOG_PATH = Path(__file__).resolve().parent / "data" / "catalog.json"
CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
CATALOG_LOCK = Lock()


def _load_catalog() -> list[dict[str, Any]]:
    if not CATALOG_PATH.exists():
        return []

    try:
        return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def _write_catalog(entries: list[dict[str, Any]]) -> None:
    CATALOG_PATH.write_text(json.dumps(entries, indent=2, default=str), encoding="utf-8")


def make_dataset_fingerprint(rows: list[dict[str, Any]] | None, metadata: dict[str, Any] | None = None) -> str:
    payload = {
        "rows": rows[:5] if rows else [],
        "metadata": metadata or {},
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return digest


def register_catalog_entry(
    *,
    action: str,
    dataset_name: str | None,
    analysis: dict[str, Any] | None = None,
    cleaning_stats: list[dict[str, Any]] | None = None,
    ml_results: dict[str, Any] | None = None,
    rows: list[dict[str, Any]] | None = None,
    target_column: str | None = None,
    source: str | None = None,
    created_by: dict[str, Any] | None = None,
) -> dict[str, Any]:
    analysis = analysis or {}
    actor = {
        "username": (created_by or {}).get("username"),
        "role": (created_by or {}).get("role"),
    }
    metadata = {
        "action": action,
        "dataset_name": dataset_name,
        "rows": analysis.get("rows") or (len(rows) if rows else 0),
        "cols": analysis.get("cols") or (len(rows[0]) if rows else 0),
        "domain": (analysis.get("domain_info") or {}).get("domain") if isinstance(analysis.get("domain_info"), dict) else None,
        "target_column": target_column,
        "source": source,
        "owner": actor.get("username"),
    }

    entry = {
        "id": str(uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "fingerprint": make_dataset_fingerprint(rows, metadata),
        "dataset_name": dataset_name,
        "action": action,
        "source": source,
        "target_column": target_column,
        "created_by": actor,
        "summary": metadata,
        "analysis": analysis,
        "cleaning_stats": cleaning_stats or [],
        "ml_results": ml_results or {},
    }

    with CATALOG_LOCK:
        entries = _load_catalog()
        entries.append(entry)
        _write_catalog(entries)

    return entry


def list_catalog_entries(limit: int = 20) -> list[dict[str, Any]]:
    with CATALOG_LOCK:
        entries = _load_catalog()
    return list(reversed(entries))[:limit]


def get_catalog_entry(entry_id: str) -> dict[str, Any] | None:
    with CATALOG_LOCK:
        entries = _load_catalog()
    for entry in entries:
        if entry.get("id") == entry_id:
            return entry
    return None


def is_catalog_entry_visible(entry: dict[str, Any], current_user: dict[str, Any]) -> bool:
    if current_user.get("role") == "admin":
        return True

    owner_username = ((entry.get("created_by") or {}).get("username") or "").strip()
    if not owner_username:
        # Legacy entries without ownership metadata are restricted to admins.
        return False

    return owner_username == current_user.get("username")


def list_catalog_entries_for_user(current_user: dict[str, Any], limit: int = 20) -> list[dict[str, Any]]:
    entries = list_catalog_entries(limit=max(limit, 1) * 5)
    visible = [entry for entry in entries if is_catalog_entry_visible(entry, current_user)]
    return visible[: max(1, limit)]
