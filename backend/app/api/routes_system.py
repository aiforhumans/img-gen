import os
import platform
import sys
from fastapi import APIRouter
from pydantic import BaseModel

from backend.app.core.config import settings, PROJECT_ROOT
from backend.app.core.vram_manager import vram_manager, VRAMStrategy
from backend.app.models.registry import model_registry

router = APIRouter(prefix="/api/system", tags=["system"])

class UpdateStrategyRequest(BaseModel):
    strategy: VRAMStrategy

@router.get("")
async def get_system_status():
    """Returns real-time GPU telemetry, VRAM allocation, CUDA/PyTorch stats, and loaded models."""
    gpu_info = vram_manager.get_gpu_info()
    return {
        "gpu": gpu_info,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "active_model": model_registry.active_model_id,
        "vram_strategy": vram_manager.current_strategy.value,
        "settings": settings.model_dump()
    }

@router.post("/vram-strategy")
async def update_vram_strategy(req: UpdateStrategyRequest):
    """Updates the central VRAM management strategy."""
    vram_manager.current_strategy = req.strategy
    return {"success": True, "vram_strategy": vram_manager.current_strategy.value}

@router.post("/clear-cache")
async def clear_gpu_cache():
    """Manually forces a garbage collection and CUDA cache flush."""
    vram_manager.safe_empty_cache()
    return {"success": True, "gpu": vram_manager.get_gpu_info()}

@router.get("/diagnostics")
async def get_diagnostics():
    """
    Generates a full diagnostic report for troubleshooting.
    Does NOT include private prompts or image contents.
    """
    gpu_info = vram_manager.get_gpu_info()

    # Read recent errors from logs/errors.log if it exists
    recent_errors = []
    err_log = PROJECT_ROOT / "logs" / "errors.log"
    if err_log.exists():
        try:
            with open(err_log, "r", encoding="utf-8") as f:
                lines = f.readlines()
                recent_errors = [line.strip() for line in lines[-20:]]
        except Exception:
            pass

    return {
        "application": {
            "name": settings.general.app_name,
            "version": settings.general.version,
            "project_root": str(PROJECT_ROOT)
        },
        "environment": {
            "os": platform.platform(),
            "python": sys.version,
            "torch": gpu_info.get("torch_version"),
            "cuda_available": gpu_info.get("has_cuda"),
            "cuda_version": gpu_info.get("cuda_version"),
            "driver_version": gpu_info.get("driver_version")
        },
        "hardware": {
            "gpu_name": gpu_info.get("gpu_name"),
            "vram_total_mb": gpu_info.get("vram_total_mb"),
            "vram_allocated_mb": gpu_info.get("vram_allocated_mb"),
            "vram_reserved_mb": gpu_info.get("vram_reserved_mb"),
            "vram_free_mb": gpu_info.get("vram_free_mb")
        },
        "models": {
            "registered_adapters": list(model_registry.adapters.keys()),
            "active_model": model_registry.active_model_id,
            "configured_model_dirs": settings.paths.model_dirs
        },
        "recent_errors": recent_errors
    }
