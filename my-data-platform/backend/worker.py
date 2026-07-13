import os
from celery import Celery
from storage import get_file_bytes_from_s3
from connectors import read_dataset_from_bytes
from advanced_cleaner import advanced_data_cleaning
from ml_engine import run_automl_stateless
from utils import analyze_dataframe, generate_cleaning_stats
from catalog import register_catalog_entry

REDIS_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

celery_app = Celery("datasaas_worker", broker=REDIS_URL, backend=RESULT_BACKEND)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
)

import base64
from feature_engineer import auto_feature_engineer

@celery_app.task(bind=True)
def async_clean_data(self, file_b64: str, filename: str, user_dict: dict):
    self.update_state(state='PROGRESS', meta={'status': 'Decoding file data...'})

    try:
        file_bytes = base64.b64decode(file_b64)
        dataframe = read_dataset_from_bytes(file_bytes, filename)

        self.update_state(state='PROGRESS', meta={'status': 'Cleaning data...'})
        cleaned_dataframe = advanced_data_cleaning(dataframe)

        self.update_state(state='PROGRESS', meta={'status': 'Running Auto-Feature Engineering...'})
        cleaned_dataframe, engineering_notes = auto_feature_engineer(cleaned_dataframe)

        self.update_state(state='PROGRESS', meta={'status': 'Analyzing cleaned data...'})
        analysis = analyze_dataframe(cleaned_dataframe)
        cleaning_stats = generate_cleaning_stats(dataframe, cleaned_dataframe)
        if engineering_notes:
            if not cleaning_stats:
                cleaning_stats = {}
            cleaning_stats["engineering_notes"] = engineering_notes

        register_catalog_entry(
            action="clean_background",
            dataset_name=f"Cleaned_{filename}",
            analysis=analysis,
            cleaning_stats=cleaning_stats,
            rows=cleaned_dataframe.head(50).to_dicts(),
            source="background_worker",
            created_by=user_dict,
        )

        return {
            "status": "success",
            "message": f"Data cleaned, features engineered, and saved to catalog as Cleaned_{filename}.",
            "rows_processed": dataframe.height
        }
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@celery_app.task(bind=True)
def async_run_automl(self, file_b64: str, filename: str, target_column: str, user_dict: dict):
    self.update_state(state='PROGRESS', meta={'status': 'Decoding file data...'})

    try:
        file_bytes = base64.b64decode(file_b64)
        dataframe = read_dataset_from_bytes(file_bytes, filename)

        self.update_state(state='PROGRESS', meta={'status': f'Running AutoML on {target_column}...'})
        ml_result = run_automl_stateless(dataframe, target_column)

        register_catalog_entry(
            action="automl_background",
            dataset_name=f"AutoML_{filename}",
            analysis={"target": target_column, "accuracy": ml_result.get("accuracy")},
            ml_results=ml_result,
            rows=dataframe.head(50).to_dicts(),
            source="background_worker",
            created_by=user_dict,
        )

        return {"status": "success", "message": "AutoML completed and model saved to catalog."}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}
