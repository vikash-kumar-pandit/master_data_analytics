from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

SHARES_PATH = Path(__file__).resolve().parent / "data" / "shares.json"
SHARES_PATH.parent.mkdir(parents=True, exist_ok=True)
SHARE_LOCK = Lock()


def _load_shares() -> list[dict[str, Any]]:
    if not SHARES_PATH.exists():
        return []
    try:
        return json.loads(SHARES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def _write_shares(shares: list[dict[str, Any]]) -> None:
    SHARES_PATH.write_text(json.dumps(shares, indent=2, default=str), encoding="utf-8")


def create_share_link(
    *,
    report_title: str,
    report_data: dict[str, Any],
    created_by: dict[str, Any] | None = None,
    expires_days: int = 30,
    access_level: str = "view",
) -> dict[str, Any]:
    """Create a shareable link for a report."""
    # Validate inputs
    if not report_title or not report_title.strip():
        raise ValueError("report_title cannot be empty")
    if not isinstance(report_data, dict):
        raise ValueError("report_data must be a dictionary")
    if expires_days < 1 or expires_days > 365:
        raise ValueError("expires_days must be between 1 and 365")
    if access_level not in ["view", "download", "edit"]:
        raise ValueError("access_level must be 'view', 'download', or 'edit'")
    
    share_token = str(uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(days=max(1, min(expires_days, 365)))
    
    share = {
        "token": share_token,
        "report_title": report_title.strip(),
        "report_data": report_data,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": expires_at.isoformat(),
        "access_level": access_level,  # "view", "download", "edit"
        "created_by": (created_by or {}).get("username"),
        "view_count": 0,
        "downloads": [],
    }

    with SHARE_LOCK:
        shares = _load_shares()
        shares.append(share)
        _write_shares(shares)

    return {
        "token": share_token,
        "share_url": f"/share/{share_token}",
        "expires_at": expires_at.isoformat(),
        "access_level": access_level,
    }


def get_share(token: str) -> dict[str, Any] | None:
    """Retrieve a share by token and check expiry."""
    if not token or not token.strip():
        raise ValueError("token cannot be empty")
    
    with SHARE_LOCK:
        shares = _load_shares()
    
    for share in shares:
        if share.get("token") == token:
            expires_at_str = share.get("expires_at")
            if expires_at_str:
                try:
                    expires_at = datetime.fromisoformat(expires_at_str)
                    if datetime.now(timezone.utc) > expires_at:
                        return None  # Share has expired
                except (ValueError, TypeError):
                    return None  # Invalid expiry format
            return share
    
    return None


def increment_view_count(token: str) -> None:
    """Increment the view count for a share."""
    if not token or not token.strip():
        raise ValueError("token cannot be empty")
    
    with SHARE_LOCK:
        shares = _load_shares()
        for share in shares:
            if share.get("token") == token:
                share["view_count"] = (share.get("view_count") or 0) + 1
                _write_shares(shares)
                break


def record_download(token: str, format: str, username: str | None = None) -> None:
    """Record a download event."""
    if not token or not token.strip():
        raise ValueError("token cannot be empty")
    if not format or not format.strip():
        raise ValueError("format cannot be empty")
    if format not in ["pdf", "pptx", "csv", "bundle"]:
        raise ValueError(f"Invalid format: {format}")
    
    with SHARE_LOCK:
        shares = _load_shares()
        for share in shares:
            if share.get("token") == token:
                downloads = share.get("downloads") or []
                downloads.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "format": format,
                    "username": username or "anonymous",
                })
                share["downloads"] = downloads
                _write_shares(shares)
                break


def list_my_shares(username: str, limit: int = 20) -> list[dict[str, Any]]:
    """List all shares created by a user."""
    if not username or not username.strip():
        raise ValueError("username cannot be empty")
    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100")
    
    with SHARE_LOCK:
        shares = _load_shares()
    
    user_shares = [s for s in shares if s.get("created_by") == username]
    return list(reversed(user_shares))[:limit]


def revoke_share(token: str, username: str | None = None) -> bool:
    """Revoke a share link."""
    if not token or not token.strip():
        raise ValueError("token cannot be empty")
    
    with SHARE_LOCK:
        shares = _load_shares()
        for i, share in enumerate(shares):
            if share.get("token") == token:
                if username and share.get("created_by") != username:
                    return False  # Not authorized
                shares.pop(i)
                _write_shares(shares)
                return True
    
    return False
