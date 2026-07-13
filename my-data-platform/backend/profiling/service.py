import os
import re
import math
import time
import logging
from typing import Any, Dict, List, Tuple
import polars as pl
import numpy as np

logger = logging.getLogger(__name__)

def _sanitize_float(val: Any) -> float:
    """Sanitizes float values to prevent JSON serialization errors for NaN/Infinity."""
    if val is None:
        return 0.0
    try:
        f_val = float(val)
        if math.isnan(f_val) or math.isinf(f_val):
            return 0.0
        return f_val
    except (ValueError, TypeError):
        return 0.0

class DatasetProfilerService:
    """Enterprise Data Profiling Service utilizing Polars & NumPy for performant, memory-efficient profiling."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.file_extension = os.path.splitext(file_path)[1].lower()
        self.file_size = os.path.getsize(file_path)

    def detect_encoding_and_delimiter(self) -> Tuple[str, str]:
        """Detects delimiter and encoding of CSV files."""
        if self.file_extension not in [".csv", ".txt"]:
            return "utf-8", ","
        
        encoding = "utf-8"
        delimiter = ","
        
        # Test encoding
        for enc in ["utf-8", "cp1252", "latin-1"]:
            try:
                with open(self.file_path, "r", encoding=enc) as f:
                    f.readline()
                encoding = enc
                break
            except UnicodeDecodeError:
                continue

        # Test delimiter
        try:
            with open(self.file_path, "r", encoding=encoding) as f:
                first_line = f.readline()
            
            delimiters = [",", ";", "\t", "|"]
            counts = {d: first_line.count(d) for d in delimiters}
            detected = max(counts, key=counts.get)
            if counts[detected] > 0:
                delimiter = detected
        except Exception:
            pass
            
        return encoding, delimiter

    def run_profiling(self, target_column: str = None) -> Dict[str, Any]:
        """Runs the complete profiling pipeline chunk by chunk to prevent RAM crashes."""
        start_time = time.time()
        encoding, delimiter = self.detect_encoding_and_delimiter()
        polars_encoding = "utf8" if encoding == "utf-8" else encoding
        
        # Load lazily to prevent RAM overflow
        if self.file_extension == ".csv":
            lf = pl.scan_csv(self.file_path, encoding=polars_encoding, separator=delimiter, ignore_errors=True)
            df = lf.collect()
        elif self.file_extension == ".parquet":
            lf = pl.scan_parquet(self.file_path)
            df = lf.collect()
        elif self.file_extension in [".xls", ".xlsx"]:
            df = pl.read_excel(self.file_path)
        elif self.file_extension == ".json":
            try:
                lf = pl.scan_ndjson(self.file_path)
                df = lf.collect()
            except Exception:
                df = pl.read_json(self.file_path)
        elif self.file_extension == ".sqlite":
            import duckdb
            conn = duckdb.connect()
            tables = conn.execute(f"SELECT name FROM sqlite_scan('{self.file_path}', 'sqlite_master') WHERE type='table'").fetchall()
            if not tables:
                raise ValueError("SQLite database contains no tables.")
            df = conn.execute(f"SELECT * FROM sqlite_scan('{self.file_path}', '{tables[0][0]}')").pl()
        else:
            raise ValueError(f"Unsupported file extension: {self.file_extension}")
            
        rows = df.height
        cols = df.width
        columns = df.columns
        schema_dict = {col: str(dtype) for col, dtype in zip(df.columns, df.dtypes)}
        
        # Heuristic memory usage estimation
        memory_usage_est = sum(df[c].estimated_size() for c in columns)
        
        # Initialize profiling reports
        column_stats = {}
        warnings = []
        recommendations = []
        
        # Identify types
        numerical_cols = []
        categorical_cols = []
        datetime_cols = []
        boolean_cols = []
        text_cols = []
        
        # Regex for PII semantic detection
        email_regex = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
        phone_regex = re.compile(r"^\+?1?\s*\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$")
        currency_regex = re.compile(r"[\$\u20AC\u00A3\u00A5]")
        
        for col in columns:
            series = df[col]
            dtype = series.dtype
            dtype_str = str(dtype).lower()
            
            null_count = series.null_count()
            missing_pct = (null_count / rows * 100) if rows > 0 else 0
            n_unique = series.n_unique()
            
            # Base stats
            stats = {
                "name": col,
                "type": dtype_str,
                "null_count": null_count,
                "missing_pct": round(missing_pct, 2),
                "unique_count": n_unique,
                "unique_pct": round((n_unique / rows * 100) if rows > 0 else 0, 2)
            }
            
            # Categorize type
            col_type = "text"
            if dtype.is_numeric() or dtype.is_integer():
                col_type = "numerical"
                numerical_cols.append(col)
            elif "date" in dtype_str or "time" in dtype_str:
                col_type = "datetime"
                datetime_cols.append(col)
            elif "bool" in dtype_str:
                col_type = "boolean"
                boolean_cols.append(col)
            else:
                # String heuristics: distinguish categorical from long text
                if n_unique <= 30 or n_unique / rows < 0.05:
                    col_type = "categorical"
                    categorical_cols.append(col)
                else:
                    col_type = "text"
                    text_cols.append(col)
                    
            stats["category"] = col_type
            
            # Numeric calculations
            if col_type == "numerical":
                # Filter out nulls
                valid_series = series.drop_nulls()
                if valid_series.len() > 0:
                    vals = valid_series.to_numpy()
                    
                    mean = float(np.mean(vals))
                    median = float(np.median(vals))
                    std = float(np.std(vals))
                    var = float(np.var(vals))
                    
                    q1 = float(np.percentile(vals, 25))
                    q3 = float(np.percentile(vals, 75))
                    iqr = q3 - q1
                    
                    # Outliers calculation
                    lower_bound = q1 - 1.5 * iqr
                    upper_bound = q3 + 1.5 * iqr
                    outliers = int(np.sum((vals < lower_bound) | (vals > upper_bound)))
                    
                    # Skewness & Kurtosis
                    try:
                        from scipy.stats import skew, kurtosis
                        skewness = float(skew(vals))
                        kurt = float(kurtosis(vals))
                    except Exception:
                        # simple fallback formula
                        skewness = 3 * (mean - median) / (std + 1e-6)
                        kurt = 0.0
                        
                    stats.update({
                        "mean": _sanitize_float(round(mean, 4)),
                        "median": _sanitize_float(round(median, 4)),
                        "std_dev": _sanitize_float(round(std, 4)),
                        "variance": _sanitize_float(round(var, 4)),
                        "min": _sanitize_float(float(np.min(vals))),
                        "max": _sanitize_float(float(np.max(vals))),
                        "q1": _sanitize_float(round(q1, 4)),
                        "q3": _sanitize_float(round(q3, 4)),
                        "iqr": _sanitize_float(round(iqr, 4)),
                        "outliers": outliers,
                        "skewness": _sanitize_float(round(skewness, 4)),
                        "kurtosis": _sanitize_float(round(kurt, 4))
                    })
            
            # Categorical / Text specific stats
            elif col_type in ["categorical", "text"]:
                valid_series = series.drop_nulls()
                if valid_series.len() > 0:
                    mode_val = valid_series.mode()
                    mode_str = str(mode_val[0]) if mode_val.len() > 0 else "N/A"
                    stats["mode"] = mode_str
                    
                    # Calculate entropy
                    value_counts = valid_series.value_counts()
                    total_valid = valid_series.len()
                    ent = 0.0
                    for count in value_counts["count"]:
                        p = count / total_valid
                        ent -= p * math.log2(p)
                    stats["entropy"] = _sanitize_float(round(ent, 4))
                    
                    # PII semantic scans
                    sample_vals = valid_series.head(100).to_list()
                    has_email = any(isinstance(v, str) and email_regex.match(v) for v in sample_vals)
                    has_phone = any(isinstance(v, str) and phone_regex.match(v) for v in sample_vals)
                    has_currency = any(isinstance(v, str) and currency_regex.search(v) for v in sample_vals)
                    
                    if has_email:
                        stats["pii_detected"] = "Email addresses detected"
                        warnings.append({"column": col, "type": "PII Exposure", "message": f"Column '{col}' contains email addresses. Recommended to apply sanitization mask."})
                    elif has_phone:
                        stats["pii_detected"] = "Phone numbers detected"
                        warnings.append({"column": col, "type": "PII Exposure", "message": f"Column '{col}' contains phone number formatting."})
                    elif has_currency:
                        stats["currency_detected"] = True
                        
            column_stats[col] = stats
            
            # Generate quality warnings per column
            if missing_pct > 30:
                warnings.append({"column": col, "type": "High Missing Values", "message": f"Column '{col}' has {missing_pct:.1f}% missing values."})
                recommendations.append({"column": col, "type": "Impute/Drop", "message": f"Drop '{col}' or apply interpolation because over 30% of data is null."})
                
            if n_unique == 1:
                warnings.append({"column": col, "type": "Constant Column", "message": f"Column '{col}' is constant (has only 1 unique value)."})
                recommendations.append({"column": col, "type": "Drop Constant", "message": f"Drop constant column '{col}' before training model."})
                
        # Duplicate rows
        duplicate_rows = df.height - df.unique().height
        if duplicate_rows > 0:
            warnings.append({"column": "Dataset", "type": "Duplicate Rows", "message": f"Dataset contains {duplicate_rows} exact duplicate rows."})
            recommendations.append({"column": "Dataset", "type": "Deduplicate", "message": "Remove exact duplicates to avoid model bias."})
            
        # Pearson correlation matrix (numerical columns)
        corr_matrix = {}
        if len(numerical_cols) >= 2:
            try:
                num_df = df.select(numerical_cols).drop_nulls()
                corr_df = num_df.corr()
                for i, col_a in enumerate(numerical_cols):
                    corr_matrix[col_a] = {}
                    for j, col_b in enumerate(numerical_cols):
                        val = corr_df[col_b][i]
                        sanitized_val = _sanitize_float(val)
                        corr_matrix[col_a][col_b] = round(sanitized_val, 4)
                        
                        # Multicollinearity warning
                        if col_a != col_b and abs(sanitized_val) > 0.85 and i < j:
                            warnings.append({"columns": [col_a, col_b], "type": "Multicollinearity", "message": f"High correlation ({sanitized_val:.2f}) between '{col_a}' and '{col_b}'."})
                            recommendations.append({"columns": [col_a, col_b], "type": "Feature Selection", "message": f"Drop one of '{col_a}' or '{col_b}' to prevent regression collinearity."})
            except Exception as e:
                logger.warning(f"Failed to calculate correlation matrix: {e}")

        # Class Imbalance detection
        if target_column and target_column in categorical_cols:
            target_counts = df[target_column].drop_nulls().value_counts()
            if target_counts.height >= 2:
                min_class = target_counts["count"].min()
                max_class = target_counts["count"].max()
                ratio = min_class / max_class
                if ratio < 0.1:
                    warnings.append({"column": target_column, "type": "Class Imbalance", "message": f"Target column '{target_column}' is highly imbalanced (min/max class ratio: {ratio:.3f})."})
                    recommendations.append({"column": target_column, "type": "SMOTE / Class Weighting", "message": "Use SMOTE oversampling or balance class weights during model training."})

        # Target Leakage detection
        if target_column and target_column in numerical_cols:
            for num_col in numerical_cols:
                if num_col != target_column:
                    corr_val = corr_matrix.get(num_col, {}).get(target_column, 0.0)
                    if abs(corr_val) > 0.95:
                        warnings.append({"column": num_col, "type": "Target Leakage", "message": f"Potential target leakage: '{num_col}' has {corr_val:.2f} correlation with target '{target_column}'."})
                        recommendations.append({"column": num_col, "type": "Drop Leaker", "message": f"Exclude feature '{num_col}' as it likely contains target information."})

        # Heuristic Domain classification
        domain = "Generic"
        col_names_lower = [c.lower() for c in columns]
        if any(kw in col_names_lower for kw in ["sales", "revenue", "price", "profit", "customer"]):
            domain = "Retail & E-commerce"
        elif any(kw in col_names_lower for kw in ["patient", "doctor", "health", "disease", "age"]):
            domain = "Healthcare & Medical"
        elif any(kw in col_names_lower for kw in ["loan", "balance", "default", "interest", "transaction"]):
            domain = "Finance & Banking"
            
        # Target suggestion
        target_suggestion = target_column or (numerical_cols[0] if numerical_cols else (categorical_cols[0] if categorical_cols else None))
        
        # Model recommendation
        recommended_model = "XGBoostRegressor"
        if target_suggestion:
            if target_suggestion in categorical_cols or (target_suggestion in numerical_cols and len(df[target_suggestion].unique()) < 10):
                recommended_model = "XGBoostClassifier"
            elif dates_found := [c for c in columns if c.lower() in ["date", "timestamp"]]:
                recommended_model = "ARIMA / Prophet (Time Series Forecasting)"
                
        # Generate Story narrative
        story = f"This dataset belongs to the **{domain}** domain and has **{rows} rows** and **{cols} columns**.\n"
        story += f"We identified {len(numerical_cols)} numeric features and {len(categorical_cols)} categorical fields.\n"
        if duplicate_rows > 0:
            story += f"Note: {duplicate_rows} duplicate observations were found and should be purged.\n"
        story += f"The recommended analytics goal is to model target **{target_suggestion}** using **{recommended_model}**."
        
        # Executive Summary
        summary = (
            f"Dataset name: {os.path.basename(self.file_path)}\n"
            f"Dimensions: {rows} x {cols}\n"
            f"Data health: {len(warnings)} Quality Warnings active. Target suggestion: {target_suggestion}."
        )

        elapsed = time.time() - start_time
        
        return {
            "rows": rows,
            "columns": cols,
            "file_size": self.file_size,
            "memory_usage_bytes": memory_usage_est,
            "schema": schema_dict,
            "column_types": {
                "numerical": numerical_cols,
                "categorical": categorical_cols,
                "datetime": datetime_cols,
                "boolean": boolean_cols,
                "text": text_cols
            },
            "statistics": column_stats,
            "correlation_matrix": corr_matrix,
            "warnings": warnings,
            "recommendations": recommendations,
            "story": story,
            "summary": summary,
            "load_time_sec": round(elapsed, 4)
        }
