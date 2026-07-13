import os
import re
import math
import logging
from typing import Any, Dict, List, Tuple
import polars as pl
import numpy as np

logger = logging.getLogger(__name__)

class DatasetPreparerService:
    """Core Platform Data Transformation & Chunking Pipeline Service using Polars LazyFrames."""

    def __init__(self, input_path: str, output_path: str):
        self.input_path = input_path
        self.output_path = output_path
        self.file_ext = os.path.splitext(input_path)[1].lower()

    def _get_lazyframe(self) -> pl.LazyFrame:
        if self.file_ext == ".csv":
            # Detect separator
            separator = ","
            try:
                with open(self.input_path, "r", encoding="utf-8", errors="ignore") as f:
                    first_line = f.readline()
                for delim in [",", ";", "\t", "|"]:
                    if first_line.count(delim) > 0:
                        separator = delim
                        break
            except Exception:
                pass
            return pl.scan_csv(self.input_path, separator=separator, ignore_errors=True)
        elif self.file_ext == ".parquet":
            return pl.scan_parquet(self.input_path)
        else:
            # Fallback to loading dataframe and lazying it
            df = pl.read_csv(self.input_path) if self.file_ext == ".csv" else pl.read_excel(self.input_path)
            return df.lazy()

    def _write_lazyframe(self, lf: pl.LazyFrame):
        """Sinks the LazyFrame streamingly to disk to support files larger than RAM."""
        # Clean parent dirs
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        
        # Sinking to parquet is preferred for fast intermediate states
        if self.output_path.endswith(".parquet"):
            lf.sink_parquet(self.output_path)
        elif self.output_path.endswith(".csv"):
            lf.sink_csv(self.output_path)
        else:
            df = lf.collect()
            if self.output_path.endswith(".json"):
                df.write_json(self.output_path)
            else:
                df.write_parquet(self.output_path)

    def execute_transform(self, op_type: str, params: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """Applies a specific data preparation operation on the LazyFrame."""
        lf = self._get_lazyframe()
        columns = params.get("columns", [])
        
        # Calculate shape & schema before
        schema_before = {col: str(dtype) for col, dtype in lf.schema.items()}
        
        ai_explanation = f"Applied '{op_type}' transformation step."

        # Apply specific operations
        if op_type == "remove_missing":
            lf = lf.drop_nulls(subset=columns)
            ai_explanation = f"Removed all rows containing missing values in columns: {', '.join(columns)}."

        elif op_type == "fill_mean":
            # Collect column mean lazily by resolving values first
            df_temp = lf.select([pl.col(c).mean() for c in columns]).collect()
            exprs = []
            for c in columns:
                mean_val = df_temp[c][0]
                exprs.append(pl.col(c).fill_null(mean_val).alias(c))
            lf = lf.with_columns(exprs)
            ai_explanation = f"Imputed null cells with column mean values in columns: {', '.join(columns)}."

        elif op_type == "fill_median":
            df_temp = lf.select([pl.col(c).median() for c in columns]).collect()
            exprs = []
            for c in columns:
                med_val = df_temp[c][0]
                exprs.append(pl.col(c).fill_null(med_val).alias(c))
            lf = lf.with_columns(exprs)
            ai_explanation = f"Imputed null cells with column median values in columns: {', '.join(columns)}."

        elif op_type == "fill_mode":
            exprs = []
            for c in columns:
                # Mode needs collection
                mode_series = lf.select(pl.col(c).mode()).collect().get_column(c)
                mode_val = mode_series[0] if mode_series.len() > 0 else None
                exprs.append(pl.col(c).fill_null(mode_val).alias(c))
            lf = lf.with_columns(exprs)
            ai_explanation = f"Imputed null cells with column mode values in columns: {', '.join(columns)}."

        elif op_type == "forward_fill":
            lf = lf.with_columns([pl.col(c).forward_fill().alias(c) for c in columns])
            ai_explanation = f"Propagated non-null values forward to fill missing slots in columns: {', '.join(columns)}."

        elif op_type == "backward_fill":
            lf = lf.with_columns([pl.col(c).backward_fill().alias(c) for c in columns])
            ai_explanation = f"Propagated non-null values backward to fill missing slots in columns: {', '.join(columns)}."

        elif op_type == "interpolate":
            lf = lf.with_columns([pl.col(c).interpolate().alias(c) for c in columns])
            ai_explanation = f"Applied linear series interpolation to fill gaps in columns: {', '.join(columns)}."

        elif op_type == "duplicate_removal":
            lf = lf.unique(keep="first")
            ai_explanation = "Purged duplicate observations keeping the first encountered row."

        elif op_type == "column_rename":
            rename_map = params.get("rename_map", {}) # {"old": "new"}
            lf = lf.rename(rename_map)
            ai_explanation = f"Renamed columns: {', '.join([f'{k} -> {v}' for k, v in rename_map.items()])}."

        elif op_type == "column_merge":
            sep = params.get("separator", " ")
            out_col = params.get("output_column", "merged_column")
            lf = lf.with_columns(pl.concat_str([pl.col(c) for c in columns], separator=sep).alias(out_col))
            ai_explanation = f"Merged columns ({', '.join(columns)}) into a new column '{out_col}' using delimiter '{sep}'."

        elif op_type == "column_split":
            col = params.get("column")
            sep = params.get("separator", " ")
            # For lazy framing split, we collect sample to see count of parts
            sample_parts = lf.select(pl.col(col).str.split(sep)).head(5).collect().get_column(col)
            non_null_parts = [len(p) for p in sample_parts if p is not None]
            max_parts = max(non_null_parts) if non_null_parts else 2
            exprs = []
            for i in range(max_parts):
                exprs.append(pl.col(col).str.split(sep).list.get(i).alias(f"{col}_part_{i+1}"))
            lf = lf.with_columns(exprs)
            ai_explanation = f"Split column '{col}' into {max_parts} segment columns using delimiter '{sep}'."

        elif op_type == "drop_column":
            lf = lf.drop(columns)
            ai_explanation = f"Excluded columns: {', '.join(columns)} from the dataset."

        elif op_type == "keep_column":
            lf = lf.select(columns)
            ai_explanation = f"Retained only columns: {', '.join(columns)} and dropped all others."

        elif op_type == "cast_type":
            target_type = params.get("target_type", "str")
            type_mapping = {
                "int": pl.Int64, "float": pl.Float64, "str": pl.Utf8, "bool": pl.Boolean
            }
            pl_type = type_mapping.get(target_type, pl.Utf8)
            lf = lf.with_columns([pl.col(c).cast(pl_type, strict=False).alias(c) for c in columns])
            ai_explanation = f"Casted data type of columns: {', '.join(columns)} to target type '{target_type}'."

        elif op_type == "currency_parsing":
            lf = lf.with_columns([
                pl.col(c).str.replace_all(r"[^\d.\-]", "").replace("", None).cast(pl.Float64, strict=False).alias(c)
                for c in columns
            ])
            ai_explanation = f"Parsed string characters and currencies into raw decimal values for columns: {', '.join(columns)}."

        elif op_type == "date_parsing":
            fmt = params.get("date_format", "%Y-%m-%d")
            lf = lf.with_columns([
                pl.col(c).str.to_datetime(format=fmt, strict=False).alias(c) for c in columns
            ])
            ai_explanation = f"Parsed string datetime representation using formatting pattern '{fmt}' in columns: {', '.join(columns)}."

        elif op_type == "trim_spaces":
            lf = lf.with_columns([pl.col(c).str.strip_chars().alias(c) for c in columns])
            ai_explanation = f"Trimmed leading/trailing whitespaces in columns: {', '.join(columns)}."

        elif op_type == "lowercase":
            lf = lf.with_columns([pl.col(c).str.to_lowercase().alias(c) for c in columns])
            ai_explanation = f"Normalized values to lowercase letters in columns: {', '.join(columns)}."

        elif op_type == "uppercase":
            lf = lf.with_columns([pl.col(c).str.to_uppercase().alias(c) for c in columns])
            ai_explanation = f"Normalized values to uppercase letters in columns: {', '.join(columns)}."

        elif op_type == "regex_replace":
            pattern = params.get("pattern", "")
            repl = params.get("replacement", "")
            lf = lf.with_columns([pl.col(c).str.replace_all(pattern, repl).alias(c) for c in columns])
            ai_explanation = f"Replaced text segments matching pattern '{pattern}' with '{repl}' in columns: {', '.join(columns)}."

        elif op_type == "regex_extract":
            pattern = params.get("pattern", "")
            grp = params.get("group_index", 0)
            lf = lf.with_columns([pl.col(c).str.extract(pattern, grp).alias(c) for c in columns])
            ai_explanation = f"Extracted sub-patterns matching group {grp} with regex '{pattern}' in columns: {', '.join(columns)}."

        elif op_type == "find_replace":
            find_val = params.get("find_value", "")
            repl_val = params.get("replacement", "")
            lf = lf.with_columns([pl.col(c).replace(find_val, repl_val).alias(c) for c in columns])
            ai_explanation = f"Substituted occurrences of '{find_val}' with '{repl_val}' in columns: {', '.join(columns)}."

        elif op_type == "outlier_removal":
            for c in columns:
                q1 = lf.select(pl.col(c).quantile(0.25)).collect().item() or 0.0
                q3 = lf.select(pl.col(c).quantile(0.75)).collect().item() or 0.0
                iqr = q3 - q1
                lf = lf.filter((pl.col(c) >= q1 - 1.5 * iqr) & (pl.col(c) <= q3 + 1.5 * iqr))
            ai_explanation = f"Dropped outlier rows beyond 1.5 IQR bounds in columns: {', '.join(columns)}."

        elif op_type == "winsorization":
            lower_q = params.get("lower_quantile", 0.05)
            upper_q = params.get("upper_quantile", 0.95)
            exprs = []
            for c in columns:
                lower = lf.select(pl.col(c).quantile(lower_q)).collect().item() or 0.0
                upper = lf.select(pl.col(c).quantile(upper_q)).collect().item() or 0.0
                exprs.append(
                    pl.when(pl.col(c) < lower).then(lower)
                    .when(pl.col(c) > upper).then(upper)
                    .otherwise(pl.col(c)).alias(c)
                )
            lf = lf.with_columns(exprs)
            ai_explanation = f"Winsorized/capped values outside [{lower_q}, {upper_q}] range in columns: {', '.join(columns)}."

        elif op_type == "minmax_scaling":
            exprs = []
            for c in columns:
                min_v = lf.select(pl.col(c).min()).collect().item() or 0.0
                max_v = lf.select(pl.col(c).max()).collect().item() or 1.0
                exprs.append(((pl.col(c) - min_v) / (max_v - min_v + 1e-9)).alias(c))
            lf = lf.with_columns(exprs)
            ai_explanation = f"Scaled numeric scale to interval [0, 1] in columns: {', '.join(columns)}."

        elif op_type == "standardization":
            exprs = []
            for c in columns:
                mean_v = lf.select(pl.col(c).mean()).collect().item() or 0.0
                std_v = lf.select(pl.col(c).std()).collect().item() or 1.0
                exprs.append(((pl.col(c) - mean_v) / (std_v + 1e-9)).alias(c))
            lf = lf.with_columns(exprs)
            ai_explanation = f"Standardized distribution (mean=0, std=1) in columns: {', '.join(columns)}."

        elif op_type == "one_hot_encoding":
            # Collecting is required to create dummies
            df_temp = lf.collect()
            df_dummies = df_temp.to_dummies(columns)
            lf = df_dummies.lazy()
            ai_explanation = f"Generated one-hot indicator columns for categorical fields: {', '.join(columns)}."

        elif op_type == "label_encoding":
            lf = lf.with_columns([
                pl.col(c).cast(pl.Categorical).to_physical().alias(c) for c in columns
            ])
            ai_explanation = f"Assigned unique integer class labels to values in columns: {', '.join(columns)}."

        elif op_type == "emoji_removal":
            # Replace non-ascii and emojis
            lf = lf.with_columns([
                pl.col(c).str.replace_all(r"[^\x00-\x7F]", "").alias(c) for c in columns
            ])
            ai_explanation = f"Purged unicode emojis and special non-ASCII representations in columns: {', '.join(columns)}."

        elif op_type == "html_removal":
            lf = lf.with_columns([
                pl.col(c).str.replace_all(r"<[^>]*>", "").alias(c) for c in columns
            ])
            ai_explanation = f"Stripped HTML tags and formatting segments in columns: {', '.join(columns)}."

        elif op_type == "whitespace_cleaning":
            lf = lf.with_columns([
                pl.col(c).str.replace_all(r"\s+", " ").alias(c) for c in columns
            ])
            ai_explanation = f"Normalized multi-spaces and whitespace padding in columns: {', '.join(columns)}."

        else:
            logger.warning(f"Operation type '{op_type}' not matched in service pipeline.")

        # Write transformation results to disk streamingly
        self._write_lazyframe(lf)

        # Collect metrics of output
        lf_after = self._get_lazyframe()
        rows_after = lf_after.select(pl.len()).collect().item()
        cols_after = len(lf_after.schema)
        schema_after = {col: str(dtype) for col, dtype in lf_after.schema.items()}

        comparison = {
            "schema_before": schema_before,
            "schema_after": schema_after,
            "rows_after": rows_after,
            "columns_after": cols_after
        }

        return comparison, ai_explanation
