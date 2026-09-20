import asyncio
import base64
import io
import secrets
import time
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional
from PIL import Image
from pydantic import BaseModel, Field

from backend.app.core.config import PROJECT_ROOT, settings
from backend.app.core.logger import app_logger, gen_logger, error_logger
from backend.app.core.exceptions import GenerationCancelled, ModelLoadError, OOMRetryExhausted
from backend.app.core.vram_manager import vram_manager, VRAMStrategy
from backend.app.core.database import insert_generation
from backend.app.gallery.metadata_manager import create_png_info
from backend.app.models.registry import model_registry
from backend.app.routing.auto_router import auto_router
from backend.app.prompt_engine.lm_studio_client import lm_studio_client
from backend.app.prompt_engine.style_composer import style_composer
from backend.app.lora.lora_scanner import lora_scanner

class JobState(str, Enum):
    WAITING = "waiting"
    PREPARING = "preparing"
    LOADING_MODEL = "loading_model"
    GENERATING = "generating"
    DECODING = "decoding"
    SAVING = "saving"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobMetrics(BaseModel):
    model_load_time: float = 0.0
    prompt_processing_time: float = 0.0
    generation_time: float = 0.0
    decode_time: float = 0.0
    save_time: float = 0.0
    total_time: float = 0.0
    peak_vram_mb: float = 0.0
    images_per_minute: float = 0.0
    oom_retries: int = 0
    effective_vram_strategy: str = "BALANCED"

class GenerationJob(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    prompt: str
    original_prompt: str = ""
    negative_prompt: str = ""
    enhanced_prompt: Optional[str] = ""
    final_prompt: Optional[str] = ""
    model: str = "auto"
    mode: str = "auto"
    style: str = "none"
    aspect_ratio: str = "1:1"
    quality: str = "balanced"
    width: int = 1024
    height: int = 1024
    steps: int = 20
    guidance: float = 7.0
    seed: int = -1
    sampler: str = "Default (Recommended)"
    scheduler: str = "Default"
    loras: List[Dict[str, Any]] = Field(default_factory=list)
    vram_strategy: str = "BALANCED"
    precision: str = "fp16"

    # Editing specifics
    edit_mode: Optional[str] = None
    init_image: Optional[str] = None
    mask_image: Optional[str] = None
    strength: float = 0.75
    expand_left: int = 0
    expand_right: int = 0
    expand_top: int = 0
    expand_bottom: int = 0

    state: JobState = JobState.WAITING
    progress: float = 0.0
    current_step: int = 0
    total_steps: int = 20
    preview_base64: Optional[str] = None
    output_image_path: Optional[str] = None
    output_image_url: Optional[str] = None
    metrics: JobMetrics = Field(default_factory=JobMetrics)
    error_message: Optional[str] = None
    routing_reason: Optional[str] = None
    vram_strategy_used: str = "BALANCED"

def is_cuda_oom(exc: BaseException) -> bool:
    err_msg = str(exc).lower()
    return "out of memory" in err_msg or "cuda oom" in err_msg or "cudaoutofmemory" in err_msg

class JobQueue:
    """
    Asynchronous job queue manager for background image generation.
    Handles prioritization, step callbacks, cancellations, and performance telemetry.
    """
    def __init__(self):
        self.jobs: Dict[str, GenerationJob] = {}
        self.queue: asyncio.Queue = asyncio.Queue()
        self.current_job_id: Optional[str] = None
        self._cancel_requested: Dict[str, bool] = {}
        self._worker_task: Optional[asyncio.Task] = None

    def start_worker(self):
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._process_queue())

    def submit_job(self, job: GenerationJob) -> str:
        self.jobs[job.id] = job
        self.queue.put_nowait(job.id)
        self.start_worker()
        app_logger.info(f"Job {job.id} submitted to queue.")
        return job.id

    def cancel_job(self, job_id: str) -> bool:
        if job_id in self.jobs:
            job = self.jobs[job_id]
            if job.state not in [JobState.COMPLETE, JobState.FAILED, JobState.CANCELLED]:
                self._cancel_requested[job_id] = True
                job.state = JobState.CANCELLED
                job.error_message = "Generation cancelled by user."
                app_logger.info(f"Job {job_id} marked as CANCELLED.")
                return True
        return False

    def get_job(self, job_id: str) -> Optional[GenerationJob]:
        return self.jobs.get(job_id)

    def list_jobs(self, limit: int = 20) -> List[GenerationJob]:
        return sorted(self.jobs.values(), key=lambda j: j.created_at, reverse=True)[:limit]

    def clear_completed(self):
        to_delete = [
            jid for jid, j in self.jobs.items()
            if j.state in [JobState.COMPLETE, JobState.FAILED, JobState.CANCELLED] and jid != self.current_job_id
        ]
        for jid in to_delete:
            del self.jobs[jid]

    async def _process_queue(self):
        while True:
            job_id = await self.queue.get()
            self.current_job_id = job_id
            job = self.jobs.get(job_id)

            if not job or self._cancel_requested.get(job_id, False):
                if job and job.state != JobState.CANCELLED:
                    job.state = JobState.CANCELLED
                    job.error_message = "Generation cancelled by user."
                self.queue.task_done()
                self.current_job_id = None
                continue

            t_start = time.time()
            vram_manager.reset_peak_vram()

            try:
                await self._execute_job(job)
            except GenerationCancelled:
                job.state = JobState.CANCELLED
                job.error_message = "Generation cancelled by user."
                app_logger.info(f"Job {job_id} execution cleanly cancelled.")
            except OOMRetryExhausted as e:
                error_msg = str(e)
                error_logger.error(f"Job {job_id} OOM exhausted: {error_msg}")
                job.state = JobState.FAILED
                job.error_message = error_msg
            except Exception as e:
                error_msg = str(e)
                error_logger.error(f"Job {job_id} failed: {error_msg}", exc_info=True)
                job.state = JobState.FAILED
                job.error_message = f"Generation failed: {error_msg}"
            finally:
                job.metrics.total_time = round(time.time() - t_start, 2)
                if job.metrics.total_time > 0 and job.state == JobState.COMPLETE:
                    job.metrics.images_per_minute = round(60.0 / job.metrics.total_time, 1)
                vram_manager.safe_empty_cache()

                self.queue.task_done()
                self.current_job_id = None

    async def _execute_job(self, job: GenerationJob):
        # Check cancellation
        if self._cancel_requested.get(job.id, False):
            raise GenerationCancelled()

        # 0. Resolve random seed centrally BEFORE inference (Phase 5)
        if job.seed < 0:
            job.seed = secrets.randbelow(2**32)
            app_logger.info(f"[JobQueue] Centrally resolved random seed for job {job.id}: {job.seed}")

        # 1. Routing, Style Composition & Prompt Intelligence (Phase 9)
        job.state = JobState.PREPARING
        t_prep_start = time.time()

        style_comp = style_composer.compose(
            prompt=job.prompt,
            style_id=job.style,
            user_negative_prompt=job.negative_prompt
        )
        job.original_prompt = style_comp.original_prompt
        job.negative_prompt = style_comp.negative_prompt
        styled_prompt = style_comp.style_prompt

        if job.aspect_ratio == "auto" and style_comp.recommended_aspect_ratio:
            job.aspect_ratio = style_comp.recommended_aspect_ratio

        if job.model == "auto":
            decision = auto_router.analyze(styled_prompt, user_mode=job.mode)
            target_model_id = decision.model
            job.routing_reason = decision.reason
            if job.aspect_ratio == "auto" or job.aspect_ratio == "1:1":
                job.width = decision.width
                job.height = decision.height
                job.aspect_ratio = decision.aspect_ratio
            if job.steps == 20:
                job.steps = decision.steps
            if job.guidance == 7.0:
                job.guidance = decision.guidance
        else:
            target_model_id = job.model
            job.routing_reason = f"Manual override to model '{job.model}'."

        # Prompt Intelligence / expansion
        if settings.lm_studio.enabled:
            job.enhanced_prompt = await lm_studio_client.enhance_prompt(styled_prompt)
        else:
            from backend.app.prompt_engine.local_analyzer import local_analyzer
            job.enhanced_prompt = local_analyzer.enhance(styled_prompt)

        job.final_prompt = job.enhanced_prompt if job.enhanced_prompt else styled_prompt
        job.metrics.prompt_processing_time = round(time.time() - t_prep_start, 2)

        if self._cancel_requested.get(job.id, False):
            raise GenerationCancelled()

        # Validate LoRA compatibility with target architecture (Phase 10)
        req_adapter = model_registry.get_adapter(target_model_id)
        if req_adapter:
            for lora in job.loras:
                lora_scanner.validate_compatibility(req_adapter.architecture, lora)

        # 2. Loading Model & VRAM enforcement with Automatic OOM Recovery (Phase 7 & 8)
        job.state = JobState.LOADING_MODEL
        t_load_start = time.time()

        max_retries = 3
        current_strategy = job.vram_strategy or vram_manager.current_strategy.value
        adapter = None
        final_image = None

        for attempt in range(max_retries + 1):
            if self._cancel_requested.get(job.id, False):
                raise GenerationCancelled()

            try:
                job.vram_strategy_used = current_strategy
                job.metrics.effective_vram_strategy = current_strategy
                adapter = model_registry.load_model(
                    target_model_id,
                    vram_strategy=current_strategy,
                    precision=job.precision
                )
                job.metrics.model_load_time = round(time.time() - t_load_start, 2)

                # Attach current job LoRAs after ensuring clean reset
                adapter.unload_all_loras()
                for lora in job.loras:
                    if adapter.supports_lora():
                        adapter.load_lora(lora.get("path"), lora.get("weight", 1.0))

                if self._cancel_requested.get(job.id, False):
                    raise GenerationCancelled()

                # 3. Generating (Text-to-Image or Editing)
                job.state = JobState.GENERATING
                job.total_steps = job.steps
                t_gen_start = time.time()

                def step_callback(step: int, total_steps: int, preview_img: Optional[Image.Image]):
                    if self._cancel_requested.get(job.id, False):
                        raise GenerationCancelled("Job cancelled by user.")
                    job.current_step = step
                    job.progress = round((step / max(1, total_steps)) * 100, 1)

                    if preview_img and settings.generation.live_preview:
                        buf = io.BytesIO()
                        preview_img.save(buf, format="JPEG", quality=70)
                        job.preview_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")

                prompt_to_use = job.final_prompt or job.prompt

                # Decode source images if editing mode requested
                source_image = None
                mask_image = None
                if job.init_image:
                    source_image = self._load_image_payload(job.init_image)
                if job.mask_image:
                    mask_image = self._load_image_payload(job.mask_image)

                loop = asyncio.get_running_loop()

                def run_inference():
                    if job.edit_mode == "inpaint" and source_image and mask_image:
                        return adapter.inpaint(
                            image=source_image,
                            mask=mask_image,
                            prompt=prompt_to_use,
                            negative_prompt=job.negative_prompt,
                            steps=job.steps,
                            guidance=job.guidance,
                            seed=job.seed,
                            sampler=job.sampler,
                            scheduler=job.scheduler,
                            callback=step_callback
                        )
                    elif job.edit_mode == "outpaint" and source_image:
                        return adapter.outpaint(
                            image=source_image,
                            expand_left=job.expand_left,
                            expand_right=job.expand_right,
                            expand_top=job.expand_top,
                            expand_bottom=job.expand_bottom,
                            prompt=prompt_to_use,
                            negative_prompt=job.negative_prompt,
                            steps=job.steps,
                            guidance=job.guidance,
                            seed=job.seed,
                            sampler=job.sampler,
                            scheduler=job.scheduler,
                            callback=step_callback
                        )
                    elif job.edit_mode == "img2img" and source_image:
                        return adapter.img2img(
                            image=source_image,
                            prompt=prompt_to_use,
                            negative_prompt=job.negative_prompt,
                            strength=job.strength,
                            steps=job.steps,
                            guidance=job.guidance,
                            seed=job.seed,
                            sampler=job.sampler,
                            scheduler=job.scheduler,
                            callback=step_callback
                        )
                    elif job.edit_mode == "instruct" and source_image:
                        return adapter.edit(
                            image=source_image,
                            instruction=prompt_to_use,
                            seed=job.seed,
                            callback=step_callback
                        )
                    else:
                        return adapter.generate(
                            prompt=prompt_to_use,
                            negative_prompt=job.negative_prompt,
                            width=job.width,
                            height=job.height,
                            steps=job.steps,
                            guidance=job.guidance,
                            seed=job.seed,
                            sampler=job.sampler,
                            scheduler=job.scheduler,
                            callback=step_callback
                        )

                final_image = await loop.run_in_executor(None, run_inference)
                job.metrics.generation_time = round(time.time() - t_gen_start, 2)
                break # Inference succeeded

            except BaseException as e:
                if isinstance(e, GenerationCancelled):
                    raise
                if is_cuda_oom(e):
                    app_logger.warning(f"[JobQueue] CUDA OOM on strategy {current_strategy} (attempt {attempt + 1}/{max_retries + 1})")
                    vram_manager.safe_empty_cache()
                    model_registry.unload_model(target_model_id)

                    next_strategy = vram_manager.step_down_strategy_from(current_strategy)
                    if next_strategy and attempt < max_retries:
                        job.metrics.oom_retries += 1
                        current_strategy = next_strategy.value
                        continue
                    else:
                        raise OOMRetryExhausted(
                            "CUDA Out of Memory on RTX 5080 across all VRAM strategies. "
                            "Please reduce image resolution, close other GPU applications, or select a smaller model."
                        ) from e
                raise

        # Check cancellation before saving
        if self._cancel_requested.get(job.id, False):
            raise GenerationCancelled()

        # 4. Measure Peak VRAM BEFORE metadata is written (Phase 11)
        job.metrics.peak_vram_mb = vram_manager.record_peak_vram()

        # Clean up LoRAs from adapter so state does not leak to subsequent jobs (Phase 10 & 12)
        if adapter:
            adapter.unload_all_loras()

        # 5. Saving & Metadata Embedding (Phase 2 & Phase 11)
        job.state = JobState.SAVING
        t_save_start = time.time()

        today_str = datetime.now().strftime("%Y-%m-%d")
        output_dir = PROJECT_ROOT / "outputs" / today_str
        output_dir.mkdir(parents=True, exist_ok=True)

        file_id = f"{int(time.time())}_{job.id[:8]}"
        img_path = output_dir / f"{file_id}.png"
        thumb_path = output_dir / f"{file_id}_thumb.webp"

        gpu_info = vram_manager.get_gpu_info()
        metadata_payload = {
            "id": job.id,
            "created_at": job.created_at,
            "prompt": job.prompt,
            "original_prompt": job.original_prompt,
            "enhanced_prompt": job.enhanced_prompt or "",
            "final_prompt": job.final_prompt or "",
            "negative_prompt": job.negative_prompt,
            "model": target_model_id,
            "model_version": adapter.name if adapter else target_model_id,
            "mode": job.mode,
            "style": job.style,
            "aspect_ratio": job.aspect_ratio,
            "quality": job.quality,
            "sampler": job.sampler,
            "scheduler": job.scheduler,
            "loras": job.loras,
            "seed": job.seed,
            "steps": job.steps,
            "guidance": job.guidance,
            "width": job.width,
            "height": job.height,
            "generation_time": job.metrics.generation_time,
            "peak_vram_mb": job.metrics.peak_vram_mb,
            "vram_strategy": job.vram_strategy_used,
            "oom_retries": job.metrics.oom_retries,
            "gpu_name": gpu_info.get("gpu_name", ""),
            "app_version": settings.general.version
        }

        # Embed PNG info
        png_info = create_png_info(metadata_payload)
        final_image.save(img_path, format="PNG", pnginfo=png_info)

        # Create thumbnail
        thumb = final_image.copy()
        thumb.thumbnail((384, 384), Image.Resampling.LANCZOS)
        thumb.save(thumb_path, format="WEBP", quality=80)

        # Persist to SQLite Database
        db_record = dict(metadata_payload)
        db_record["image_path"] = str(img_path)
        db_record["thumbnail_path"] = str(thumb_path)
        await insert_generation(db_record)

        job.metrics.save_time = round(time.time() - t_save_start, 2)
        job.metrics.total_time = round(time.time() - t_prep_start, 2)
        job.output_image_path = str(img_path)
        job.output_image_url = f"/api/gallery/image/{job.id}"
        job.progress = 100.0
        job.state = JobState.COMPLETE

        gen_logger.info(
            f"Job {job.id} completed in {job.metrics.total_time}s | Model: {target_model_id} | Seed: {job.seed} | Size: {job.width}x{job.height}"
        )

    def _load_image_payload(self, image_str: str) -> Optional[Image.Image]:
        try:
            if image_str.startswith("data:image"):
                base64_data = image_str.split(",", 1)[1]
                return Image.open(io.BytesIO(base64.b64decode(base64_data))).convert("RGB")
            p = Path(image_str)
            if p.exists():
                return Image.open(p).convert("RGB")
            # Try outputs relative path
            clean = image_str.lstrip("/")
            if clean.startswith("outputs/"):
                p_rel = PROJECT_ROOT / clean
                if p_rel.exists():
                    return Image.open(p_rel).convert("RGB")
        except Exception as e:
            app_logger.warning(f"Failed to load image payload: {e}")
        return None

job_queue = JobQueue()
