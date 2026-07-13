import pytest
from fastapi.testclient import TestClient
from main import app
import polars as pl

client = TestClient(app)


def get_auth_headers():
    response = client.post(
        "/api/auth/login",
        data={"username": "admin_user", "password": "password123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_endpoint():
    headers = get_auth_headers()
    # Create simple CSV file in memory
    csv_content = b"name,val,category\nAlice,10,A\nBob,20,B"
    
    response = client.post(
        "/upload",
        files={"file": ("test.csv", csv_content, "text/csv")},
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "analysis" in data
    assert "grid_data" in data


def test_analytics_query():
    headers = get_auth_headers()
    payload = {
        "question": "Show descriptive statistics",
        "rows": [{"val": 10, "category": "A"}, {"val": 20, "category": "B"}],
        "previous_rows": None,
        "analysis": None
    }
    response = client.post(
        "/api/analytics/query",
        json=payload,
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "recommendations" in data


def test_analytics_forecast():
    headers = get_auth_headers()
    payload = {
        "rows": [
            {"date": "2026-01-01", "val": 10},
            {"date": "2026-01-02", "val": 15},
            {"date": "2026-01-03", "val": 20}
        ],
        "metric_column": "val",
        "date_column": "date",
        "horizon": 3
    }
    response = client.post(
        "/api/analytics/forecast",
        json=payload,
        headers=headers
    )
    assert response.status_code == 200
    assert response.status_code == 200
    data = response.json()
    assert "forecast" in data
    assert "model_stats" in data


def test_analytics_compare():
    headers = get_auth_headers()
    payload = {
        "before_rows": [{"val": 10}, {"val": 20}],
        "after_rows": [{"val": 12}, {"val": 22}]
    }
    response = client.post(
        "/api/analytics/compare",
        json=payload,
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "comparison" in data
    assert "metrics" in data


def test_analytics_report():
    headers = get_auth_headers()
    payload = {
        "title": "Analytics Quality Report",
        "subtitle": "Test report",
        "sections": [
            {
                "heading": "Summary",
                "rows": [{"label": "Rows count", "value": "100"}]
            }
        ],
        "output_format": "pdf"
    }
    # PDF format
    response = client.post(
        "/api/analytics/report",
        json=payload,
        headers=headers
    )
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")

    # PPTX format
    payload["output_format"] = "pptx"
    response_pptx = client.post(
        "/api/analytics/report",
        json=payload,
        headers=headers
    )
    assert response_pptx.status_code == 200
