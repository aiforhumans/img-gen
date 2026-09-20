from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.core.generation_config import GenerationConfig
from backend.app.core.job_queue import job_queue, GenerationJob, JobState
from backend.app.routing.auto_router import auto_router, RoutingDecision
from backend.app.prompt_engine.lm_studio_client import lm_studio_client

router = APIRouter(prefix="/api", tags=["generation"])

class AnalyzePromptRequest(BaseModel):
    prompt: str
    mode: str = "auto"

class PolishPromptRequest(BaseModel):
    prompt: str
    style: Optional[str] = None

@router.post("/analyze-prompt", response_model=RoutingDecision)
async def analyze_prompt(req: AnalyzePromptRequest):
    """Returns the routing decision and analysis for a given prompt without executing generation."""
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")
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
async def generate_image(req: GenerationConfig):
    """Submits a text-to-image or editing job to the async generation queue."""
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")

    job = GenerationJob(
        prompt=req.prompt,
        original_prompt=req.original_prompt or req.prompt,
        negative_prompt=req.negative_prompt,
        model=req.model,
        mode=req.mode,
        style=req.style,
        aspect_ratio=req.aspect_ratio,
        quality=req.quality,
        width=req.width,
        height=req.height,
        steps=req.steps,
        guidance=req.guidance,
        seed=req.seed,
        sampler=req.sampler,
        scheduler=req.scheduler,
        loras=[l.model_dump() for l in req.loras],
        vram_strategy=req.vram_strategy,
        precision=req.precision,
        edit_mode=req.edit_mode,
        init_image=req.init_image,
        mask_image=req.mask_image,
        strength=req.strength,
        expand_left=req.expand_left,
        expand_right=req.expand_right,
        expand_top=req.expand_top,
        expand_bottom=req.expand_bottom
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
    job = job_queue.get_job(job_id)
    state = job.state.value if job else "unknown"
    return {"success": success, "job_id": job_id, "state": state}

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
    from datetime import datetime
    from pathlib import Path
    import time
    from PIL import Image
    from backend.app.core.config import PROJECT_ROOT
    from urllib.parse import urlparse
    from backend.app.core.database import insert_generation, get_generation_by_id
    from backend.app.core.job_queue import job_queue
    from backend.app.gallery.metadata_manager import create_png_info, extract_metadata_from_png
    from backend.app.editing.upscaler import upscaler_engine

    target_path = None

    # 1. Direct image_path provided
    if req.image_path:
        p = Path(req.image_path)
        if p.exists() and p.is_file():
            target_path = p
        elif (PROJECT_ROOT / req.image_path).exists():
            target_path = PROJECT_ROOT / req.image_path

    # 2. Extract from image_url
    if not target_path and req.image_url:
        parsed = urlparse(req.image_url)
        path_str = parsed.path if parsed.path else req.image_url.split("?")[0].strip()

        # Check if URL refers to gallery API: /api/gallery/image/{generation_id}
        if "/api/gallery/image/" in path_str:
            gen_id = path_str.split("/api/gallery/image/")[-1].strip().strip("/")
            record = await get_generation_by_id(gen_id)
            if record and record.get("image_path"):
                rec_p = Path(record["image_path"])
                if rec_p.exists() and rec_p.is_file():
                    target_path = rec_p
            if not target_path:
                job = job_queue.get_job(gen_id)
                if job and job.output_image_path and Path(job.output_image_path).exists():
                    target_path = Path(job.output_image_path)

        # Check /outputs/ path
        elif "/outputs/" in path_str or path_str.startswith("outputs/"):
            rel_part = path_str.split("outputs/")[-1].lstrip("/\\")
            cand = PROJECT_ROOT / "outputs" / rel_part
            if cand.exists() and cand.is_file():
                target_path = cand

        # Check if path_str is an ID directly
        if not target_path:
            clean_id = path_str.strip("/\\")
            record = await get_generation_by_id(clean_id)
            if record and record.get("image_path") and Path(record["image_path"]).exists():
                target_path = Path(record["image_path"])

        # Fallback: scan outputs directory for matching filename
        if not target_path:
            clean_name = Path(path_str).name
            if clean_name:
                for cand in (PROJECT_ROOT / "outputs").glob(f"**/{clean_name}"):
                    if cand.is_file():
                        target_path = cand
                        break

    if not target_path or not target_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Source image file not found for url='{req.image_url}' or path='{req.image_path}'."
        )

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
