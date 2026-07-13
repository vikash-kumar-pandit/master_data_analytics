import os
import io
import json
import pytest
from fastapi.testclient import TestClient
from database import SessionLocal
from main import app

client = TestClient(app)


def _get_auth_headers():
    # Register the user first to make sure it exists
    client.post(
        "/api/auth/register",
        json={
            "username": "analyst_user",
            "password": "Securepassword123@",
            "email": "analyst@example.com",
            "role": "analyst"
        }
    )
    
    # Login
    response = client.post(
        "/api/auth/login",
        data={"username": "analyst_user", "password": "Securepassword123@"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_dataset_ingestion_and_pipeline():
    headers = _get_auth_headers()
    
    # Create a mock CSV file
    csv_content = (
        "id,name,value,is_active,created_at\n"
        "1,item_a,10.5,True,2026-01-01\n"
        "2,item_b,20.0,False,2026-01-02\n"
        "3,item_c,15.75,True,2026-01-03\n"
    )
    file_payload = ("test_dataset.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")
    
    # Run ingestion
    response = client.post(
        "/api/analytics/datasets/ingest",
        headers=headers,
        data={"project_name": "Test Ingestion Project"},
        files={"file": file_payload}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "project_id" in data
    assert "dataset_id" in data
    assert data["metadata"]["row_count"] == 3
    assert data["metadata"]["column_count"] == 5
    assert "id" in data["metadata"]["primary_key_candidates"]
    
    project_id = data["project_id"]
    
    # Verify Project list
    list_response = client.get("/api/analytics/projects", headers=headers)
    assert list_response.status_code == 200
    projects = list_response.json()
    assert any(p["id"] == project_id for p in projects)
    
    # Verify pipeline state
    pipe_response = client.get(f"/api/analytics/projects/{project_id}/pipeline", headers=headers)
    assert pipe_response.status_code == 200
    pipeline = pipe_response.json()
    
    # Upload and profile must be COMPLETED
    upload_node = next(n for n in pipeline if n["node_type"] == "UPLOAD")
    profile_node = next(n for n in pipeline if n["node_type"] == "PROFILE")
    assert upload_node["status"] == "COMPLETED"
    assert profile_node["status"] == "COMPLETED"
    
    # Update pipeline node status to RUNNING for QUALITY
    update_response = client.post(
        f"/api/analytics/projects/{project_id}/nodes/QUALITY",
        headers=headers,
        data={"status": "RUNNING", "logs": "Running quality checks..."}
    )
    assert update_response.status_code == 200
    
    # Recheck pipeline
    pipe_response = client.get(f"/api/analytics/projects/{project_id}/pipeline", headers=headers)
    quality_node = next(n for n in pipe_response.json() if n["node_type"] == "QUALITY")
    assert quality_node["status"] == "RUNNING"
    assert quality_node["logs"] == "Running quality checks..."
    
    # Export csv step
    export_response = client.get(
        f"/api/analytics/projects/{project_id}/export/UPLOAD?format=csv",
        headers=headers
    )
    assert export_response.status_code == 200
    assert b"id,name,value" in export_response.content
