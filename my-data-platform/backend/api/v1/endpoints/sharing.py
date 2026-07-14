from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import StreamingResponse
import io
from schemas import CreateShareRequest
from auth import require_role
from share_manager import create_share_link, get_share, increment_view_count, record_download, list_my_shares, revoke_share
from catalog import register_catalog_entry
from report_generator import generate_structured_report_pdf, generate_structured_report_pptx

router = APIRouter()

@router.post("/api/share/create")
async def create_share(
    payload: CreateShareRequest,
    current_user: dict = Depends(require_role(["analyst", "admin"])),
):
    try:
        payload.validate_inputs()
        
        share = create_share_link(
            report_title=payload.report_title,
            report_data=payload.report_data,
            created_by=current_user,
            expires_days=payload.expires_days,
            access_level=payload.access_level,
        )
        register_catalog_entry(
            action="share",
            dataset_name=payload.report_title,
            analysis={"access_level": payload.access_level},
            rows=[],
            source="report_sharing",
            created_by=current_user,
        )
        return share
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to create share: {str(exc)}")


@router.get("/api/share/my-shares")
async def list_my_shares_endpoint(
    current_user: dict = Depends(require_role(["analyst", "admin"])),
):
    try:
        username = current_user.get("username")
        if not username:
            raise HTTPException(status_code=400, detail="User must be authenticated")
        
        shares = list_my_shares(username, limit=20)
        return {
            "shares": [
                {
                    "token": s.get("token"),
                    "report_title": s.get("report_title"),
                    "created_at": s.get("created_at"),
                    "expires_at": s.get("expires_at"),
                    "view_count": s.get("view_count"),
                    "downloads_count": len(s.get("downloads", [])),
                }
                for s in shares
            ]
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to list shares: {str(exc)}")


@router.get("/api/share/{token}")
async def view_share(token: str):
    try:
        if not token or not token.strip():
            raise HTTPException(status_code=400, detail="token cannot be empty")
        
        share = get_share(token)
        if not share:
            raise HTTPException(status_code=404, detail="Share not found or has expired.")
        
        increment_view_count(token)
        return {
            "report_title": share.get("report_title"),
            "report_data": share.get("report_data"),
            "created_at": share.get("created_at"),
            "access_level": share.get("access_level"),
            "view_count": share.get("view_count"),
        }
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve share: {str(exc)}")


@router.post("/api/share/{token}/download")
async def download_share(token: str, format: str = "pdf"):
    try:
        if not token or not token.strip():
            raise HTTPException(status_code=400, detail="token cannot be empty")
        if not format or not format.strip():
            format = "pdf"
        
        format = format.lower()
        if format not in ["pdf", "pptx"]:
            raise HTTPException(status_code=400, detail="format must be 'pdf' or 'pptx'")
        
        share = get_share(token)
        if not share:
            raise HTTPException(status_code=404, detail="Share not found or has expired.")
        
        if share.get("access_level") not in ["download", "edit"]:
            raise HTTPException(status_code=403, detail="Download not allowed for this share.")
        
        record_download(token, format)
        report_data = share.get("report_data") or {}
        
        if format == "pptx":
            file_bytes = generate_structured_report_pptx(
                title=report_data.get("title", "Report"),
                subtitle=report_data.get("subtitle", ""),
                sections=report_data.get("sections", []),
            )
            media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            filename = "shared_report.pptx"
        else:
            file_bytes = generate_structured_report_pdf(
                title=report_data.get("title", "Report"),
                subtitle=report_data.get("subtitle", ""),
                sections=report_data.get("sections", []),
            )
            media_type = "application/pdf"
            filename = "shared_report.pdf"
        
        buffer = io.BytesIO(file_bytes)
        return StreamingResponse(
            buffer,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(exc)}")


@router.delete("/api/share/{token}")
async def revoke_share_endpoint(
    token: str,
    current_user: dict = Depends(require_role(["analyst", "admin"])),
):
    try:
        if not token or not token.strip():
            raise HTTPException(status_code=400, detail="token cannot be empty")
        
        username = current_user.get("username")
        success = revoke_share(token, username)
        if not success:
            raise HTTPException(status_code=403, detail="Not authorized to revoke this share.")
        return {"status": "revoked"}
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to revoke share: {str(exc)}")
