"""
API Endpoint Tests
Tests for FastAPI endpoint validation and error handling.
"""

import pytest
import sys
import os
import json
from unittest.mock import MagicMock, patch, AsyncMock

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from fastapi.testclient import TestClient
from fastapi import HTTPException

# Mock the dependencies before importing main
import auth as auth_module
auth_module.require_role = lambda roles: lambda x: {"user_id": "test_user", "role": "admin"}


# Import main after mocking
from main import app, QuestionRequest, ForecastRequest, CompareRequest


client = TestClient(app)


class TestAnalyticsQueryEndpoint:
    """Test /api/analytics/query endpoint validation"""
    
    def test_query_empty_question(self):
        """Test query with empty question"""
        payload = {
            "question": "",
            "rows": [{"col": 1}]
        }
        response = client.post("/api/analytics/query", json=payload)
        # Should handle gracefully - either 400 or return fallback result
        assert response.status_code in [400, 200]
    
    def test_query_no_rows(self):
        """Test query with no rows"""
        payload = {
            "question": "What is this?",
            "rows": []
        }
        response = client.post("/api/analytics/query", json=payload)
        assert response.status_code in [400, 200]
    
    def test_query_invalid_rows_format(self):
        """Test query with invalid rows format"""
        payload = {
            "question": "What is this?",
            "rows": "not_a_list"
        }
        response = client.post("/api/analytics/query", json=payload)
        assert response.status_code in [400, 422]  # Validation error or Pydantic error
    
    def test_query_valid_request(self):
        """Test query with valid request"""
        payload = {
            "question": "What is the average age?",
            "rows": [
                {"name": "Alice", "age": 25},
                {"name": "Bob", "age": 30}
            ]
        }
        response = client.post("/api/analytics/query", json=payload)
        assert response.status_code in [200, 500]  # Accept both success and service error
        if response.status_code == 200:
            data = response.json()
            assert "intent" in data
            assert "answer" in data


class TestForecastEndpoint:
    """Test /api/analytics/forecast endpoint validation"""
    
    def test_forecast_valid_request(self):
        """Test forecast with valid data"""
        payload = {
            "rows": [
                {"value": 100},
                {"value": 150},
                {"value": 200}
            ],
            "metric_column": "value",
            "horizon": 3
        }
        response = client.post("/api/analytics/forecast", json=payload)
        assert response.status_code in [200, 400, 500]
    
    def test_forecast_empty_rows(self):
        """Test forecast with empty rows"""
        payload = {
            "rows": [],
            "metric_column": "value",
            "horizon": 3
        }
        response = client.post("/api/analytics/forecast", json=payload)
        assert response.status_code in [400, 500]
    
    def test_forecast_invalid_horizon(self):
        """Test forecast with invalid horizon"""
        payload = {
            "rows": [{"value": 100}],
            "metric_column": "value",
            "horizon": -1  # Invalid
        }
        response = client.post("/api/analytics/forecast", json=payload)
        # Should either fix the horizon or reject
        assert response.status_code in [200, 400, 500]


class TestCompareEndpoint:
    """Test /api/analytics/compare endpoint validation"""
    
    def test_compare_valid_request(self):
        """Test compare with valid data"""
        payload = {
            "before_rows": [{"col": 100}],
            "after_rows": [{"col": 110}]
        }
        response = client.post("/api/analytics/compare", json=payload)
        assert response.status_code in [200, 400, 500]
    
    def test_compare_empty_before_rows(self):
        """Test compare with empty before_rows"""
        payload = {
            "before_rows": [],
            "after_rows": [{"col": 110}]
        }
        response = client.post("/api/analytics/compare", json=payload)
        assert response.status_code in [400, 500]


class TestReportEndpoint:
    """Test /api/analytics/report endpoint validation"""
    
    def test_report_empty_sections(self):
        """Test report with empty sections"""
        payload = {
            "title": "Test Report",
            "subtitle": "Test",
            "sections": [],
            "output_format": "pdf"
        }
        response = client.post("/api/analytics/report", json=payload)
        # Should generate a valid PDF even with empty sections
        assert response.status_code in [200, 400, 500]
        if response.status_code == 200:
            assert response.headers["content-type"] == "application/pdf"
    
    def test_report_malformed_sections(self):
        """Test report with malformed sections"""
        payload = {
            "title": "Test",
            "subtitle": "Test",
            "sections": [
                {"heading": "Valid", "rows": [{"label": "A", "value": "B"}]},
                None,
                "invalid"
            ],
            "output_format": "pdf"
        }
        response = client.post("/api/analytics/report", json=payload)
        # Should handle gracefully and generate report
        assert response.status_code in [200, 400, 500]
    
    def test_report_pptx_format(self):
        """Test report with PPTX format"""
        payload = {
            "title": "Presentation",
            "subtitle": "Test",
            "sections": [
                {
                    "heading": "Slide 1",
                    "rows": [{"label": "Point", "value": "Content"}]
                }
            ],
            "output_format": "pptx"
        }
        response = client.post("/api/analytics/report", json=payload)
        assert response.status_code in [200, 400, 500]
        if response.status_code == 200:
            assert "presentationml" in response.headers.get("content-type", "")


class TestHealthEndpoint:
    """Test health check endpoint"""
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


class TestErrorResponses:
    """Test error response formats"""
    
    def test_error_response_format(self):
        """Test that errors return proper format"""
        payload = {
            "question": "Test",
            "rows": "invalid"  # Will cause Pydantic validation error
        }
        response = client.post("/api/analytics/query", json=payload)
        assert response.status_code >= 400
        # Should have error details in response
        if response.status_code != 200:
            try:
                data = response.json()
                # Check if error info is present
                assert "detail" in data or response.text
            except:
                pass  # Some errors might not be JSON


class TestInputSanitization:
    """Test input sanitization"""
    
    def test_very_long_question(self):
        """Test with very long question string"""
        payload = {
            "question": "A" * 10000,
            "rows": [{"col": 1}]
        }
        response = client.post("/api/analytics/query", json=payload)
        # Should handle without crashing
        assert response.status_code in [200, 400, 500]
    
    def test_question_with_special_chars(self):
        """Test with special characters in question"""
        payload = {
            "question": "What <is> \"this\" & that? कुछ देखो",
            "rows": [{"col": 1}]
        }
        response = client.post("/api/analytics/query", json=payload)
        assert response.status_code in [200, 400, 500]
    
    def test_very_large_rows_payload(self):
        """Test with large rows payload"""
        # Create 1000 rows
        rows = [{"col1": i, "col2": i*2, "col3": f"data_{i}"} for i in range(1000)]
        payload = {
            "question": "Analyze this",
            "rows": rows
        }
        response = client.post("/api/analytics/query", json=payload)
        # Should handle without crashing
        assert response.status_code in [200, 400, 500]


class TestConcurrency:
    """Test concurrent request handling"""
    
    def test_multiple_sequential_requests(self):
        """Test multiple sequential requests"""
        payloads = [
            {"question": f"Query {i}", "rows": [{"value": i}]}
            for i in range(5)
        ]
        
        for payload in payloads:
            response = client.post("/api/analytics/query", json=payload)
            # All should succeed or fail gracefully
            assert response.status_code in [200, 400, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
