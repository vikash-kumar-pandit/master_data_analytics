import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_404_error_handling():
    """Accessing a non-existent endpoint returns a formatted JSON response."""
    response = client.get("/api/non-existent-route-999")
    assert response.status_code == 404
    payload = response.json()
    assert payload["status"] == "error"
    assert "Not Found" in payload["detail"]

def test_422_validation_error_handling():
    """Sending a malformed JSON payload returns a formatted 422 JSON response."""
    # /api/analytics/query expects QuestionRequest schema fields
    response = client.post("/api/analytics/query", json={"invalid_field": "val"})
    assert response.status_code == 422
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["detail"] == "Invalid request fields"
    assert "errors" in payload
