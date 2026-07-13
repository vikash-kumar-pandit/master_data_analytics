import pytest
import polars as pl
from unittest.mock import MagicMock, patch
from pdf_generator import (
    markdown_to_html,
    generate_distribution_base64,
    generate_correlation_matrix_base64,
    generate_ml_visualization_base64
)
from report_generator import generate_pdf_in_memory

def test_markdown_to_html():
    md = "# Title\n## Header 2\n### Header 3\n* Item 1\n* Item 2\n\n**Bold Text**"
    html = markdown_to_html(md)
    assert "<h1>Title</h1>" in html
    assert "<h2>Header 2</h2>" in html
    assert "<h3>Header 3</h3>" in html
    assert "<ul>" in html
    assert "<li>Item 1</li>" in html
    assert "<strong>Bold Text</strong>" in html


def test_generate_base64_plots():
    df = pl.DataFrame({
        "val1": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        "val2": [4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
    })
    
    png_dist = generate_distribution_base64(df)
    assert len(png_dist) > 0
    
    png_corr = generate_correlation_matrix_base64(df)
    assert len(png_corr) > 0

    png_ml = generate_ml_visualization_base64(df, "val1")
    assert len(png_ml) > 0


@patch("report_generator.HTML")
def test_generate_pdf_in_memory(mock_html):
    # Mock WeasyPrint HTML compilation
    mock_instance = MagicMock()
    mock_instance.write_pdf.return_value = b"%PDF-1.4 mock bytes"
    mock_html.return_value = mock_instance

    df = pl.DataFrame({
        "val1": [1.0, 2.0, 3.0],
        "val2": [4.0, 5.0, 6.0]
    })
    
    analysis_summary = {
        "rows": 3,
        "cols": 2,
        "category": "Test Data",
        "ai_insights": "### Key Findings\n* Test insights here.",
        "automl": {"best_algorithm": "RandomForest", "accuracy": 0.95}
    }
    
    pdf_bytes = generate_pdf_in_memory(df, analysis_summary)
    assert pdf_bytes == b"%PDF-1.4 mock bytes"
    assert mock_html.called is True
