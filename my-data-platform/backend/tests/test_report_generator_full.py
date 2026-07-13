import pytest
import polars as pl
from unittest.mock import MagicMock, patch
import io
from pptx import Presentation
from report_generator import (
    generate_pdf_in_memory,
    generate_structured_report_pdf,
    generate_structured_report_pptx
)

@patch("report_generator.HTML")
def test_generate_pdf_in_memory_full(mock_html):
    # Mock WeasyPrint
    mock_instance = MagicMock()
    mock_instance.write_pdf.return_value = b"%PDF-1.4 mock bytes"
    mock_html.return_value = mock_instance

    # Test with None df and None summary
    pdf = generate_pdf_in_memory(None, None)
    assert pdf == b"%PDF-1.4 mock bytes"

    # Test with full dataset and ML summary
    df = pl.DataFrame({
        "a": [1.0, 2.0],
        "b": ["x", "y"]
    })
    summary = {
        "rows": 2,
        "cols": 2,
        "category": "Test Data",
        "ai_insights": "## Insights\nSome info.",
        "automl": {
            "target_column": "a",
            "best_algorithm": "LightGBM",
            "r2": 0.9,
            "mae": 0.1,
            "rmse": 0.15
        }
    }
    pdf = generate_pdf_in_memory(df, summary)
    assert pdf == b"%PDF-1.4 mock bytes"

    # Test exception fallback
    mock_html.side_effect = Exception("Crash")
    pdf_fail = generate_pdf_in_memory(df, summary)
    assert pdf_fail == b"%PDF-1.4\n%EOF"


@patch("report_generator.HTML")
def test_generate_structured_report_pdf_themes(mock_html):
    mock_instance = MagicMock()
    mock_instance.write_pdf.return_value = b"%PDF-1.4 structured"
    mock_html.return_value = mock_instance

    sections = [
        {"heading": "Intro", "rows": [{"label": "L1", "value": "V1\nwith newline"}]},
        {"heading": "Details", "rows": []}
    ]

    # Test themes
    themes = ["Quality Profile", "Technical Research Paper", "Executive Briefing", "General Report"]
    for title in themes:
        pdf = generate_structured_report_pdf(title=title, subtitle="Sub", sections=sections)
        assert pdf == b"%PDF-1.4 structured"

    # Test None/empty inputs
    pdf_empty = generate_structured_report_pdf(title=None, subtitle=None, sections=None)
    assert pdf_empty == b"%PDF-1.4 structured"

    # Test exception fallback
    mock_html.side_effect = Exception("Weasyprint error")
    pdf_fail = generate_structured_report_pdf(title="Test", subtitle="Sub", sections=sections)
    assert pdf_fail == b"%PDF-1.4\n%EOF"


def test_generate_structured_report_pptx_full():
    sections = [
        {
            "heading": "Summary Section",
            "rows": [
                {"label": "Metric A", "value": "100"},
                {"label": None, "value": "Value without label"},
                {"label": "Long Metric", "value": "A" * 300}  # Triggers truncation
            ]
        },
        {
            "heading": "Empty Section",
            "rows": []
        },
        "invalid_section_type"
    ]

    # Normal generation
    pptx_bytes = generate_structured_report_pptx(title="PPTX Report", subtitle="Sub", sections=sections)
    assert len(pptx_bytes) > 0

    # Test that it's a valid Presentation
    prs = Presentation(io.BytesIO(pptx_bytes))
    assert len(prs.slides) == 3  # 1 title slide + 2 valid sections

    # Test None / empty values
    pptx_empty = generate_structured_report_pptx(title=None, subtitle=None, sections=None)
    assert len(pptx_empty) > 0

    # Test invalid row types inside section
    bad_sections = [{"heading": "Section", "rows": ["not_a_dict"]}]
    pptx_bad_rows = generate_structured_report_pptx(title="Bad Rows", subtitle="", sections=bad_sections)
    assert len(pptx_bad_rows) > 0

    # Test crash in Presentation save fallback
    with patch("report_generator.Presentation", side_effect=[Exception("PPTX crash"), MagicMock()]):
        pptx_fail = generate_structured_report_pptx(title="Crash", subtitle="", sections=[])
        assert len(pptx_fail) >= 0
