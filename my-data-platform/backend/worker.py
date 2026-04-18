import base64
import os

from celery import Celery

from ml_engine import run_automl_stateless
from utils import analyze_dataframe, generate_cleaning_stats, read_csv_from_bytes
from advanced_cleaner import advanced_data_cleaning


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("data_tasks", broker=REDIS_URL, backend=REDIS_URL)


@celery_app.task(bind=True)
def async_clean_data(self, file_base64_string: str) -> dict:
    self.update_state(state="PROGRESS", meta={"status": "Loading CSV into memory...", "progress": 20})

    file_bytes = base64.b64decode(file_base64_string)
    dataframe = read_csv_from_bytes(file_bytes)

    self.update_state(
        state="PROGRESS",
        meta={"status": "Applying smart cleaning (types, outliers, imputation)...", "progress": 70},
    )
    cleaned = advanced_data_cleaning(dataframe)
    analysis = analyze_dataframe(cleaned)
    cleaning_stats = generate_cleaning_stats(dataframe, cleaned)

    return {
        "status": "Data cleaning successful",
        "analysis": analysis,
        "cleaning_stats": cleaning_stats,
        "grid_data": cleaned.to_dicts(),
        "sample_data": cleaned.head(100).to_dicts(),
    }


@celery_app.task(bind=True)
def async_run_automl(self, file_base64_string: str, target_column: str) -> dict:
    self.update_state(state="PROGRESS", meta={"status": "Loading dataset for AutoML...", "progress": 20})

    if not target_column:
        raise ValueError("Target column is required")

    file_bytes = base64.b64decode(file_base64_string)
    dataframe = read_csv_from_bytes(file_bytes)

    self.update_state(state="PROGRESS", meta={"status": "Running model selection...", "progress": 75})
    result = run_automl_stateless(dataframe, target_column)

    return {
        "status": "AutoML completed",
        "automl": result,
    }
