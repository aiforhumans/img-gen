import json
from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.core.config import PROJECT_ROOT

router = APIRouter(prefix="/api/styles", tags=["styles"])
STYLES_DIR = PROJECT_ROOT / "config" / "styles"

class StyleModel(BaseModel):
    id: str
    name: str
    category: str = "Custom"
    prompt_template: str
    negative_prompt: str = ""
    recommended_aspect_ratio: str = "1:1"
    recommended_model: str = "auto"
    default: bool = False

@router.get("")
async def get_styles():
    """Retrieves all JSON style presets available in config/styles."""
    STYLES_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for file_p in sorted(STYLES_DIR.glob("*.json")):
        try:
            with open(file_p, "r", encoding="utf-8") as f:
                data = json.load(f)
                results.append(data)
        except Exception:
            pass
    return {"styles": results}

@router.post("")
async def save_style(style: StyleModel):
    """Creates or updates a custom style preset."""
    STYLES_DIR.mkdir(parents=True, exist_ok=True)
    file_p = STYLES_DIR / f"{style.id}.json"
    with open(file_p, "w", encoding="utf-8") as f:
        json.dump(style.model_dump(), f, indent=2)
    return {"success": True, "style": style.model_dump()}

@router.delete("/{style_id}")
async def delete_style(style_id: str):
    """Deletes a custom style preset."""
    file_p = STYLES_DIR / f"{style_id}.json"
    if file_p.exists():
        file_p.unlink()
        return {"success": True, "deleted": style_id}
    raise HTTPException(status_code=404, detail="Style preset not found.")
