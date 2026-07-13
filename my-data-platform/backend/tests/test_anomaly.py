import pytest
import polars as pl
from anomaly_detector import (
    detect_anomalies_iqr,
    detect_anomalies_zscore,
    detect_anomalies_isolation_forest,
    compute_dataset_anomalies
)

def test_anomaly_detection_iqr():
    df = pl.DataFrame({
        "num": [10, 12, 11, 13, 14, 100, 12, 11, 10, -50], # 100 and -50 are outliers
        "txt": ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]
    })
    
    # Test numerical
    res = detect_anomalies_iqr(df, "num")
    assert res["method"] == "iqr"
    assert res["anomaly_count"] == 2
    assert res["anomaly_indices"] == [5, 9]
    
    # Test string column edge case
    res_txt = detect_anomalies_iqr(df, "txt")
    assert res_txt["anomaly_count"] == 0


def test_anomaly_detection_zscore():
    df = pl.DataFrame({
        "num": [10, 10, 10, 10, 10, 10, 10, 10, 10, 1000], # 1000 is an extreme outlier
        "zero_var": [5, 5, 5, 5, 5, 5, 5, 5, 5, 5],
        "txt": ["a"] * 10
    })
    
    res = detect_anomalies_zscore(df, "num", threshold=2.0)
    assert res["anomaly_count"] == 1
    assert res["anomaly_indices"] == [9]

    # Test zero variance
    res_zero = detect_anomalies_zscore(df, "zero_var")
    assert res_zero["anomaly_count"] == 0
    assert res_zero.get("note") == "zero_std"

    # Test non-numeric
    res_txt = detect_anomalies_zscore(df, "txt")
    assert res_txt["anomaly_count"] == 0


def test_anomaly_detection_isolation_forest():
    df = pl.DataFrame({
        "num1": [1.0, 1.1, 1.0, 1.2, 1.1, 10.0, 1.0, 1.1, 1.0, 1.2],
        "num2": [2.0, 2.1, 2.0, 2.2, 2.1, 20.0, 2.0, 2.1, 2.0, 2.2],
        "txt": ["a"] * 10
    })

    res = detect_anomalies_isolation_forest(df, ["num1", "num2"], contamination=0.1)
    assert res["method"] == "isolation_forest"
    assert res["anomaly_count"] >= 1
    assert 5 in res["anomaly_indices"]

    # Test empty or string column inputs
    res_empty = detect_anomalies_isolation_forest(df, [])
    assert res_empty["anomaly_count"] == 0
    
    res_txt = detect_anomalies_isolation_forest(df, ["txt"])
    assert res_txt["anomaly_count"] == 0


def test_compute_dataset_anomalies():
    df = pl.DataFrame({
        "val1": [10, 11, 12, 10, 100],
        "val2": [20, 21, 22, 20, -50],
        "txt": ["x"] * 5
    })
    
    res = compute_dataset_anomalies(df)
    assert res["overall"]["anomaly_count"] == 2
    assert "val1" in res["columns"]
    assert "val2" in res["columns"]
    
    # Test empty df
    empty_df = pl.DataFrame()
    res_empty = compute_dataset_anomalies(empty_df)
    assert res_empty["overall"]["anomaly_count"] == 0
