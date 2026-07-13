from __future__ import annotations

from typing import Any

import polars as pl


class ValidationError(Exception):
    pass


def validate_upload_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValidationError("Payload must be a JSON object")
    rows = payload.get("rows", [])
    if not isinstance(rows, list) or len(rows) == 0:
        raise ValidationError("Payload must contain a non-empty 'rows' array")
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValidationError(f"Row {i} must be an object")
    return payload


def validate_numeric_column(dataframe, column_name: str) -> None:
    if column_name not in dataframe.columns:
        raise ValidationError(f"Column '{column_name}' not found in dataset")
    dtype = dataframe[column_name].dtype
    if dtype not in {pl.Int64, pl.Int32, pl.Float64, pl.Float32, pl.Int8, pl.Int16, pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64}:
        raise ValidationError(f"Column '{column_name}' must be numeric, got {dtype}")


def validate_class_balance(dataframe, target_column: str, min_samples_per_class: int = 5) -> dict[str, Any]:
    if target_column not in dataframe.columns:
        raise ValidationError(f"Target column '{target_column}' not found")
    counts = dataframe[target_column].value_counts().sort("count", descending=True)
    imbalance = {}
    for row in counts.iter_rows(named=True):
        label = str(row[target_column])
        count = int(row["count"])
        if count < min_samples_per_class:
            imbalance[label] = count
    return {
        "is_balanced": len(imbalance) == 0,
        "imbalanced_classes": imbalance,
        "class_distribution": {str(r[target_column]): int(r["count"]) for r in counts.iter_rows(named=True)},
    }
