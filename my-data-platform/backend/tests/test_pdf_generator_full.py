import pytest
import polars as pl
from unittest.mock import MagicMock, patch
from pdf_generator import (
    markdown_to_html,
    generate_distribution_base64,
    generate_correlation_matrix_base64,
    generate_ml_visualization_base64,
    create_pdf_in_memory
)

def test_markdown_to_html():
    assert markdown_to_html("") == ""
    assert markdown_to_html(None) == ""
    
    md = "# H1\n## H2\n### H3\n* Item 1\n- Item 2\n\nSome text with **bold** and *italic*."
    html = markdown_to_html(md)
    assert "<h1>H1</h1>" in html
    assert "<h2>H2</h2>" in html
    assert "<h3>H3</h3>" in html
    assert "<ul>" in html
    assert "<li>Item 1</li>" in html
    assert "<li>Item 2</li>" in html
    assert "<strong>bold</strong>" in html
    assert "<em>italic</em>" in html


def test_generate_distribution_base64():
    # Empty / no numeric columns
    df_empty = pl.DataFrame({"a": ["x", "y"]})
    assert generate_distribution_base64(df_empty) == ""
    
    # Fewer than 5 values
    df_small = pl.DataFrame({"a": [1, 2, 3]})
    assert generate_distribution_base64(df_small) == ""

    # Success flow
    df_ok = pl.DataFrame({"a": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]})
    img = generate_distribution_base64(df_ok)
    assert len(img) > 0

    # Exception fallback
    with patch("matplotlib.pyplot.subplots", side_effect=Exception("matplotlib crash")):
        assert generate_distribution_base64(df_ok) == ""


def test_generate_correlation_matrix_base64():
    # Fewer than 2 numeric columns
    df_small = pl.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    assert generate_correlation_matrix_base64(df_small) == ""

    # Success flow
    df_ok = pl.DataFrame({
        "a": [1.0, 2.0, 3.0, 4.0, 5.0],
        "b": [5.0, 4.0, 3.0, 2.0, 1.0]
    })
    img = generate_correlation_matrix_base64(df_ok)
    assert len(img) > 0

    # Exception fallback
    with patch("matplotlib.pyplot.subplots", side_effect=Exception("matplotlib crash")):
        assert generate_correlation_matrix_base64(df_ok) == ""


def test_generate_ml_visualization_base64():
    # Missing target
    df = pl.DataFrame({"a": [1, 2]})
    assert generate_ml_visualization_base64(df, "missing") == ""
    assert generate_ml_visualization_base64(df, None) == ""

    # Classification (binary: 2 classes)
    df_binary = pl.DataFrame({
        "a": [1.0, 2.0, 1.5, 2.5, 3.0, 3.5, 1.0, 2.0, 1.5, 2.5],
        "target": [0, 1, 0, 1, 1, 1, 0, 0, 0, 1]
    })
    img_bin = generate_ml_visualization_base64(df_binary, "target")
    assert len(img_bin) > 0

    # Classification (multi-class: > 2 classes, <= 10 unique integer classes)
    df_multi = pl.DataFrame({
        "a": [1.0, 2.0, 1.5, 2.5, 3.0, 3.5, 1.0, 2.0, 1.5, 2.5],
        "b": [2.0, 3.0, 2.5, 3.5, 4.0, 4.5, 2.0, 3.0, 2.5, 3.5],
        "target": [0, 1, 2, 0, 1, 2, 0, 1, 2, 0]
    })
    img_multi = generate_ml_visualization_base64(df_multi, "target")
    assert len(img_multi) > 0

    # Regression (Float target)
    df_reg = pl.DataFrame({
        "a": [1.0, 2.0, 1.5, 2.5, 3.0, 3.5, 1.0, 2.0, 1.5, 2.5],
        "target": [10.5, 20.0, 15.2, 25.1, 30.0, 35.5, 10.1, 20.2, 15.6, 25.0]
    })
    img_reg = generate_ml_visualization_base64(df_reg, "target")
    assert len(img_reg) > 0

    # Exception fallback
    with patch("sklearn.model_selection.train_test_split", side_effect=Exception("split crash")):
        assert generate_ml_visualization_base64(df_binary, "target") == ""


@patch("pdf_generator.HTML")
def test_create_pdf_in_memory(mock_html):
    mock_instance = MagicMock()
    mock_instance.write_pdf.return_value = b"%PDF-1.4 test bytes"
    mock_html.return_value = mock_instance

    # Test None DataFrame
    pdf = create_pdf_in_memory("Summary", None)
    assert pdf == b"%PDF-1.4 test bytes"

    # Test full dataset
    df = pl.DataFrame({
        "a": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        "b": ["x", "y", "z", "w", "u", "v"]
    })
    pdf_full = create_pdf_in_memory("## AI Summary", df)
    assert pdf_full == b"%PDF-1.4 test bytes"

    # Test exception fallback
    mock_html.side_effect = Exception("Weasyprint error")
    pdf_fail = create_pdf_in_memory("Summary", df)
    assert pdf_fail == b"%PDF-1.4\n%EOF"
