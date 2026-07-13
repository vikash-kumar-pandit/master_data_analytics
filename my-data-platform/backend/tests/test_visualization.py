import io
import json
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def _get_auth_headers():
    client.post(
        "/api/auth/register",
        json={
            "username": "viz_user",
            "password": "Securepassword123@",
            "email": "viz@example.com",
            "role": "analyst"
        }
    )
    
    response = client.post(
        "/api/auth/login",
        data={"username": "viz_user", "password": "Securepassword123@"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_ai_visualization_intelligence_engine():
    headers = _get_auth_headers()
    
    # Ingest mock Retail sales CSV
    csv_content = (
        "sales,category,date\n"
        "100.0,Furniture,2026-01-01\n"
        "500.0,Technology,2026-01-02\n"
        "200.0,Furniture,2026-01-03\n"
        "12000.0,Technology,2026-01-04\n"
    )
    file_payload = ("retail_sales.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")
    
    ingest_res = client.post(
        "/api/analytics/datasets/ingest",
        headers=headers,
        data={"project_name": "Viz Project"},
        files={"file": file_payload}
    )
    assert ingest_res.status_code == 200
    project_id = ingest_res.json()["project_id"]
    
    # 1. POST /recommend
    rec_res = client.post(
        "/api/visualization/recommend",
        headers=headers,
        data={"project_id": project_id}
    )
    assert rec_res.status_code == 200
    recs = rec_res.json()
    assert len(recs) > 0
    # Ensure ranked by rank order
    assert recs[0]["rank"] <= recs[-1]["rank"]
    
    # 2. POST /generate for single visual (e.g. sales_trend)
    gen_res = client.post(
        "/api/visualization/generate",
        headers=headers,
        data={
            "project_id": project_id,
            "chart_type": "sales_trend",
            "columns_json": json.dumps(["sales", "date"])
        }
    )
    assert gen_res.status_code == 200
    viz_data = gen_res.json()
    assert viz_data["chart_type"] == "sales_trend"
    assert len(viz_data["image_base64"]) > 0
    
    # 3. POST /generate-all
    gen_all_res = client.post(
        "/api/visualization/generate-all",
        headers=headers,
        data={"project_id": project_id}
    )
    assert gen_all_res.status_code == 200
    assert gen_all_res.json()["success"] is True
    assert gen_all_res.json()["count"] > 0
    
    # 4. GET /project/{id}
    list_res = client.get(f"/api/visualization/project/{project_id}", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == gen_all_res.json()["count"]
    
    # 5. GET /export?format=pptx
    pptx_res = client.get(f"/api/visualization/export?project_id={project_id}&format=pptx", headers=headers)
    assert pptx_res.status_code == 200
    assert len(pptx_res.content) > 0
    
    # 6. GET /export?format=zip
    zip_res = client.get(f"/api/visualization/export?project_id={project_id}&format=zip", headers=headers)
    assert zip_res.status_code == 200
    assert len(zip_res.content) > 0
