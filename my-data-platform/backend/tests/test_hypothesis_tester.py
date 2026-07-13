import polars as pl
import numpy as np
from hypothesis_tester import run_automated_ab_test

def test_run_automated_ab_test_success_significant():
    # Group A: Mean 10.0, Sample 100
    # Group B: Mean 15.0, Sample 100
    np.random.seed(42)
    group_a_values = np.random.normal(loc=10.0, scale=1.0, size=100)
    group_b_values = np.random.normal(loc=15.0, scale=1.0, size=100)
    
    df = pl.DataFrame({
        "sales": list(group_a_values) + list(group_b_values),
        "store": ["Store A"] * 100 + ["Store B"] * 100
    })
    
    result = run_automated_ab_test(df, "sales", "store")
    
    assert result["status"] == "success"
    assert result["is_statistically_significant"] is True
    assert "🚀 Statistically Proven" in result["business_insight"]
    assert result["p_value"] < 0.05
    assert result["group_a"]["name"] == "Store A" or result["group_b"]["name"] == "Store A"

def test_run_automated_ab_test_success_non_significant():
    # Group A: Mean 10.0, Sample 100
    # Group B: Mean 10.1 (very close), Sample 100
    np.random.seed(42)
    group_a_values = np.random.normal(loc=10.0, scale=1.0, size=100)
    group_b_values = np.random.normal(loc=10.1, scale=1.0, size=100)
    
    df = pl.DataFrame({
        "sales": list(group_a_values) + list(group_b_values),
        "store": ["Store A"] * 100 + ["Store B"] * 100
    })
    
    result = run_automated_ab_test(df, "sales", "store")
    
    assert result["status"] == "success"
    assert result["is_statistically_significant"] is False
    assert "⚖️ No Clear Winner" in result["business_insight"]
    assert result["p_value"] >= 0.05

def test_run_automated_ab_test_small_sample():
    # Group A: Sample 10
    # Group B: Sample 10
    df = pl.DataFrame({
        "sales": [10.0] * 10 + [12.0] * 10,
        "store": ["Store A"] * 10 + ["Store B"] * 10
    })
    
    result = run_automated_ab_test(df, "sales", "store")
    assert "warning" in result
    assert "too small" in result["warning"]

def test_run_automated_ab_test_invalid_cols():
    df = pl.DataFrame({
        "sales": [10.0] * 50,
        "store": ["Store A"] * 50
    })
    result = run_automated_ab_test(df, "revenue", "store") # invalid metric
    assert "error" in result
