from datetime import datetime, timezone
from database import SessionLocal
from models import MLModelRecord

def register_model(dataset_fingerprint: str, target_column: str, algorithm: str, accuracy, metrics: list | dict | None, created_by: dict, **kwargs):
    username = created_by.get("username", "system")
    with SessionLocal() as db:
        model_record = MLModelRecord(
            dataset_fingerprint=dataset_fingerprint,
            target_column=target_column,
            algorithm=algorithm,
            accuracy=str(accuracy) if accuracy is not None else None,
            metrics=metrics or {},
            created_by=username
        )
        db.add(model_record)
        db.commit()

def find_model_for_dataset(dataset_fingerprint: str, target_column: str) -> dict | None:
    with SessionLocal() as db:
        model_record = db.query(MLModelRecord).filter(
            MLModelRecord.dataset_fingerprint == dataset_fingerprint,
            MLModelRecord.target_column == target_column
        ).order_by(MLModelRecord.created_at.desc()).first()

        if not model_record:
            return None
        
        return {
            "algorithm": model_record.algorithm,
            "accuracy": float(model_record.accuracy) if model_record.accuracy and model_record.accuracy != "None" else None,
            "metrics": model_record.metrics,
            "created_at": model_record.created_at.isoformat() if model_record.created_at else None
        }
