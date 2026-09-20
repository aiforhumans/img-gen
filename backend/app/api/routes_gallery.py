from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse

from backend.app.core.database import (
    list_generations, get_generation_by_id, toggle_favorite, delete_generation
)
from backend.app.gallery.metadata_manager import extract_metadata_from_png

router = APIRouter(prefix="/api/gallery", tags=["gallery"])

@router.get("")
async def get_gallery_items(
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    favorite_only: bool = False,
    model: Optional[str] = None,
    search: Optional[str] = None
):
    """Retrieves paginated images and generation parameters from the local gallery."""
    items, total = await list_generations(
        limit=limit,
        offset=offset,
        favorite_only=favorite_only,
        model_filter=model,
        search_query=search
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}

@router.get("/image/{generation_id}")
async def get_generation_image(generation_id: str):
    """Serves the full-resolution PNG image for a generation."""
    record = await get_generation_by_id(generation_id)
    if not record:
        raise HTTPException(status_code=404, detail="Image record not found.")

    path = Path(record["image_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="Image file missing on disk.")

    return FileResponse(path, media_type="image/png")

@router.get("/thumb/{generation_id}")
async def get_generation_thumbnail(generation_id: str):
    """Serves the optimized WebP thumbnail for fast gallery rendering."""
    record = await get_generation_by_id(generation_id)
    if not record:
        raise HTTPException(status_code=404, detail="Thumbnail record not found.")

    path = Path(record.get("thumbnail_path") or record["image_path"])
    if not path.exists():
        path = Path(record["image_path"])
        if not path.exists():
            raise HTTPException(status_code=404, detail="File missing on disk.")

    return FileResponse(path, media_type="image/webp" if path.suffix == ".webp" else "image/png")

@router.post("/{generation_id}/favorite")
async def toggle_favorite_endpoint(generation_id: str):
    """Toggles favorite bookmark status on a generation."""
    new_status = await toggle_favorite(generation_id)
    return {"id": generation_id, "is_favorite": new_status}

@router.delete("/{generation_id}")
async def delete_generation_endpoint(generation_id: str):
    """Permanently deletes a generation and its files from disk."""
    success = await delete_generation(generation_id)
    return {"id": generation_id, "success": success}

@router.post("/extract-metadata")
async def extract_metadata_endpoint(file: UploadFile = File(...)):
    """Extracts embedded prompt/seed metadata from an uploaded PNG file."""
    try:
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(await file.read())
            tmp_path = Path(tmp.name)

        meta = extract_metadata_from_png(tmp_path)
        tmp_path.unlink()
        return {"metadata": meta}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read PNG metadata: {str(e)}")
