from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import pandas as pd
import polars as pl


SUPPORTED_EXTENSIONS = {".csv", ".tsv", ".json", ".ndjson", ".parquet", ".xlsx", ".xls"}


def infer_extension(filename: str | None) -> str:
    if not filename:
        return ".csv"
    return Path(filename).suffix.lower() or ".csv"


def _read_csv_variants(contents: bytes) -> pl.DataFrame:
    attempts: list[str] = []

    try:
        return pl.read_csv(io.BytesIO(contents), try_parse_dates=True)
    except Exception as exc:
        attempts.append(f"utf8: {exc}")

    if contents.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            decoded = contents.decode("utf-16")
            return pl.read_csv(io.StringIO(decoded), try_parse_dates=True)
        except Exception as exc:
            attempts.append(f"utf16: {exc}")

    for encoding in ("cp1252", "latin-1"):
        try:
            decoded = contents.decode(encoding)
            return pl.read_csv(io.StringIO(decoded), try_parse_dates=True)
        except Exception as exc:
            attempts.append(f"{encoding}: {exc}")

    try:
        return pl.read_csv(io.BytesIO(contents), encoding="utf8-lossy", try_parse_dates=True)
    except Exception as exc:
        attempts.append(f"utf8-lossy: {exc}")

    raise ValueError("CSV decoding failed. Tried utf8, utf16, cp1252, latin-1, utf8-lossy.")


def _read_json_dataset(contents: bytes) -> pl.DataFrame:
    if contents.startswith(b"\xef\xbb\xbf"):
        contents = contents[3:]

    try:
        text = contents.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = contents.decode("utf-8", errors="ignore")
    text = text.strip()
    if not text:
        raise ValueError("JSON file is empty")

    try:
        parsed: Any = json.loads(text)
    except json.JSONDecodeError:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        parsed = [json.loads(line) for line in lines]

    if isinstance(parsed, dict):
        if "data" in parsed and isinstance(parsed["data"], list):
            parsed = parsed["data"]
        else:
            parsed = [parsed]

    if not isinstance(parsed, list):
        raise ValueError("JSON must decode to a list or object")

    return pl.from_dicts(parsed)


def _read_excel_dataset(contents: bytes) -> pl.DataFrame:
    try:
        dataframe = pd.read_excel(io.BytesIO(contents), engine="openpyxl")
    except Exception:
        dataframe = pd.read_excel(io.BytesIO(contents))
    return pl.from_pandas(dataframe)


def _read_parquet_dataset(contents: bytes) -> pl.DataFrame:
    return pl.read_parquet(io.BytesIO(contents))


def read_dataset_from_bytes(contents: bytes, filename: str | None = None) -> pl.DataFrame:
    extension = infer_extension(filename)

    if extension in {".csv", ".tsv"}:
        dataframe = _read_csv_variants(contents)
        if extension == ".tsv":
            try:
                return pl.read_csv(io.BytesIO(contents), separator="\t", try_parse_dates=True)
            except Exception:
                pass
        return dataframe

    if extension in {".json", ".ndjson"}:
        return _read_json_dataset(contents)

    if extension in {".xlsx", ".xls"}:
        return _read_excel_dataset(contents)

    if extension == ".parquet":
        return _read_parquet_dataset(contents)

    raise ValueError(
        f"Unsupported file type '{extension}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
    )


def read_csv_from_bytes(contents: bytes) -> pl.DataFrame:
    return read_dataset_from_bytes(contents, filename="data.csv")
