import os
import uuid
import hashlib
import time
import logging
from typing import Any, Dict, List, Tuple
import polars as pl
import duckdb

logger = logging.getLogger(__name__)

class DatasetEngine:
    """Enterprise-grade Dataset Ingestion and Profiling Engine using Polars and DuckDB."""

    def __init__(self, file_path: str, dataset_id: str = None):
        self.file_path = file_path
        self.dataset_id = dataset_id or str(uuid.uuid4())
        self.file_extension = os.path.splitext(file_path)[1].lower()
        self.file_size = os.path.getsize(file_path)
        
    def calculate_md5(self) -> str:
        """Calculates MD5 hash of the file in chunks to prevent memory blowup."""
        hash_md5 = hashlib.md5()
        with open(self.file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def detect_encoding_and_delimiter(self) -> Tuple[str, str]:
        """Detects CSV delimiter and file encoding using simple heuristics."""
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

        # Test delimiter on first line
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

    def load_metadata(self) -> Dict[str, Any]:
        """Loads dataset schema and high-level metadata instantly using lazy evaluation."""
        start_time = time.time()
        encoding, delimiter = self.detect_encoding_and_delimiter()
        polars_encoding = "utf8" if encoding == "utf-8" else encoding
        
        row_count = 0
        columns = []
        schema_dict = {}
        memory_usage_est = 0
        
        try:
            # Lazy load based on file extension
            if self.file_extension == ".csv":
                lf = pl.scan_csv(self.file_path, encoding=polars_encoding, separator=delimiter, ignore_errors=True)
                row_count = lf.select(pl.len()).collect().item()
                schema_dict = lf.schema
                columns = list(schema_dict.keys())
                memory_usage_est = self.file_size * 1.5 # Heuristic for raw memory footprint
                
            elif self.file_extension == ".parquet":
                lf = pl.scan_parquet(self.file_path)
                row_count = lf.select(pl.len()).collect().item()
                schema_dict = lf.schema
                columns = list(schema_dict.keys())
                memory_usage_est = self.file_size * 3.0 # Compressed Parquet expands significantly in memory
                
            elif self.file_extension in [".xls", ".xlsx"]:
                # Excel cannot be lazily scanned easily, read headers and estimate
                df = pl.read_excel(self.file_path, read_options={"n_rows": 100})
                columns = df.columns
                schema_dict = {col: str(dtype) for col, dtype in zip(df.columns, df.dtypes)}
                
                # Excel row count check using DuckDB (very fast for large sheets)
                conn = duckdb.connect()
                try:
                    conn.execute("install spatial; load spatial;") # required for excel integration in duckdb
                    row_count = conn.execute(f"SELECT COUNT(*) FROM st_read('{self.file_path}')").fetchone()[0]
                except Exception:
                    # fallback to pandas load row count
                    import pandas as pd
                    xl = pd.ExcelFile(self.file_path)
                    sheet = xl.sheet_names[0]
                    df_full = xl.parse(sheet, usecols=[0])
                    row_count = len(df_full)
                memory_usage_est = self.file_size * 5.0
                
            elif self.file_extension == ".json":
                # JSON lazy scan fallback
                try:
                    lf = pl.scan_ndjson(self.file_path)
                    row_count = lf.select(pl.len()).collect().item()
                    schema_dict = lf.schema
                    columns = list(schema_dict.keys())
                except Exception:
                    df = pl.read_json(self.file_path)
                    row_count = df.height
                    columns = df.columns
                    schema_dict = {col: str(dtype) for col, dtype in zip(df.columns, df.dtypes)}
                memory_usage_est = self.file_size * 2.5
                
            elif self.file_extension == ".sqlite":
                # Query sqlite metadata via DuckDB
                conn = duckdb.connect()
                tables = conn.execute(f"SELECT name FROM sqlite_scan('{self.file_path}', 'sqlite_master') WHERE type='table'").fetchall()
                if tables:
                    main_table = tables[0][0]
                    row_count = conn.execute(f"SELECT COUNT(*) FROM sqlite_scan('{self.file_path}', '{main_table}')").fetchone()[0]
                    schema_df = conn.execute(f"PRAGMA table_info('{main_table}')").pl()
                    columns = schema_df["name"].to_list()
                    # map schema types
                    schema_dict = {row["name"]: row["type"] for row in schema_df.iter_rows(named=True)}
                memory_usage_est = self.file_size
                
            else:
                raise ValueError(f"Unsupported file format: {self.file_extension}")
                
        except Exception as e:
            logger.exception(f"Error reading metadata from {self.file_path}: {e}")
            raise RuntimeError(f"Metadata ingestion failed: {e}") from e

        # Categorize columns
        categorical_cols = []
        numerical_cols = []
        datetime_cols = []
        boolean_cols = []
        text_cols = []
        
        for col, dtype in schema_dict.items():
            dtype_str = str(dtype).lower()
            if "float" in dtype_str or "int" in dtype_str or "decimal" in dtype_str or "double" in dtype_str:
                numerical_cols.append(col)
            elif "date" in dtype_str or "time" in dtype_str:
                datetime_cols.append(col)
            elif "bool" in dtype_str:
                boolean_cols.append(col)
            elif "cat" in dtype_str or "enum" in dtype_str:
                categorical_cols.append(col)
            else:
                # Treat others as string/text columns
                # We will further distinguish text vs categorical when profiling values
                text_cols.append(col)

        # Profile sample data for missing percentage and candidate keys
        missing_pct = {}
        pk_candidates = []
        duplicate_keys_count = {}
        
        try:
            # Read first 10,000 rows for quick heuristics
            sample_df = self.read_chunk(limit=10000)
            total_sample_rows = sample_df.height
            
            if total_sample_rows > 0:
                for col in columns:
                    nulls = sample_df[col].null_count()
                    missing_pct[col] = (nulls / total_sample_rows) * 100
                    
                    # Candidate PK check: must have 0 nulls and 100% unique values in sample
                    n_uniq = sample_df[col].n_unique()
                    if nulls == 0 and n_uniq == total_sample_rows:
                        pk_candidates.append(col)
                        
                    # Count duplicates for candidate columns
                    if n_uniq < total_sample_rows:
                        duplicate_keys_count[col] = total_sample_rows - n_uniq
                        
        except Exception as e:
            logger.warning(f"Failed to profile column heuristics on sample: {e}")

        elapsed_time = time.time() - start_time
        # Est processing time: 0.1s + 4s per 10M cells
        cell_count = row_count * len(columns)
        est_proc_time = 0.1 + (cell_count / 1000000) * 0.4
        
        return {
            "dataset_id": self.dataset_id,
            "filename": os.path.basename(self.file_path),
            "file_size": self.file_size,
            "row_count": row_count,
            "column_count": len(columns),
            "columns": columns,
            "schema": {c: str(t) for c, t in schema_dict.items()},
            "encoding": encoding,
            "delimiter": delimiter,
            "md5_hash": self.calculate_md5(),
            "memory_usage_bytes": int(memory_usage_est),
            "estimated_processing_time_sec": round(est_proc_time, 2),
            "column_types": {
                "numerical": numerical_cols,
                "categorical": categorical_cols,
                "datetime": datetime_cols,
                "boolean": boolean_cols,
                "text": text_cols
            },
            "missing_percentages": missing_pct,
            "primary_key_candidates": pk_candidates,
            "duplicate_keys_count": duplicate_keys_count,
            "load_time_sec": round(elapsed_time, 4)
        }

    def read_chunk(self, offset: int = 0, limit: int = 10000) -> pl.DataFrame:
        """Reads a chunk of the dataset safely using Polars to support lazy-loading of 100M+ rows."""
        encoding, delimiter = self.detect_encoding_and_delimiter()
        polars_encoding = "utf8" if encoding == "utf-8" else encoding
        
        if self.file_extension == ".csv":
            # Using CSV slice read
            return pl.read_csv(
                self.file_path,
                separator=delimiter,
                encoding=polars_encoding,
                skip_rows=offset,
                n_rows=limit,
                ignore_errors=True
            )
        elif self.file_extension == ".parquet":
            # Using lazy select with slice
            lf = pl.scan_parquet(self.file_path)
            return lf.slice(offset, limit).collect()
        elif self.file_extension in [".xls", ".xlsx"]:
            import pandas as pd
            xl = pd.ExcelFile(self.file_path)
            df = xl.parse(xl.sheet_names[0], skiprows=offset, nrows=limit)
            return pl.from_pandas(df)
        elif self.file_extension == ".json":
            try:
                lf = pl.scan_ndjson(self.file_path)
                return lf.slice(offset, limit).collect()
            except Exception:
                df = pl.read_json(self.file_path)
                return df.slice(offset, limit)
        elif self.file_extension == ".sqlite":
            conn = duckdb.connect()
            tables = conn.execute(f"SELECT name FROM sqlite_scan('{self.file_path}', 'sqlite_master') WHERE type='table'").fetchall()
            if not tables:
                return pl.DataFrame()
            main_table = tables[0][0]
            # Fetch slice using SQL
            df = conn.execute(f"SELECT * FROM sqlite_scan('{self.file_path}', '{main_table}') LIMIT {limit} OFFSET {offset}").pl()
            return df
        else:
            raise ValueError(f"Cannot read chunk for file type: {self.file_extension}")
