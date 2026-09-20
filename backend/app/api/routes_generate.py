from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.core.job_queue import job_queue, GenerationJob, JobState
from backend.app.routing.auto_router import auto_router, RoutingDecision
from backend.app.prompt_engine.lm_studio_client import lm_studio_client

router = APIRouter(prefix="/api", tags=["generation"])

class GenerateRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    model: str = "auto"
    mode: str = "auto"
    aspect_ratio: str = "1:1"
    quality: str = "balanced"
    width: int = 1024
    height: int = 1024
    steps: int = 20
    guidance: float = 7.0
    seed: int = -1
    loras: List[Dict[str, Any]] = Field(default_factory=list)

class AnalyzePromptRequest(BaseModel):
    prompt: str
    mode: str = "auto"

class PolishPromptRequest(BaseModel):
    prompt: str
    style: Optional[str] = None

@router.post("/analyze-prompt", response_model=RoutingDecision)
async def analyze_prompt(req: AnalyzePromptRequest):
    """Returns the routing decision and analysis for a given prompt without executing generation."""
    return auto_router.analyze(req.prompt, user_mode=req.mode)

@router.post("/prompt/polish")
async def polish_prompt(req: PolishPromptRequest):
    """
    One-Click Magic Polish: Expands and refines user prompts with visual lighting,
    camera optics, and aesthetic details via LM Studio (falling back to local engine).
    """
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")

    is_lm_online = await lm_studio_client.is_available()
    polished = await lm_studio_client.enhance_prompt(req.prompt, style_name=req.style)
    
    diff_chars = len(polished) - len(req.prompt)
    summary = f"+{diff_chars} characters added" if diff_chars >= 0 else f"{diff_chars} characters trimmed"

    return {
        "original": req.prompt,
        "polished": polished,
        "provider": "lm_studio" if is_lm_online else "local_engine",
        "diff_summary": summary
    }

@router.post("/generate")
async def generate_image(req: GenerateRequest):
    """Submits a text-to-image job to the async generation queue."""
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")

    job = GenerationJob(
        prompt=req.prompt,
        negative_prompt=req.negative_prompt,
        model=req.model,
        mode=req.mode,
        aspect_ratio=req.aspect_ratio,
        quality=req.quality,
        width=req.width,
        height=req.height,
        steps=req.steps,
        guidance=req.guidance,
        seed=req.seed,
        loras=req.loras
    )
    job_id = job_queue.submit_job(job)
    return {"job_id": job_id, "state": job.state.value}

@router.get("/jobs")
async def list_jobs():
    """Lists current and recent generation jobs with state and progress."""
    return [job.model_dump() for job in job_queue.list_jobs()]

@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Retrieves status, progress, preview, and telemetry for a specific job."""
    job = job_queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job.model_dump()

@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancels a pending or generating job."""
    success = job_queue.cancel_job(job_id)
    return {"success": success, "job_id": job_id}

@router.post("/jobs/clear")
async def clear_completed_jobs():
    """Cleans up completed, cancelled, or failed jobs from memory."""
    job_queue.clear_completed()
    return {"success": True}

class UpscaleRequest(BaseModel):
    image_url: Optional[str] = None
    image_path: Optional[str] = None
    scale: int = 2 # 2 or 4

@router.post("/upscale")
async def upscale_image_endpoint(req: UpscaleRequest):
    """
    High-fidelity 2x and 4x image upscaling with Lanczos interpolation,
    unsharp detail sharpening, and gallery registration.
    """
    import io
    from pathlib import Path
    from datetime import datetime
    import time
    from PIL import Image
    from backend.app.core.config import PROJECT_ROOT, settings
    from backend.app.core.database import insert_generation
    from backend.app.gallery.metadata_manager import create_png_info, extract_metadata_from_png
    from backend.app.editing.upscaler import upscaler_engine

    target_path = None
    if req.image_path:
        target_path = Path(req.image_path)
    elif req.image_url:
        clean_url = req.image_url.split("?")[0]
        if clean_url.startswith("/outputs/"):
            target_path = PROJECT_ROOT / clean_url.lstrip("/")
        elif clean_url.startswith("http"):
            parts = clean_url.split("/outputs/")
            if len(parts) > 1:
                target_path = PROJECT_ROOT / "outputs" / parts[1]

    if not target_path or not target_path.exists():
        raise HTTPException(status_code=404, detail="Source image file not found.")

    try:
        source_img = Image.open(target_path)
        existing_meta = extract_metadata_from_png(target_path) or {}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to open source image: {e}")

    scale = 4 if req.scale == 4 else 2
    upscaled_img = upscaler_engine.upscale(source_img, scale=scale)
    new_w, new_h = upscaled_img.size

    # Save to outputs directory
    today_str = datetime.now().strftime("%Y-%m-%d")
    output_dir = PROJECT_ROOT / "outputs" / today_str
    output_dir.mkdir(parents=True, exist_ok=True)

    file_id = f"{int(time.time())}_upscale_{scale}x"
    out_img_path = output_dir / f"{file_id}.png"
    out_thumb_path = output_dir / f"{file_id}_thumb.webp"

    meta_payload = dict(existing_meta)
    meta_payload["id"] = file_id
    meta_payload["created_at"] = datetime.now().isoformat()
    meta_payload["width"] = new_w
    meta_payload["height"] = new_h
    meta_payload["prompt"] = existing_meta.get("prompt", "") + f" [Upscaled {scale}x]"
    meta_payload["upscaled"] = f"{scale}x"

    png_info = create_png_info(meta_payload)
    upscaled_img.save(out_img_path, format="PNG", pnginfo=png_info)

    thumb = upscaled_img.copy()
    thumb.thumbnail((384, 384), Image.Resampling.LANCZOS)
    thumb.save(out_thumb_path, format="WEBP", quality=80)

    # Insert into gallery database
    db_record = dict(meta_payload)
    db_record["image_path"] = str(out_img_path)
    db_record["thumbnail_path"] = str(out_thumb_path)
    db_record["file_size_bytes"] = out_img_path.stat().st_size
    await insert_generation(db_record)

    output_url = f"/outputs/{today_str}/{out_img_path.name}"
    return {
        "success": True,
        "output_url": output_url,
        "output_path": str(out_img_path),
        "width": new_w,
        "height": new_h,
        "scale": scale
    }
