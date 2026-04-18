import polars as pl
from connectors import read_dataset_from_bytes


def read_csv_from_bytes(contents: bytes) -> pl.DataFrame:
    return read_dataset_from_bytes(contents, filename="data.csv")

def infer_category(dataframe: pl.DataFrame) -> str:
    lower_columns = {column.lower() for column in dataframe.columns}

    if {"price", "amount", "sales"}.intersection(lower_columns):
        return "Retail"
    if {"age", "gender", "income"}.intersection(lower_columns):
        return "Customer"
    return "Generic"


def analyze_dataframe(dataframe: pl.DataFrame) -> dict:
    return {
        "category": infer_category(dataframe),
        "rows": dataframe.height,
        "cols": dataframe.width,
        "column_info": dataframe.columns,
        "null_counts": dataframe.null_count().to_dicts(),
        "audit_errors": generate_audit_report(dataframe),
    }


def generate_audit_report(dataframe: pl.DataFrame) -> list[dict]:
    report: list[dict] = []

    indexed = dataframe.with_row_index("row")

    for column in dataframe.columns:
        null_rows = indexed.filter(pl.col(column).is_null())["row"].to_list()
        for row_index in null_rows[:10]:
            report.append(
                {
                    "row": int(row_index),
                    "col": column,
                    "issue": f"Missing value in {column}",
                    "severity": "High",
                }
            )

    duplicate_rows = indexed.filter(dataframe.is_duplicated())["row"].to_list()
    first_column = dataframe.columns[0] if dataframe.columns else ""

    for row_index in duplicate_rows[:5]:
        report.append(
            {
                "row": int(row_index),
                "col": first_column,
                "issue": "Duplicate Row",
                "severity": "Medium",
            }
        )

    return report


def clean_dataframe(dataframe: pl.DataFrame) -> pl.DataFrame:
    cleaned = dataframe.unique(keep="first")
    cleaned = cleaned.fill_null(strategy="forward")

    date_columns = [column for column in cleaned.columns if "date" in column.lower()]
    if date_columns:
        cleaned = cleaned.with_columns(
            [pl.col(column).cast(pl.Utf8).str.to_date(strict=False) for column in date_columns]
        )

    return cleaned


def generate_cleaning_stats(before_dataframe: pl.DataFrame, after_dataframe: pl.DataFrame) -> list[dict]:
    before_null_map = before_dataframe.null_count().to_dicts()[0] if before_dataframe.columns else {}
    after_null_map = after_dataframe.null_count().to_dicts()[0] if after_dataframe.columns else {}

    columns = list(dict.fromkeys([*before_dataframe.columns, *after_dataframe.columns]))
    stats: list[dict] = []

    for column_name in columns:
        stats.append(
            {
                "columnName": column_name,
                "missingBefore": int(before_null_map.get(column_name, 0)),
                "missingAfter": int(after_null_map.get(column_name, 0)),
            }
        )

    return stats