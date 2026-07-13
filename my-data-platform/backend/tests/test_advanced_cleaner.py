import pytest
import polars as pl
from advanced_cleaner import (
    _standardize_column_name,
    _looks_numeric_text,
    advanced_data_cleaning,
    advanced_data_arranging
)

def test_standardize_column_name():
    assert _standardize_column_name("  Total Sales  ") == "total_sales"
    assert _standardize_column_name("User   ID") == "user_id"


def test_looks_numeric_text():
    assert _looks_numeric_text("123.45") is True
    assert _looks_numeric_text("$12,345") is True
    assert _looks_numeric_text("not-numeric") is False


def test_advanced_data_cleaning():
    df = pl.DataFrame({
        "  User ID  ": [1, 1, 2, 3, 4], # Duplicate row for 1
        "Sales Amt": ["$100.50", "$100.50", "€200.00", None, "$150.00"],
        "Val Outlier": [10.0, 10.0, 12.0, 1000.0, 11.0], # 1000.0 is outlier
        "Txt Val": ["   trimmed  ", "   trimmed  ", None, "b", "c"]
    })

    cleaned = advanced_data_cleaning(df)
    
    # 1. Column names standardized
    assert "user_id" in cleaned.columns
    assert "sales_amt" in cleaned.columns
    assert "val_outlier" in cleaned.columns
    assert "txt_val" in cleaned.columns

    # 2. Duplicates removed (1, 1, 2, 3, 4 -> 4 unique rows)
    assert cleaned.height == 4

    # 3. Currency converted to numeric & nulls filled
    assert cleaned["sales_amt"].dtype in [pl.Float64, pl.Float32]
    # The null value in sales_amt should be imputed with the median of valid values (100.50, 200.0) -> 150.25
    assert cleaned["sales_amt"].null_count() == 0

    # 4. Outliers capped (1000.0 capped to upper bound)
    assert cleaned["val_outlier"].max() < 1000.0

    # 5. Text values trimmed and nulls filled with mode ("trimmed")
    assert "trimmed" in cleaned["txt_val"].to_list()
    assert cleaned["txt_val"].null_count() == 0


def test_advanced_data_arranging():
    df = pl.DataFrame({
        "other_val": [5, 4, 3],
        "id_col": [1, 2, 3],
        "date_col": ["2026-01-01 10:00:00", "2026-01-02 11:00:00", "not-a-date"],
        "txt_space": ["a   b", "c   d", "e"]
    })

    arranged, notes = advanced_data_arranging(df)
    
    # Priority column ordering: id first, date next, then others
    assert arranged.columns[0] == "id_col"
    assert arranged.columns[1] == "date_col"
    assert len(notes) > 0
    
    # Trim text whitespaces
    assert arranged["txt_space"].to_list() == ["a b", "c d", "e"]
