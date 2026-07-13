import pytest
import polars as pl
from data_quality import (
    calculate_data_quality_metrics,
    get_quality_report
)

def test_calculate_data_quality_metrics_empty():
    df = pl.DataFrame()
    res = calculate_data_quality_metrics(df)
    assert res["overall_score"] == 0
    assert "Dataset is empty" in res["issues"]
    assert res["row_count"] == 0


def test_calculate_data_quality_metrics_good():
    df = pl.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "val": [10.5, 20.0, 15.2, 10.0, 30.5],
        "label": ["A", "B", "A", "C", "B"]
    })
    
    res = calculate_data_quality_metrics(df)
    assert res["row_count"] == 5
    assert res["column_count"] == 3
    assert res["completeness_score"] == 100.0
    assert res["uniqueness_score"] == 100.0
    assert res["overall_score"] >= 80.0
    assert res["quality_level"] in ["GOOD", "EXCELLENT"]


def test_calculate_data_quality_metrics_issues():
    # Duplicate rows and missing values
    df = pl.DataFrame({
        "id": [1, 1, 2, 3, 4],
        "val": [10.5, 10.5, None, None, 30.5],
        "txt": ["A", "A", "B", None, "B"]
    })

    res = calculate_data_quality_metrics(df)
    assert res["uniqueness_score"] < 100.0 # because row 0 and 1 are duplicate
    assert res["completeness_score"] < 100.0 # because nulls exist
    assert len(res["issues"]) > 0


def test_get_quality_report():
    df = pl.DataFrame({
        "id": [1, 2, 3],
        "val": [10.5, 20.0, 30.0]
    })
    report = get_quality_report(df)
    assert "summary" in report
    assert "scores" in report
    assert "column_analysis" in report
    assert "recommendations" in report
    assert report["summary"]["overall_score"] > 50.0
