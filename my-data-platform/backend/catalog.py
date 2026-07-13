import uuid
import datetime
from datetime import datetime as dt, timezone
from database import SessionLocal
from models import CatalogItem
from activity_tracker import track_activity

def _make_json_serializable(data):
    if isinstance(data, dict):
        return {k: _make_json_serializable(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_make_json_serializable(item) for item in data]
    elif isinstance(data, (datetime.date, datetime.datetime)):
        return data.isoformat()
    return data

def register_catalog_entry(action: str, dataset_name: str | None, analysis: dict, rows: list, source: str, created_by: dict, **kwargs):
    username = created_by.get("username", "system")
    ml_results = kwargs.get("ml_results", {})

    with SessionLocal() as db:
        new_item = CatalogItem(
            id=str(uuid.uuid4()),
            name=dataset_name or f"Result_{action}_{dt.now().strftime('%Y%m%d%H%M')}",
            type=action,
            owner=username,
            visibility="private",
            summary=_make_json_serializable(analysis),
            preview_data=_make_json_serializable(rows[:50]) if rows else [],
            ml_results=_make_json_serializable(ml_results)
        )
        db.add(new_item)
        db.commit()
        item_id = new_item.id
        item_name = new_item.name

    track_activity(
        username=username,
        action=action,
        resource=dataset_name,
        metadata_info={"source": source, "rows_processed": len(rows) if rows else 0}
    )
    return {"id": item_id, "name": item_name}

def get_catalog_entry(entry_id: str) -> dict | None:
    with SessionLocal() as db:
        item = db.query(CatalogItem).filter(CatalogItem.id == entry_id).first()
        if not item:
            return None
        return {
            "id": item.id,
            "name": item.name,
            "type": item.type,
            "owner": item.owner,
            "visibility": item.visibility,
            "summary": item.summary,
            "preview_data": item.preview_data,
            "ml_results": item.ml_results,
            "created_at": item.created_at.isoformat() if item.created_at else None
        }

def list_catalog_entries_for_user(user: dict, limit: int = 20) -> list[dict]:
    username = user.get("username")
    role = user.get("role")
    
    with SessionLocal() as db:
        query = db.query(CatalogItem)
        if role != "admin":
            query = query.filter(CatalogItem.owner == username)
            
        items = query.order_by(CatalogItem.created_at.desc()).limit(limit).all()
        
        return [{
            "id": item.id,
            "name": item.name,
            "type": item.type,
            "owner": item.owner,
            "visibility": item.visibility,
            "summary": item.summary,
            "ml_results": item.ml_results,
            "created_at": item.created_at.isoformat() if item.created_at else None
        } for item in items]

def is_catalog_entry_visible(entry: dict, user: dict) -> bool:
    if user.get("role") == "admin":
        return True
    return entry.get("owner") == user.get("username")
