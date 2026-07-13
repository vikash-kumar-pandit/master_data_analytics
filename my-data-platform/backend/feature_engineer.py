import logging
import polars as pl

logger = logging.getLogger("feature_engineer")

def auto_feature_engineer(dataframe: pl.DataFrame) -> tuple[pl.DataFrame, list[str]]:
    """
    Automatically generates new analytical features from existing raw data
    using highly optimized Polars expressions.
    """
    engineered_df = dataframe.clone()
    notes: list[str] = []

    # 1. Date/Time Feature Extraction (सीज़नलिटी और ट्रेंड्स के लिए)
    date_columns = [
        name for name, dtype in zip(engineered_df.columns, engineered_df.dtypes)
        if isinstance(dtype, (pl.Date, pl.Datetime))
    ]

    for col in date_columns:
        engineered_df = engineered_df.with_columns([
            pl.col(col).dt.year().alias(f"{col}_Year"),
            pl.col(col).dt.month().alias(f"{col}_Month"),
            pl.col(col).dt.weekday().alias(f"{col}_Weekday"),
            # Polars weekday: 6 = Saturday, 7 = Sunday
            pl.col(col).dt.weekday().is_in([6, 7]).cast(pl.Int32).alias(f"{col}_Is_Weekend")
        ])
        notes.append(f"Extracted Year, Month, Weekday, and Weekend indicators from '{col}'.")

    # 2. Text Feature Engineering (टेक्स्ट डेटा की गहराई मापने के लिए)
    utf8_columns = [
        name for name, dtype in zip(engineered_df.columns, engineered_df.dtypes) 
        if dtype == pl.Utf8
    ]
    
    for col in utf8_columns:
        # Check average length of the column's values
        try:
            avg_length = engineered_df.select(pl.col(col).str.len_chars().mean()).item()
            if avg_length is not None and avg_length > 20:
                engineered_df = engineered_df.with_columns([
                    pl.col(col).str.len_chars().alias(f"{col}_Length"),
                    pl.col(col).str.count_matches(r"\?|\!").alias(f"{col}_Punctuation_Count")
                ])
                notes.append(f"Generated text analytics features for '{col}' (Length & Punctuation).")
        except Exception as e:
            logger.debug(f"Skipping text analysis for column {col}: {e}")

    # 3. Financial/Business Ratios (बिज़नेस लॉजिक)
    cols_lower = {c.lower(): c for c in engineered_df.columns}
    
    sales_col = cols_lower.get("sales") or cols_lower.get("revenue")
    cost_col = cols_lower.get("cost") or cols_lower.get("discount")
    
    if sales_col and cost_col:
        try:
            # Profit / Sales Ratio (सुरक्षित डिवीज़न)
            engineered_df = engineered_df.with_columns(
                (
                    (pl.col(sales_col) - pl.col(cost_col)) / 
                    pl.when(pl.col(sales_col) == 0).then(1).otherwise(pl.col(sales_col))
                ).alias("Auto_Profit_Margin_Ratio")
            )
            notes.append(f"Calculated 'Auto_Profit_Margin_Ratio' using '{sales_col}' and '{cost_col}'.")
        except Exception as e:
            logger.warning(f"Could not calculate financial ratios: {e}")

    return engineered_df, notes
