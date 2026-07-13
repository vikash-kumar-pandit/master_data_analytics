from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl


def detect_anomalies_iqr(
    dataframe: pl.DataFrame,
    column_name: str,
    multiplier: float = 1.5,
) -> dict[str, Any]:
    series = dataframe[column_name]
    if series.dtype not in {pl.Int64, pl.Int32, pl.Float64, pl.Float32}:
        return {"anomaly_count": 0, "anomaly_indices": [], "method": "iqr"}

    q1 = float(series.quantile(0.25) or 0)
    q3 = float(series.quantile(0.75) or 0)
    iqr = q3 - q1
    lower = q1 - multiplier * iqr
    upper = q3 + multiplier * iqr

    mask = (series < lower) | (series > upper)
    indices = [i for i, is_anomaly in enumerate(mask.to_list()) if is_anomaly]
    return {
        "column": column_name,
        "method": "iqr",
        "q1": q1,
        "q3": q3,
        "iqr": iqr,
        "lower_bound": lower,
        "upper_bound": upper,
        "anomaly_count": len(indices),
        "anomaly_indices": indices[:100],
        "anomaly_pct": round((len(indices) / max(1, series.len())) * 100, 2),
    }


def detect_anomalies_zscore(
    dataframe: pl.DataFrame,
    column_name: str,
    threshold: float = 3.0,
) -> dict[str, Any]:
    series = dataframe[column_name]
    if series.dtype not in {pl.Int64, pl.Int32, pl.Float64, pl.Float32}:
        return {"anomaly_count": 0, "anomaly_indices": [], "method": "zscore"}

    values = series.drop_nulls().to_numpy()
    if len(values) == 0:
        return {"anomaly_count": 0, "anomaly_indices": [], "method": "zscore"}

    mean = float(np.mean(values))
    std = float(np.std(values))
    if std == 0:
        return {"anomaly_count": 0, "anomaly_indices": [], "method": "zscore", "note": "zero_std"}

    z = np.abs((values - mean) / std)
    anomaly_mask = z > threshold
    anomaly_count = int(np.sum(anomaly_mask))

    all_indices = [i for i, v in enumerate(series.to_list()) if v is not None]
    anomaly_indices = [
        all_indices[i] for i, is_anomaly in enumerate(anomaly_mask) if is_anomaly
    ][:100]

    return {
        "column": column_name,
        "method": "zscore",
        "mean": mean,
        "std": std,
        "threshold": threshold,
        "anomaly_count": anomaly_count,
        "anomaly_indices": anomaly_indices,
        "anomaly_pct": round((anomaly_count / max(1, len(values))) * 100, 2),
    }


def detect_anomalies_isolation_forest(
    dataframe: pl.DataFrame,
    column_names: list[str],
    contamination: float = 0.1,
) -> dict[str, Any]:
    try:
        from sklearn.ensemble import IsolationForest
    except ImportError as exc:
        raise ImportError(
            "scikit-learn is not installed. Install it with `pip install scikit-learn` to enable isolation forest anomaly detection."
        ) from exc

    if not column_names:
        return {"anomaly_count": 0, "anomaly_indices": [], "method": "isolation_forest"}

    df = dataframe.select(column_names).drop_nulls()
    if df.height == 0:
        return {"anomaly_count": 0, "anomaly_indices": [], "method": "isolation_forest"}

    numeric_cols = [
        name for name, dtype in zip(df.columns, df.dtypes)
        if dtype in {pl.Int64, pl.Int32, pl.Float64, pl.Float32}
    ]
    if not numeric_cols:
        return {"anomaly_count": 0, "anomaly_indices": [], "method": "isolation_forest"}

    x = df.select(numeric_cols).fill_null(0).to_numpy()
    model = IsolationForest(contamination=min(max(contamination, 0.01), 0.5), random_state=42)
    preds = model.fit_predict(x)
    anomaly_mask = preds == -1
    anomaly_count = int(np.sum(anomaly_mask))

    # Fast check using Polars expression to extract row indexes without row loop iterators
    non_null_mask = dataframe[numeric_cols[0]].is_not_null()
    original_indices = [i for i, val in enumerate(non_null_mask.to_list()) if val]
    anomaly_indices = [
        original_indices[i] for i, is_anomaly in enumerate(anomaly_mask) if is_anomaly
    ][:200]

    return {
        "method": "isolation_forest",
        "columns_used": numeric_cols,
        "contamination": contamination,
        "anomaly_count": anomaly_count,
        "anomaly_indices": anomaly_indices,
        "anomaly_pct": round((anomaly_count / max(1, len(preds))) * 100, 2),
    }


def compute_dataset_anomalies(
    dataframe: pl.DataFrame,
    numeric_columns: list[str] | None = None,
) -> dict[str, Any]:
    if dataframe.height == 0:
        return {"overall": {"anomaly_count": 0, "anomaly_pct": 0.0}, "columns": {}}

    if numeric_columns is None:
        numeric_columns = [
            name for name, dtype in zip(dataframe.columns, dataframe.dtypes)
            if dtype in {pl.Int64, pl.Int32, pl.Float64, pl.Float32}
        ]

    column_results: dict[str, Any] = {}
    total_anomaly_cells = 0
    total_cells = 0

    for column_name in numeric_columns:
        iqr_result = detect_anomalies_iqr(dataframe, column_name)
        zscore_result = detect_anomalies_zscore(dataframe, column_name)

        primary = iqr_result if iqr_result["anomaly_count"] >= zscore_result["anomaly_count"] else zscore_result
        column_results[column_name] = {
            "anomaly_count": primary["anomaly_count"],
            "anomaly_pct": primary["anomaly_pct"],
            "method": primary["method"],
            "bounds": {
                "lower": primary.get("lower_bound") or primary.get("mean", 0) - 3 * primary.get("std", 1),
                "upper": primary.get("upper_bound") or primary.get("mean", 0) + 3 * primary.get("std", 1),
            },
        }
        total_anomaly_cells += primary["anomaly_count"]
        total_cells += dataframe[column_name].len()

    overall_pct = round((total_anomaly_cells / max(1, total_cells)) * 100, 2)
    return {
        "overall": {
            "anomaly_count": total_anomaly_cells,
            "anomaly_pct": overall_pct,
            "numeric_columns_scanned": len(numeric_columns),
        },
        "columns": column_results,
    }
