import sys
import logging
import warnings
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Silence repetitive uvicorn polling access logs (200 OK / 304 Not Modified)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

from backend.app.core.config import settings, PROJECT_ROOT
from backend.app.core.logger import app_logger
from backend.app.core.database import init_db
from backend.app.core.job_queue import job_queue
from backend.app.core.vram_manager import vram_manager

from backend.app.api.routes_generate import router as generate_router
from backend.app.api.routes_models import router as models_router
from backend.app.api.routes_gallery import router as gallery_router
from backend.app.api.routes_system import router as system_router
from backend.app.api.routes_styles import router as styles_router
from backend.app.api.routes_lora import router as lora_router
from backend.app.api.routes_reference import router as reference_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app_logger.info("==================================================")
    app_logger.info(f"Starting {settings.general.app_name} v{settings.general.version}")
    app_logger.info("Initializing Local Database...")
    await init_db()

    gpu_info = vram_manager.get_gpu_info()
    app_logger.info(f"Hardware: {gpu_info['gpu_name']} | Total VRAM: {gpu_info['vram_total_mb']} MB")
    app_logger.info(f"VRAM Strategy: {vram_manager.current_strategy.value}")
    app_logger.info(f"LM Studio: {settings.lm_studio.base_url} (Enabled: {settings.lm_studio.enabled})")

    # Start async generation worker
    job_queue.start_worker()
    app_logger.info("Generation Queue Worker active.")
    app_logger.info("==================================================")

    yield

    # Shutdown
    app_logger.info("Shutting down... Reclaiming VRAM.")
    vram_manager.unload_all()

app = FastAPI(
    title=settings.general.app_name,
    version=settings.general.version,
    description="Modern local image generation platform optimized for RTX 5080 (16GB VRAM)",
    lifespan=lifespan
)

# Strict local CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:7860",
        "http://127.0.0.1:7860"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(generate_router)
app.include_router(models_router)
app.include_router(gallery_router)
app.include_router(system_router)
app.include_router(styles_router)
app.include_router(lora_router)
app.include_router(reference_router)

# Mount outputs static folder
outputs_dir = PROJECT_ROOT / "outputs"
outputs_dir.mkdir(parents=True, exist_ok=True)
app.mount("/outputs", StaticFiles(directory=str(outputs_dir)), name="outputs")

# Mount frontend if built
frontend_dist = PROJECT_ROOT / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
else:
    @app.get("/")
    async def root():
        return {
            "status": "online",
            "app": settings.general.app_name,
            "version": settings.general.version,
            "api_docs": "/docs",
            "message": "Frontend dev server runs at http://127.0.0.1:5173 or build with npm run build."
        }
