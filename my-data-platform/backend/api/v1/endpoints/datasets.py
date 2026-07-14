from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from auth import require_role
from connectors import read_dataset_from_bytes
from utils import analyze_dataframe
from identifier import identify_dataset_semantics
from catalog import register_catalog_entry
from api.ws.monitor import broadcast_event

router = APIRouter()

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_role(["analyst", "admin"])),
):
    contents = await file.read()

    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        dataframe = read_dataset_from_bytes(contents, file.filename)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to parse dataset: {exc}") from exc

    analysis = analyze_dataframe(dataframe)
    semantics = identify_dataset_semantics(dataframe)
    analysis["domain_info"] = semantics

    catalog_entry = register_catalog_entry(
        action="upload",
        dataset_name=file.filename,
        analysis=analysis,
        rows=dataframe.head(50).to_dicts(),
        source="file_upload",
        created_by=current_user,
    )

    await broadcast_event({
        "type": "catalog:activity",
        "payload": {
            "action": "upload",
            "dataset_name": file.filename,
            "rows": analysis.get("rows"),
            "cols": analysis.get("cols"),
            "catalog_id": catalog_entry.get("id") if isinstance(catalog_entry, dict) else None,
        },
    })

    return {
        "analysis": analysis,
        "grid_data": dataframe.to_dicts(),
        "sample_data": dataframe.head(10).to_dicts(),
        "catalog_preview": {
            "dataset_name": file.filename,
            "summary": {
                "rows": analysis.get("rows"),
                "cols": analysis.get("cols"),
                "domain": semantics.get("domain"),
            },
        },
    }
