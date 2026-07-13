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
            "username": "prep_user",
            "password": "Securepassword123@",
            "email": "prep@example.com",
            "role": "analyst"
        }
    )
    
    response = client.post(
        "/api/auth/login",
        data={"username": "prep_user", "password": "Securepassword123@"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_data_preparation_studio_pipeline():
    headers = _get_auth_headers()
    
    # 1. Ingest Dataset
    csv_content = (
        "name,val\n"
        "Alice,10.0\n"
        "Bob,\n"
        "CHARLIE,20.0\n"
    )
    file_payload = ("prep_dataset.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")
    
    ingest_res = client.post(
        "/api/analytics/datasets/ingest",
        headers=headers,
        data={"project_name": "Prep Project"},
        files={"file": file_payload}
    )
    assert ingest_res.status_code == 200
    project_id = ingest_res.json()["project_id"]
    
    # 2. Run fill_mean on column 'val'
    run_res = client.post(
        "/api/preparation/run",
        headers=headers,
        data={
            "project_id": project_id,
            "operation_type": "fill_mean",
            "parameters_json": json.dumps({"columns": ["val"]})
        }
    )
    assert run_res.status_code == 200
    assert run_res.json()["version_num"] == 2
    
    # Check that null is filled with mean (15.0)
    preview = run_res.json()["preview_data"]
    assert preview[1]["val"] == 15.0
    
    # 3. Run lowercase on column 'name'
    run_res2 = client.post(
        "/api/preparation/run",
        headers=headers,
        data={
            "project_id": project_id,
            "operation_type": "lowercase",
            "parameters_json": json.dumps({"columns": ["name"]})
        }
    )
    assert run_res2.status_code == 200
    assert run_res2.json()["version_num"] == 3
    preview2 = run_res2.json()["preview_data"]
    assert preview2[2]["name"] == "charlie"
    
    # 4. Check Transformation History
    hist_res = client.get(f"/api/preparation/history?project_id={project_id}", headers=headers)
    assert hist_res.status_code == 200
    hist_data = hist_res.json()
    assert hist_data["current_pointer"] == 3
    assert len(hist_data["steps"]) == 3
    
    # 5. Undo step
    undo_res = client.post(
        "/api/preparation/undo",
        headers=headers,
        data={"project_id": project_id}
    )
    assert undo_res.status_code == 200
    assert undo_res.json()["current_pointer"] == 2
    
    # 6. Redo step
    redo_res = client.post(
        "/api/preparation/redo",
        headers=headers,
        data={"project_id": project_id}
    )
    assert redo_res.status_code == 200
    assert redo_res.json()["current_pointer"] == 3
    
    # 7. Rollback to version 1 (raw)
    roll_res = client.post(
        f"/api/preparation/rollback/1",
        headers=headers,
        data={"project_id": project_id, "version": 1}
    )
    assert roll_res.status_code == 200
    assert roll_res.json()["current_pointer"] == 1
    
    # 8. Export active version (version 1)
    exp_res = client.get(f"/api/preparation/export?project_id={project_id}&format=csv", headers=headers)
    assert exp_res.status_code == 200
    assert b"Bob" in exp_res.content
