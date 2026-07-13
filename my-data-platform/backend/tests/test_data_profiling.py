import os
import io
import json
import pytest
from fastapi.testclient import TestClient
from database import SessionLocal
from main import app

client = TestClient(app)


def _get_auth_headers():
    client.post(
        "/api/auth/register",
        json={
            "username": "profiling_user",
            "password": "Securepassword123@",
            "email": "profiler@example.com",
            "role": "analyst"
        }
    )
    
    response = client.post(
        "/api/auth/login",
        data={"username": "profiling_user", "password": "Securepassword123@"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_universal_data_profiling_pipeline():
    headers = _get_auth_headers()
    
    # Create a mock CSV with target leakage, constant cols, and PII
    csv_content = (
        "id,email,value,constant_col,target,leaker_col\n"
        "1,vikash@example.com,10.5,1,100.0,99.9\n"
        "2,john@gmail.com,20.0,1,200.0,199.9\n"
        "3,alice@yahoo.com,15.75,1,150.0,149.9\n"
    )
    file_payload = ("profile_dataset.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")
    
    # 1. Ingest
    ingest_res = client.post(
        "/api/analytics/datasets/ingest",
        headers=headers,
        data={"project_name": "Profiling Project"},
        files={"file": file_payload}
    )
    assert ingest_res.status_code == 200
    project_id = ingest_res.json()["project_id"]
    dataset_id = ingest_res.json()["dataset_id"]
    
    # 2. Run Profiler
    profile_res = client.post(
        "/api/profile/run",
        headers=headers,
        data={"project_id": project_id, "target_column": "target"}
    )
    assert profile_res.status_code == 200
    res_data = profile_res.json()
    assert "profile_id" in res_data
    
    profile_info = res_data["data"]
    assert profile_info["rows"] == 3
    assert profile_info["columns"] == 6
    
    # Verify constant column warning
    warnings = profile_info["warnings"]
    assert any("constant_col" in w.get("column", "") and "constant" in w["message"].lower() for w in warnings)
    
    # Verify email PII detection
    assert profile_info["statistics"]["email"]["pii_detected"] == "Email addresses detected"
    
    # Verify target leakage detection
    assert any("leaker_col" in w.get("column", "") and "leakage" in w["message"].lower() for w in warnings)
    
    # 3. Retrieve Profile
    get_res = client.get(f"/api/profile/{dataset_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["rows"] == 3
    
    # 4. Exports check
    exp_json = client.get(f"/api/profile/export/json?dataset_id={dataset_id}", headers=headers)
    assert exp_json.status_code == 200
    assert exp_json.json()["rows"] == 3
    
    exp_html = client.get(f"/api/profile/export/html?dataset_id={dataset_id}", headers=headers)
    assert exp_html.status_code == 200
    assert b"<!DOCTYPE html>" in exp_html.content
    
    exp_pdf = client.get(f"/api/profile/export/pdf?dataset_id={dataset_id}", headers=headers)
    assert exp_pdf.status_code == 200
    assert exp_pdf.content.startswith(b"%PDF")
