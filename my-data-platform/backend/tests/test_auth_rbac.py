"""
test_auth_rbac.py — Role-Based Access Control (RBAC) Integration Tests

Tests cover:
  - Login returns correct role & token
  - Wrong password rejected (401)
  - Viewer cannot upload (403)
  - Analyst can upload (200)
  - Non-admin gets 403 on admin-only endpoint
  - Admin (real credentials) gets 200 on admin endpoint
  - Rate limiting blocks repeated logins (429)

The conftest.py in this directory seeds the test DB with:
  - Admin: Vikash_24a12res1159@iitp.ac.in / Vikashkumarpandit1159@gmail.com
  - Analyst: data_analyst / password123
  - Viewer:  guest_viewer / password123
"""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import app
from observability import RATE_LIMIT_STATE, RATE_LIMITS

client = TestClient(app)

# ── credentials ──────────────────────────────────────────────────────────────
ADMIN_USERNAME = "Vikash_24a12res1159@iitp.ac.in"
ADMIN_PASSWORD = "Vikashkumarpandit1159@gmail.com"


# ── helpers ───────────────────────────────────────────────────────────────────
def login(username: str, password: str = "password123"):
    return client.post(
        "/api/auth/login",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def sample_csv() -> bytes:
    return b"name,value\nalpha,1\nbeta,2\n"


# ── tests ─────────────────────────────────────────────────────────────────────
def test_login_returns_role_and_token():
    """Analyst login returns correct role and a non-empty JWT."""
    response = login("data_analyst")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["role"] == "analyst"
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]


def test_login_rejects_invalid_password():
    """Login with wrong password returns 401."""
    response = login("data_analyst", "wrong-password")
    assert response.status_code == 401


def test_viewer_cannot_upload():
    """Viewer role is forbidden from uploading files."""
    token = login("guest_viewer").json()["access_token"]
    response = client.post(
        "/upload",
        files={"file": ("sample.csv", sample_csv(), "text/csv")},
        headers=auth_headers(token),
    )
    assert response.status_code == 403


def test_analyst_can_upload():
    """Analyst role can upload and receive analysis results."""
    token = login("data_analyst").json()["access_token"]
    response = client.post(
        "/upload",
        files={"file": ("sample.csv", sample_csv(), "text/csv")},
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    payload = response.json()
    assert "analysis" in payload
    assert "grid_data" in payload


def test_admin_stats_requires_admin_role():
    """Non-admin role is forbidden from accessing admin-only stats endpoint."""
    analyst_token = login("data_analyst").json()["access_token"]
    response = client.get("/api/admin-stats", headers=auth_headers(analyst_token))
    assert response.status_code == 403


def test_admin_stats_allows_admin_role():
    """Admin can access admin-only stats endpoint with real credentials."""
    response = login(ADMIN_USERNAME, ADMIN_PASSWORD)
    assert response.status_code == 200, (
        f"Admin login failed (status={response.status_code}): {response.text}"
    )
    admin_token = response.json()["access_token"]
    stats_response = client.get("/api/admin-stats", headers=auth_headers(admin_token))
    assert stats_response.status_code == 200
    assert stats_response.json()["message"] == "Welcome Admin"


def test_viewer_login_gets_viewer_role():
    """Viewer login returns viewer role - cannot log in as analyst."""
    response = login("guest_viewer")
    assert response.status_code == 200
    assert response.json()["role"] == "viewer"


def test_analyst_login_gets_analyst_role():
    """Analyst login returns analyst role - role is strictly enforced."""
    response = login("data_analyst")
    assert response.status_code == 200
    assert response.json()["role"] == "analyst"


def test_admin_login_gets_admin_role():
    """Admin login returns admin role."""
    response = login(ADMIN_USERNAME, ADMIN_PASSWORD)
    assert response.status_code == 200, response.text
    assert response.json()["role"] == "admin"


def test_rate_limit_blocks_repeated_login(monkeypatch):
    """Rate limiter blocks excessive login attempts from the same client."""
    RATE_LIMIT_STATE.clear()
    monkeypatch.setitem(RATE_LIMITS, "/api/auth/login", 1)

    first = login("guest_viewer")
    second = login("guest_viewer")

    assert first.status_code == 200
    assert second.status_code == 429
