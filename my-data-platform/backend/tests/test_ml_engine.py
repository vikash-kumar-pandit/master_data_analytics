import pytest
import polars as pl
from unittest.mock import MagicMock, patch
from ml_engine import run_automl_stateless
from ml_advanced import run_nocode_clustering, run_nocode_nlp

def test_run_automl_stateless_classification():
    # 30 rows to allow stable stratified cross-validation splits
    df = pl.DataFrame({
        "feat1": [float(i) for i in range(30)],
        "feat2": [float(i % 5) for i in range(30)],
        "target": [i % 2 for i in range(30)]
    })
    
    res = run_automl_stateless(df, "target")
    assert res["problem_type"] == "classification"
    assert res["engine"] == "sklearn_fallback"
    assert len(res["metrics"]) > 0
    assert "best_algorithm" in res
    assert res["accuracy"] is not None


def test_run_automl_stateless_regression():
    # Regression dataset (continuous numerical target)
    df = pl.DataFrame({
        "feat1": [float(i) for i in range(30)],
        "feat2": [float(i % 5) for i in range(30)],
        "target": [float(10.0 + i * 2.5) for i in range(30)]
    })
    
    res = run_automl_stateless(df, "target")
    assert res["problem_type"] == "regression"
    assert res["r2"] is not None


@patch("importlib.import_module")
def test_run_nocode_clustering(mock_import_module):
    df = pl.DataFrame({
        "x": [1, 2, 3],
        "y": [4, 5, 6]
    })
    
    # Mock return value of assign_model as a pandas dataframe
    import pandas as pd
    mock_pandas = pd.DataFrame({
        "x": [1, 2, 3],
        "y": [4, 5, 6],
        "Cluster": ["Cluster 0", "Cluster 1", "Cluster 0"]
    })

    # Create a mock module with the required functions
    mock_module = MagicMock()
    mock_module.assign_model.return_value = mock_pandas
    mock_import_module.return_value = mock_module
    
    res = run_nocode_clustering(df, num_clusters=2)
    assert "Cluster" in res.columns
    assert res.height == 3


@patch("ml_advanced._get_zero_shot_classifier")
def test_run_nocode_nlp(mock_get_classifier):
    df = pl.DataFrame({
        "text": ["I love this product", "I hate the service"],
        "id": [1, 2]
    })
    
    mock_classifier = MagicMock()
    # Mock the return values for zero-shot classification items
    mock_classifier.side_effect = lambda text, candidate_labels: {
        "labels": ["positive", "negative"],
        "scores": [0.9, 0.1]
    }
    mock_get_classifier.return_value = mock_classifier
    
    res = run_nocode_nlp(df, "text", ["positive", "negative"])
    assert "AI_Text_Category" in res.columns
    assert "AI_Text_Category_Confidence" in res.columns
    assert res["AI_Text_Category"].to_list() == ["positive", "positive"]
