import pytest
import sys
from unittest.mock import MagicMock, patch
import numpy as np

# Mock SHAP module globally for tests to prevent import errors and speed up execution
sys.modules["shap"] = MagicMock()

import polars as pl
from analytics_engine import (
    analyze_question,
    forecast_metric,
    _to_dataframe,
    _validate_rows_input
)
from xai_engine import generate_shap_explanations, _is_classification_target

def test_to_dataframe_empty():
    assert _to_dataframe([]).height == 0
    assert _to_dataframe(None).height == 0


def test_validate_rows_input():
    with pytest.raises(TypeError):
        _validate_rows_input("not-a-list")
    with pytest.raises(TypeError):
        _validate_rows_input([1, 2, 3])


def test_forecast_metric():
    rows = [
        {"date": "2026-01-01", "sales": 100.0},
        {"date": "2026-01-02", "sales": 120.0},
        {"date": "2026-01-03", "sales": 130.0},
        {"date": "2026-01-04", "sales": 150.0}
    ]
    res = forecast_metric(rows=rows, horizon=3, metric_column="sales")
    assert "forecast" in res
    assert len(res["forecast"]) == 3
    assert res["model_stats"]["slope"] > 0
    assert res["model_stats"]["r_squared"] > 0.8


def test_analyze_question_predictive():
    rows = [
        {"date": "2026-01-01", "sales": 100.0},
        {"date": "2026-01-02", "sales": 120.0},
        {"date": "2026-01-03", "sales": 130.0},
        {"date": "2026-01-04", "sales": 150.0}
    ]
    res = analyze_question(question="forecast next 3 days", rows=rows)
    assert res["intent"] == "predictive"
    assert "forecast" in res


def test_is_classification_target():
    import pandas as pd
    s1 = pd.Series(["A", "B", "A", "C"])
    assert _is_classification_target(s1) is True

    # 30 unique items to ensure classification is False (threshold = 20)
    s2 = pd.Series(list(range(30)))
    assert _is_classification_target(s2) is False


def test_generate_shap_explanations():
    # Mock shap explainer output
    mock_explainer_instance = MagicMock()
    mock_explainer_instance.shap_values.return_value = np.array([
        [0.1, 0.2],
        [0.05, 0.15],
        [0.12, 0.18]
    ])
    sys.modules["shap"].TreeExplainer.return_value = mock_explainer_instance

    rows = [
        {"feat1": 1.0, "feat2": 2.0, "target": 10.0},
        {"feat1": 1.5, "feat2": 2.5, "target": 15.0},
        {"feat1": 2.0, "feat2": 3.0, "target": 20.0}
    ]
    
    res = generate_shap_explanations(rows, "target")
    assert res["target_column"] == "target"
    assert len(res["global_importance"]) > 0
    assert len(res["local_explanation"]) > 0
    assert res["total_rows_used"] == 3
