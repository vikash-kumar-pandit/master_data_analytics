import pytest
import polars as pl
from unittest.mock import MagicMock, AsyncMock
from fastapi import Request
from starlette.datastructures import Headers
from validation import ValidationError, validate_upload_payload, validate_numeric_column, validate_class_balance
from security_headers import SecurityHeadersMiddleware
from privacy import sanitize_for_llm, _mask_string
from ml_registry import register_model, find_model_for_dataset
from schemas import (
    HealthResponse, CatalogQuery, WorkflowCreateRequest, WorkflowRunRequest,
    QuestionRequest, ForecastRequest, CompareRequest, StructuredReportRequest,
    InsightRequest, ClusteringRequest, NLPRequest, ExplainRequest, CreateShareRequest,
    CreateScheduleRequest, ExecutiveSummaryRequest, SearchRequest, DownloadRequest,
    ExportRequest, QualityScoreRequest, QualityReportRequest, AutoMLRequest, ExportResultsRequest
)

# --- validation.py tests ---

def test_validate_upload_payload():
    with pytest.raises(ValidationError, match="Payload must be a JSON object"):
        validate_upload_payload("not a dict")
    
    with pytest.raises(ValidationError, match="Payload must contain a non-empty 'rows' array"):
        validate_upload_payload({"other": 123})
        
    with pytest.raises(ValidationError, match="Payload must contain a non-empty 'rows' array"):
        validate_upload_payload({"rows": "not a list"})

    with pytest.raises(ValidationError, match="Payload must contain a non-empty 'rows' array"):
        validate_upload_payload({"rows": []})

    with pytest.raises(ValidationError, match="Row 0 must be an object"):
        validate_upload_payload({"rows": ["not a dict"]})
        
    payload = {"rows": [{"a": 1}, {"b": 2}]}
    assert validate_upload_payload(payload) == payload


def test_validate_numeric_column():
    df = pl.DataFrame({
        "num_col": [1.0, 2.0, 3.0],
        "txt_col": ["a", "b", "c"]
    })
    
    # Valid numeric column
    validate_numeric_column(df, "num_col")
    
    # Missing column
    with pytest.raises(ValidationError, match="Column 'missing' not found in dataset"):
        validate_numeric_column(df, "missing")
        
    # Non-numeric column
    with pytest.raises(ValidationError, match="must be numeric, got (String|Utf8)"):
        validate_numeric_column(df, "txt_col")


def test_validate_class_balance():
    df = pl.DataFrame({
        "target": ["A", "A", "A", "A", "A", "B", "B", "C"]
    })
    
    # Missing column
    with pytest.raises(ValidationError, match="Target column 'missing' not found"):
        validate_class_balance(df, "missing")
        
    res = validate_class_balance(df, "target", min_samples_per_class=5)
    assert res["is_balanced"] is False
    assert res["imbalanced_classes"] == {"B": 2, "C": 1}
    assert res["class_distribution"] == {"A": 5, "B": 2, "C": 1}
    
    # Check when it is balanced
    df_balanced = pl.DataFrame({"target": ["A"] * 6 + ["B"] * 6})
    res_bal = validate_class_balance(df_balanced, "target", min_samples_per_class=5)
    assert res_bal["is_balanced"] is True
    assert res_bal["imbalanced_classes"] == {}


# --- security_headers.py tests ---

@pytest.mark.asyncio
async def test_security_headers_middleware_http():
    # Mocking call_next that returns a mock Response
    mock_response = MagicMock()
    mock_response.headers = {}
    
    async def mock_call_next(request):
        return mock_response
        
    # Mock FastAPI Request
    scope = {"type": "http"}
    request = Request(scope=scope)
    
    middleware = SecurityHeadersMiddleware(app=None)
    resp = await middleware.dispatch(request, mock_call_next)
    
    assert resp.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains; preload"
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["X-XSS-Protection"] == "1; mode=block"
    assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "Content-Security-Policy" in resp.headers


@pytest.mark.asyncio
async def test_security_headers_middleware_websocket():
    mock_response = MagicMock()
    mock_response.headers = {}
    
    async def mock_call_next(request):
        return mock_response
        
    scope = {"type": "websocket"}
    request = MagicMock()
    request.scope = scope
    
    middleware = SecurityHeadersMiddleware(app=None)
    resp = await middleware.dispatch(request, mock_call_next)
    
    # For websocket, security headers should not be modified
    assert "Strict-Transport-Security" not in resp.headers


# --- privacy.py tests ---

def test_mask_string_patterns():
    # Email
    assert "[MASKED_EMAIL]" in _mask_string("Contact me at testing@example.com.")
    # Phone
    assert "[MASKED_PHONE]" in _mask_string("Call 123-456-7890 or +1-234-567-8901.")
    # SSN
    assert "[MASKED_SSN]" in _mask_string("SSN is 000-12-3456.")
    # Aadhaar
    assert "[MASKED_AADHAAR]" in _mask_string("My Aadhaar is 1234 5678 9012.")
    # PAN
    assert "[MASKED_PAN]" in _mask_string("PAN: ABCDE1234F.")
    # IPv4
    assert "[MASKED_IP]" in _mask_string("Server at 192.168.1.1.")
    # Credit Card
    assert "[MASKED_CARD]" in _mask_string("My card is 5432109876543210.")
    assert "123" == _mask_string("123")  # Short digit sequence should not be masked as card


def test_sanitize_for_llm():
    # Test nested dict, list, tuple, primitive types
    payload = {
        "email": "abc@def.com",
        "nested": {
            "phone": "987-654-3210",
            "list": ["My SSN is 111-22-3333", 42, None],
            "tuple": ("PAN: ABCDE1234Z", 3.14)
        }
    }
    sanitized = sanitize_for_llm(payload)
    assert sanitized["email"] == "[MASKED_EMAIL]"
    assert sanitized["nested"]["phone"] == "[MASKED_PHONE]"
    assert sanitized["nested"]["list"][0] == "My SSN is [MASKED_SSN]"
    assert sanitized["nested"]["list"][1] == 42
    assert sanitized["nested"]["list"][2] is None
    assert sanitized["nested"]["tuple"][0] == "PAN: [MASKED_PAN]"
    assert sanitized["nested"]["tuple"][1] == 3.14


# --- ml_registry.py tests ---

def test_register_and_find_model():
    fingerprint = "test-fingerprint-123"
    target = "target_col"
    created_by = {"username": "test_user"}
    
    # Register model
    register_model(
        dataset_fingerprint=fingerprint,
        target_column=target,
        algorithm="Random Forest",
        accuracy=0.925,
        metrics={"f1": 0.91},
        created_by=created_by
    )
    
    # Find model
    retrieved = find_model_for_dataset(fingerprint, target)
    assert retrieved is not None
    assert retrieved["algorithm"] == "Random Forest"
    assert retrieved["accuracy"] == 0.925
    assert retrieved["metrics"] == {"f1": 0.91}
    assert retrieved["created_at"] is not None
    
    # Query non-existent model
    assert find_model_for_dataset("non-existent", "col") is None


# --- schemas.py tests ---

def test_pydantic_schemas():
    # HealthResponse
    assert HealthResponse(status="ok").status == "ok"
    
    # CatalogQuery
    assert CatalogQuery(limit=10).limit == 10
    
    # WorkflowCreateRequest
    wf = WorkflowCreateRequest(name="wf1", steps=["step1", "step2"])
    assert wf.name == "wf1"
    assert wf.steps == ["step1", "step2"]
    
    # WorkflowRunRequest
    assert WorkflowRunRequest(rows=[{"a": 1}]).rows == [{"a": 1}]
    
    # QuestionRequest
    qr = QuestionRequest(question="What is this?", rows=[{"a": 1}])
    assert qr.question == "What is this?"
    
    # ForecastRequest
    fr = ForecastRequest(rows=[{"a": 1}])
    assert fr.horizon == 7
    
    # CompareRequest
    cr = CompareRequest(before_rows=[{"a": 1}], after_rows=[{"a": 2}])
    assert cr.before_rows == [{"a": 1}]
    
    # StructuredReportRequest
    sr = StructuredReportRequest(title="Title", sections=["s1"])
    assert sr.output_format == "pdf"
    
    # InsightRequest
    ir = InsightRequest(data_summary={"summary": True})
    assert ir.data_summary == {"summary": True}
    
    # ClusteringRequest
    clr = ClusteringRequest(rows=[{"a": 1}])
    assert clr.num_clusters == 3
    
    # NLPRequest
    nlpr = NLPRequest(rows=[{"a": 1}], text_column="text", categories=["cat1"])
    assert nlpr.text_column == "text"
    
    # ExplainRequest
    er = ExplainRequest(rows=[{"a": 1}], target_column="target")
    assert er.top_k == 12
    
    # CreateShareRequest
    csr = CreateShareRequest(report_title="Title", report_data={"data": 1})
    assert csr.access_level == "view"
    
    # CreateScheduleRequest
    cschr = CreateScheduleRequest(name="Name", report_config={"id": "r1"}, schedule_cron="* * * * *")
    assert cschr.enabled is True
    
    # ExecutiveSummaryRequest
    esr = ExecutiveSummaryRequest(analysis={"a": 1}, result={"b": 2})
    assert esr.analysis == {"a": 1}
    
    # SearchRequest
    srq = SearchRequest()
    assert srq.limit == 20
    
    # DownloadRequest
    dr = DownloadRequest(rows=[])
    assert dr.analysis == {}
    
    # ExportRequest
    exr = ExportRequest(rows=[{"a": 1}])
    assert exr.filename == "export"
    
    # QualityScoreRequest
    qsr = QualityScoreRequest(rows=[{"a": 1}])
    assert len(qsr.rows) == 1
    
    # QualityReportRequest
    qrr = QualityReportRequest(rows=[{"a": 1}])
    assert len(qrr.rows) == 1
    
    # AutoMLRequest
    amlr = AutoMLRequest(rows=[{"a": 1}], target_column="target")
    assert amlr.target_column == "target"
    
    # ExportResultsRequest
    err = ExportResultsRequest(cleaned_data=[{"a": 1}])
    assert err.cleaned_data == [{"a": 1}]
