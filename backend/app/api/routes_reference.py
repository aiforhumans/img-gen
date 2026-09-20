import base64
import io
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from PIL import Image

from backend.app.models.ip_adapter_manager import ip_adapter_manager
from backend.app.core.logger import app_logger

router = APIRouter(prefix="/api", tags=["reference"])


@router.post("/reference/upload")
async def upload_reference_image(file: UploadFile = File(...)):
    """Uploads a reference image for IP-Adapter style/subject guidance.

    Stores the image in cache/references/ with a UUID filename.
    Returns the path and a base64 thumbnail for the UI preview.
    """
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        w, h = image.size
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image file: {e}")

    # Generate unique filename
    file_id = str(uuid.uuid4())[:12]
    filename = f"{file_id}.png"

    # Save to cache/references/
    saved_path = ip_adapter_manager.save_reference_image(image, filename)

    # Generate thumbnail for UI preview
    thumb = image.copy()
    thumb.thumbnail((256, 256), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    thumb.save(buf, format="JPEG", quality=85)
    thumb_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    return {
        "path": str(saved_path),
        "thumbnail_base64": thumb_b64,
        "width": w,
        "height": h
    }


@router.get("/ip-adapter/status")
async def get_ip_adapter_status():
    """Returns current IP-Adapter system status including weight availability and active mode."""
    return ip_adapter_manager.get_status()


class DownloadRequest(BaseModel):
    mode: str  # "style" or "subject"


@router.post("/ip-adapter/download")
async def download_ip_adapter_weights(req: DownloadRequest):
    """Starts background download of IP-Adapter weights for the specified mode."""
    if req.mode not in ("style", "subject"):
        raise HTTPException(status_code=400, detail="Mode must be 'style' or 'subject'")

    if ip_adapter_manager.has_weights(req.mode) and ip_adapter_manager.has_clip_encoder():
        return {"started": False, "message": "Weights already available", "ready": True}

    ip_adapter_manager.start_background_download(req.mode)
    return {"started": True, "message": f"Downloading IP-Adapter weights for '{req.mode}' mode..."}
