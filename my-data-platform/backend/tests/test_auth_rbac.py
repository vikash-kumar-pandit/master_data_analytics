from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import app
from observability import RATE_LIMIT_STATE, RATE_LIMITS

client = TestClient(app)


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


def test_login_returns_role_and_token():
    response = login("data_analyst")
    assert response.status_code == 200
    payload = response.json()
    assert payload["role"] == "analyst"
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]


def test_login_rejects_invalid_password():
    response = login("data_analyst", "wrong-password")
    assert response.status_code == 401


def test_viewer_cannot_upload():
    token = login("guest_viewer").json()["access_token"]
    response = client.post(
        "/upload",
        files={"file": ("sample.csv", sample_csv(), "text/csv")},
        headers=auth_headers(token),
    )
    assert response.status_code == 403


def test_analyst_can_upload():
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
    analyst_token = login("data_analyst").json()["access_token"]
    response = client.get("/api/admin-stats", headers=auth_headers(analyst_token))
    assert response.status_code == 403


def test_admin_stats_allows_admin_role():
    admin_token = login("admin_user").json()["access_token"]
    response = client.get("/api/admin-stats", headers=auth_headers(admin_token))
    assert response.status_code == 200
    assert response.json()["message"] == "Welcome Admin"


def test_rate_limit_blocks_repeated_login(monkeypatch):
    RATE_LIMIT_STATE.clear()
    monkeypatch.setitem(RATE_LIMITS, "/api/auth/login", 1)

    first = login("guest_viewer")
    second = login("guest_viewer")

    assert first.status_code == 200
    assert second.status_code == 429
