import math

import polars as pl


def _standardize_column_name(column_name: str) -> str:
    name = column_name.strip().lower()
    name = "_".join(name.split())
    return name


def _looks_numeric_text(sample: str) -> bool:
    if not sample:
        return False
    allowed = set("0123456789.,$€₹£+- ")
    return all(char in allowed for char in sample)


def _safe_quantile(dataframe: pl.DataFrame, column_name: str, quantile: float):
    value = dataframe.select(pl.col(column_name).quantile(quantile)).item()
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def _impute_text_mode(dataframe: pl.DataFrame, column_name: str) -> pl.DataFrame:
    mode_series = dataframe.get_column(column_name).drop_nulls().mode()
    fill_value = mode_series.item(0) if len(mode_series) > 0 else "Unknown"
    return dataframe.with_columns(pl.col(column_name).fill_null(fill_value).alias(column_name))


def advanced_data_cleaning(dataframe: pl.DataFrame) -> pl.DataFrame:
    # 1) Standardize column names
    renamed = {_column: _standardize_column_name(_column) for _column in dataframe.columns}
    cleaned = dataframe.rename(renamed)

    # 2) Light text cleaning
    utf8_columns = [name for name, dtype in zip(cleaned.columns, cleaned.dtypes) if dtype == pl.Utf8]
    if utf8_columns:
        cleaned = cleaned.with_columns(
            [
                pl.col(column)
                .str.strip_chars()
                .str.replace_all(r"\s+", " ")
                .alias(column)
                for column in utf8_columns
            ]
        )

    # 3) Remove duplicates
    cleaned = cleaned.unique(keep="first")

    # 4) Detect currency/number-like text and cast to numeric
    for column_name, dtype in zip(cleaned.columns, cleaned.dtypes):
        if dtype != pl.Utf8:
            continue

        sample_values = cleaned.get_column(column_name).drop_nulls().head(5).to_list()
        if not sample_values:
            continue

        if not all(_looks_numeric_text(str(value)) for value in sample_values):
            continue

        cleaned = cleaned.with_columns(
            pl.col(column_name)
            .str.replace_all(r"[^\d.\-]", "")
            .replace("", None)
            .cast(pl.Float64, strict=False)
            .alias(column_name)
        )

    # 5) Outlier capping (IQR)
    numeric_columns = [
        name
        for name, dtype in zip(cleaned.columns, cleaned.dtypes)
        if dtype in {pl.Int64, pl.Int32, pl.Float64, pl.Float32}
    ]

    for column_name in numeric_columns:
        q1 = _safe_quantile(cleaned, column_name, 0.25)
        q3 = _safe_quantile(cleaned, column_name, 0.75)
        if q1 is None or q3 is None:
            continue

        iqr = q3 - q1
        lower_bound = q1 - (1.5 * iqr)
        upper_bound = q3 + (1.5 * iqr)

        cleaned = cleaned.with_columns(
            pl.when(pl.col(column_name) > upper_bound)
            .then(pl.lit(upper_bound))
            .when(pl.col(column_name) < lower_bound)
            .then(pl.lit(lower_bound))
            .otherwise(pl.col(column_name))
            .alias(column_name)
        )

    # 6) Smart missing value imputation
    for column_name, dtype in zip(cleaned.columns, cleaned.dtypes):
        null_count = cleaned.get_column(column_name).null_count()
        if null_count == 0:
            continue

        if dtype in {pl.Int64, pl.Int32, pl.Float64, pl.Float32}:
            # Use median to fill missing numeric values
            col_series = cleaned.get_column(column_name)
            median_val = col_series.median()
            if median_val is not None:
                cleaned = cleaned.with_columns(pl.col(column_name).fill_null(median_val).alias(column_name))
        elif dtype == pl.Utf8:
            cleaned = _impute_text_mode(cleaned, column_name)

    return cleaned


def advanced_data_arranging(dataframe: pl.DataFrame) -> tuple[pl.DataFrame, list[str]]:
    arranged = dataframe.clone()
    notes: list[str] = []

    # 1) Keep business-friendly column order: id/date/name first, remaining alphabetic.
    priority_prefixes = ("id", "date", "time", "timestamp", "name", "product", "category")
    priority_columns = [
        column_name
        for column_name in arranged.columns
        if any(column_name.lower().startswith(prefix) for prefix in priority_prefixes)
    ]
    trailing_columns = sorted([column_name for column_name in arranged.columns if column_name not in priority_columns])
    ordered_columns = priority_columns + trailing_columns

    if ordered_columns != arranged.columns:
        arranged = arranged.select(ordered_columns)
        notes.append("Columns reordered for readable business layout.")

    # 2) Normalize text whitespace.
    utf8_columns = [name for name, dtype in zip(arranged.columns, arranged.dtypes) if dtype == pl.Utf8]
    if utf8_columns:
        arranged = arranged.with_columns(
            [
                pl.col(column_name)
                .str.strip_chars()
                .str.replace_all(r"\s+", " ")
                .alias(column_name)
                for column_name in utf8_columns
            ]
        )
        notes.append("Text values trimmed and extra spaces normalized.")

    # 3) Standardize date-like columns to ISO strings where parsing succeeds.
    date_like_columns = [
        column_name
        for column_name in utf8_columns
        if any(token in column_name.lower() for token in ("date", "time", "timestamp"))
    ]
    for column_name in date_like_columns:
        arranged = arranged.with_columns(
            pl.when(pl.col(column_name).str.to_datetime(strict=False).is_not_null())
            .then(pl.col(column_name).str.to_datetime(strict=False).dt.strftime("%Y-%m-%d %H:%M:%S"))
            .otherwise(pl.col(column_name))
            .alias(column_name)
        )

    if date_like_columns:
        notes.append("Date/time columns converted to standard ISO display where possible.")

    # 4) Sort rows by the best available business key for stable browsing.
    sort_candidates = []
    for preferred in ("id", "date", "time", "name", "product"):
        sort_candidates.extend([column_name for column_name in arranged.columns if preferred in column_name.lower()])

    if not sort_candidates and arranged.columns:
        sort_candidates = [arranged.columns[0]]

    if sort_candidates:
        sort_column = sort_candidates[0]
        arranged = arranged.sort(sort_column, nulls_last=True)
        notes.append(f"Rows sorted by '{sort_column}' for consistent row navigation.")

    return arranged, notes
