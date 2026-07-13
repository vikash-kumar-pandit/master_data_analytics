import os
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
            "username": "copilot_user",
            "password": "Securepassword123@",
            "email": "copilot@example.com",
            "role": "analyst"
        }
    )
    
    response = client.post(
        "/api/auth/login",
        data={"username": "copilot_user", "password": "Securepassword123@"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_copilot_conversational_intelligence_pipeline():
    headers = _get_auth_headers()
    
    # Ingest mock Retail sales CSV
    csv_content = (
        "sales,category,customer_id\n"
        "100.0,Furniture,cust_1\n"
        "500.0,Technology,cust_2\n"
        "200.0,Furniture,cust_3\n"
        "12000.0,Technology,cust_4\n"  # Extreme outlier
    )
    file_payload = ("retail_sales.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")
    
    ingest_res = client.post(
        "/api/analytics/datasets/ingest",
        headers=headers,
        data={"project_name": "Copilot Project"},
        files={"file": file_payload}
    )
    assert ingest_res.status_code == 200
    project_id = ingest_res.json()["project_id"]
    
    # 1. Verify AI Execution Plan
    plan_res = client.get(f"/api/copilot/plan?project_id={project_id}", headers=headers)
    assert plan_res.status_code == 200
    plan_data = plan_res.json()
    assert plan_data["domain"] == "Retail & E-commerce"
    assert "Sales Forecasting" in plan_data["recommended_goal"]
    assert plan_data["rows"] == 4
    
    # 2. Create Chat Session
    sess_res = client.post(
        "/api/copilot/sessions/create",
        headers=headers,
        data={"project_id": project_id, "title": "Sales Diagnostics"}
    )
    assert sess_res.status_code == 200
    session_id = sess_res.json()["session_id"]
    
    # 3. Post chat message: "Find anomalies"
    chat_res = client.post(
        "/api/copilot/chat",
        headers=headers,
        data={
            "project_id": project_id,
            "session_id": session_id,
            "message": "Find outlier anomalies"
        }
    )
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert chat_data["session_id"] == session_id
    assert chat_data["confidence"] > 0
    assert "outlier" in chat_data["evidence"].lower()
    
    # Verify visual asset was generated (should be anomaly table)
    messages = chat_data["messages"]
    assistant_msg = next(m for m in messages if m["role"] == "assistant")
    assert assistant_msg["assets"]["type"] == "table"
    
    # 4. Post chat message: "Show top profitable category"
    chat_res2 = client.post(
        "/api/copilot/chat",
        headers=headers,
        data={
            "project_id": project_id,
            "session_id": session_id,
            "message": "Show top category"
        }
    )
    assert chat_res2.status_code == 200
    chat_data2 = chat_res2.json()
    messages2 = chat_data2["messages"]
    assistant_msg2 = messages2[-1]
    assert assistant_msg2["role"] == "assistant"
    assert assistant_msg2["assets"]["type"] == "bar"
