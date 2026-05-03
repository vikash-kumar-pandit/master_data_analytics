"""
Comprehensive Error Handling Tests
Tests for PDF generation, Report generation, and API endpoint validation.
"""

import pytest
import sys
import os
from io import BytesIO

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import polars as pl
from pdf_generator import create_pdf_in_memory
from report_generator import generate_pdf_in_memory, generate_structured_report_pdf, generate_structured_report_pptx
from analytics_engine import analyze_question, compare_versions, forecast_metric


class TestPDFGenerator:
    """Test error handling in pdf_generator.py"""
    
    def test_create_pdf_with_empty_dataframe(self):
        """Test PDF generation with empty dataframe"""
        df = pl.DataFrame()
        summary = "Test summary"
        result = create_pdf_in_memory(summary, df)
        assert result is not None
        assert isinstance(result, bytes)
        assert len(result) > 0
    
    def test_create_pdf_with_none_dataframe(self):
        """Test PDF generation with None dataframe"""
        summary = "Test summary"
        result = create_pdf_in_memory(summary, None)
        assert result is not None
        assert isinstance(result, bytes)
    
    def test_create_pdf_with_empty_summary(self):
        """Test PDF generation with empty summary"""
        df = pl.DataFrame({"col1": [1, 2, 3]})
        summary = ""
        result = create_pdf_in_memory(summary, df)
        assert result is not None
        assert isinstance(result, bytes)
    
    def test_create_pdf_with_long_summary(self):
        """Test PDF generation with very long summary"""
        df = pl.DataFrame({"col1": [1, 2, 3]})
        summary = "A" * 10000  # Very long summary
        result = create_pdf_in_memory(summary, df)
        assert result is not None
        assert isinstance(result, bytes)
    
    def test_create_pdf_with_valid_data(self):
        """Test PDF generation with valid data"""
        df = pl.DataFrame({
            "name": ["Alice", "Bob", "Charlie"],
            "age": [25, 30, 35],
            "salary": [50000, 60000, 70000]
        })
        summary = "This is a test summary"
        result = create_pdf_in_memory(summary, df)
        assert result is not None
        assert isinstance(result, bytes)
        assert len(result) > 100


class TestReportGenerator:
    """Test error handling in report_generator.py"""
    
    def test_generate_pdf_with_empty_dataframe(self):
        """Test report PDF generation with empty dataframe"""
        df = pl.DataFrame()
        analysis = {"rows": 0, "category": "Test", "cols": 0}
        result = generate_pdf_in_memory(df, analysis)
        assert result is not None
        assert isinstance(result, bytes)
    
    def test_generate_pdf_with_none_analysis(self):
        """Test report PDF generation with None analysis"""
        df = pl.DataFrame({"col1": [1, 2, 3]})
        result = generate_pdf_in_memory(df, None)
        assert result is not None
        assert isinstance(result, bytes)
    
    def test_structured_pdf_with_empty_sections(self):
        """Test structured PDF with empty sections"""
        result = generate_structured_report_pdf(
            title="Test Report",
            subtitle="Test Subtitle",
            sections=[]
        )
        assert result is not None
        assert isinstance(result, bytes)
    
    def test_structured_pdf_with_valid_data(self):
        """Test structured PDF with valid data"""
        sections = [
            {
                "heading": "Summary",
                "rows": [
                    {"label": "Rows", "value": "100"},
                    {"label": "Columns", "value": "5"}
                ]
            },
            {
                "heading": "Metrics",
                "rows": [
                    {"label": "Average", "value": "42.5"}
                ]
            }
        ]
        result = generate_structured_report_pdf(
            title="Test Report",
            subtitle="Analysis Results",
            sections=sections
        )
        assert result is not None
        assert isinstance(result, bytes)
        assert len(result) > 100
    
    def test_structured_pdf_with_malformed_sections(self):
        """Test structured PDF with malformed sections"""
        sections = [
            {"heading": "Valid", "rows": [{"label": "Test", "value": "Value"}]},
            "invalid_section",  # Invalid section
            None,  # None section
            {"heading": "Another", "rows": "not_a_list"},  # Invalid rows
        ]
        result = generate_structured_report_pdf(
            title="Test Report",
            subtitle="Test",
            sections=sections
        )
        assert result is not None
        assert isinstance(result, bytes)
    
    def test_structured_pptx_with_empty_sections(self):
        """Test PPTX generation with empty sections"""
        result = generate_structured_report_pptx(
            title="Test",
            subtitle="Subtitle",
            sections=[]
        )
        assert result is not None
        assert isinstance(result, bytes)
    
    def test_structured_pptx_with_valid_data(self):
        """Test PPTX generation with valid data"""
        sections = [
            {
                "heading": "Overview",
                "rows": [
                    {"label": "Total Records", "value": "1000"},
                    {"label": "Analysis Type", "value": "Sales"}
                ]
            }
        ]
        result = generate_structured_report_pptx(
            title="Sales Report",
            subtitle="Q1 2024",
            sections=sections
        )
        assert result is not None
        assert isinstance(result, bytes)
        assert len(result) > 100


class TestAnalyticsEngine:
    """Test error handling in analytics_engine.py"""
    
    def test_analyze_question_with_empty_rows(self):
        """Test question analysis with empty rows"""
        result = analyze_question(
            question="What is the average?",
            rows=[]
        )
        assert result is not None
        assert "intent" in result
        assert "answer" in result
        assert result.get("answer", "").lower() == "no data available. upload a dataset first."
    
    def test_analyze_question_with_valid_data(self):
        """Test question analysis with valid data"""
        rows = [
            {"name": "Alice", "age": 25, "salary": 50000},
            {"name": "Bob", "age": 30, "salary": 60000},
            {"name": "Charlie", "age": 35, "salary": 70000}
        ]
        result = analyze_question(
            question="What is the average salary?",
            rows=rows
        )
        assert result is not None
        assert "intent" in result
        assert "answer" in result
        assert "report_sections" in result
        assert result["report_sections"]  # Should have sections
    
    def test_analyze_question_predictive_intent(self):
        """Test predictive question analysis"""
        rows = [
            {"month": 1, "sales": 100},
            {"month": 2, "sales": 150},
            {"month": 3, "sales": 200},
            {"month": 4, "sales": 250}
        ]
        result = analyze_question(
            question="What will happen next?",
            rows=rows
        )
        assert result is not None
        assert result.get("intent") in ["predictive", "descriptive"]
    
    def test_analyze_question_with_previous_rows(self):
        """Test question analysis with version comparison"""
        before_rows = [
            {"id": 1, "value": 100},
            {"id": 2, "value": 200}
        ]
        after_rows = [
            {"id": 1, "value": 110},
            {"id": 2, "value": 210},
            {"id": 3, "value": 300}
        ]
        result = analyze_question(
            question="What changed?",
            rows=after_rows,
            previous_rows=before_rows
        )
        assert result is not None
        assert "comparison" in result
        if result["comparison"]:
            assert "row_delta" in result["comparison"]
    
    def test_compare_versions(self):
        """Test version comparison"""
        before = [{"col1": 100, "col2": "A"}]
        after = [{"col1": 110, "col2": "B"}]
        result = compare_versions(before_rows=before, after_rows=after)
        assert result is not None
        assert "row_delta" in result
    
    def test_compare_versions_empty_before(self):
        """Test version comparison with empty before_rows"""
        result = compare_versions(before_rows=[], after_rows=[{"col": 1}])
        assert result is not None
    
    def test_forecast_metric_with_valid_data(self):
        """Test metric forecasting"""
        rows = [
            {"date": "2024-01-01", "value": 100},
            {"date": "2024-01-02", "value": 110},
            {"date": "2024-01-03", "value": 120},
            {"date": "2024-01-04", "value": 130}
        ]
        result = forecast_metric(
            rows=rows,
            metric_column="value",
            date_column="date",
            horizon=3
        )
        assert result is not None
    
    def test_forecast_metric_auto_detect(self):
        """Test metric forecasting with auto-detect"""
        rows = [
            {"sales": 100},
            {"sales": 150},
            {"sales": 200}
        ]
        result = forecast_metric(
            rows=rows,
            metric_column=None,
            date_column=None,
            horizon=2
        )
        assert result is not None


class TestInputValidation:
    """Test input validation for API endpoints"""
    
    def test_validate_rows_format(self):
        """Test that rows must be list of dicts"""
        with pytest.raises(Exception):
            analyze_question(
                question="Test",
                rows="not_a_list"
            )
    
    def test_validate_empty_question(self):
        """Test that question cannot be empty"""
        # Should still process but with warning
        result = analyze_question(
            question="",
            rows=[{"col": 1}]
        )
        # Should return something, not crash
        assert result is not None
    
    def test_validate_report_sections_structure(self):
        """Test report sections must have correct structure"""
        # Should handle invalid section gracefully
        sections = [None, "invalid", 123]
        result = generate_structured_report_pdf(
            title="Test",
            subtitle="",
            sections=sections
        )
        assert result is not None
        assert isinstance(result, bytes)


# Performance and Robustness Tests
class TestRobustness:
    """Test robustness of error handling"""
    
    def test_large_dataframe_pdf(self):
        """Test PDF generation with large dataframe"""
        data = {f"col{i}": list(range(100)) for i in range(10)}
        df = pl.DataFrame(data)
        result = create_pdf_in_memory("Large dataset test", df)
        assert result is not None
        assert isinstance(result, bytes)
    
    def test_unicode_in_pdf(self):
        """Test PDF generation with unicode characters"""
        df = pl.DataFrame({
            "name": ["Alice", "Bob", "चार्ली", "David"],
            "city": ["New York", "London", "दिल्ली", "Paris"]
        })
        result = create_pdf_in_memory("Unicode test: こんにちは", df)
        assert result is not None
        assert isinstance(result, bytes)
    
    def test_special_characters_in_report(self):
        """Test report generation with special characters"""
        sections = [
            {
                "heading": "Special chars: <>\"'&",
                "rows": [
                    {"label": "Test", "value": "Value <with> \"quotes\" & symbols"}
                ]
            }
        ]
        result = generate_structured_report_pdf(
            title="Special Chars: <>\"'&",
            subtitle="Test",
            sections=sections
        )
        assert result is not None
        assert isinstance(result, bytes)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
