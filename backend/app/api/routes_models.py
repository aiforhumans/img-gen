from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from backend.app.models.registry import model_registry
from backend.app.core.vram_manager import vram_manager

router = APIRouter(prefix="/api/models", tags=["models"])

class LoadModelRequest(BaseModel):
    vram_strategy: Optional[str] = None
    precision: Optional[str] = "fp16"

@router.get("")
async def get_models():
    """Lists all registered models, their architecture, VRAM footprint, and loaded states."""
    models = model_registry.list_models()
    return {
        "models": models,
        "active_model_id": model_registry.active_model_id,
        "current_vram_strategy": vram_manager.current_strategy.value
    }

@router.post("/{model_id}/load")
async def load_model_endpoint(model_id: str, req: Optional[LoadModelRequest] = None):
    """Loads a specific model into VRAM/RAM with the requested memory strategy."""
    strat = req.vram_strategy if req else None
    prec = req.precision if req and req.precision else "fp16"
    try:
        adapter = model_registry.load_model(model_id, vram_strategy=strat, precision=prec)
        return {
            "success": True,
            "model_id": model_id,
            "is_loaded": adapter.is_loaded,
            "loaded_device": adapter.loaded_device,
            "vram_strategy": adapter.current_vram_strategy
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load model '{model_id}': {str(e)}")

@router.post("/{model_id}/unload")
async def unload_model_endpoint(model_id: str):
    """Unloads the specified model from VRAM and safely flushes the CUDA cache."""
    success = model_registry.unload_model(model_id)
    return {"success": success, "model_id": model_id}

@router.post("/{model_id}/download")
async def start_download_model(model_id: str):
    """Triggers asynchronous download of model checkpoints from Hugging Face."""
    from backend.app.models.downloader import model_downloader
    try:
        started = model_downloader.start_download(model_id)
        status = model_downloader.get_status(model_id)
        return {"started": started, "model_id": model_id, "status": status}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{model_id}/download-status")
async def get_download_status(model_id: str):
    """Queries live download progress and transferred megabytes."""
    from backend.app.models.downloader import model_downloader
    return model_downloader.get_status(model_id)

@router.get("/{model_id}/validate")
async def validate_model_weights(model_id: str):
    """Verifies that downloaded model weights and configurations are valid and intact."""
    from pathlib import Path
    from backend.app.core.config import settings
    target_dir = Path(settings.paths.model_dirs[0]) / model_id
    if not target_dir.exists():
        return {"valid": False, "exists": False, "message": "Model directory does not exist"}

    safetensors = list(target_dir.glob("**/*.safetensors"))
    configs = list(target_dir.glob("**/model_index.json")) + list(target_dir.glob("**/config.json"))

    return {
        "valid": len(safetensors) > 0 or len(configs) > 0,
        "exists": True,
        "safetensors_count": len(safetensors),
        "total_files": sum(1 for _ in target_dir.glob("**/*") if _.is_file()),
        "path": str(target_dir)
    }

@router.delete("/{model_id}")
async def delete_model_weights(model_id: str):
    """Deletes downloaded weights from disk to free drive space."""
    import shutil
    from pathlib import Path
    from backend.app.core.config import settings
    target_dir = Path(settings.paths.model_dirs[0]) / model_id
    if target_dir.exists():
        model_registry.unload_model(model_id)
        shutil.rmtree(target_dir, ignore_errors=True)
        return {"success": True, "deleted": model_id}
    raise HTTPException(status_code=404, detail="Model weights not found on disk.")

@router.get("/{model_id}/samplers")
async def get_compatible_samplers(model_id: str, steps: int = 8):
    """Returns the list of compatible samplers for a model at a given step count.

    For Z-Image Turbo (Lightning-distilled), the sampler list is step-aware:
    - 2-step: Only Euler (trailing) is safe
    - 4-step: Euler + DPM++ 2M Karras
    - 8-step: Full sampler menu
    """
    from backend.app.models.scheduler_factory import SchedulerFactory

    adapter = model_registry.get_adapter(model_id)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found in registry.")

    architecture = adapter.architecture
    samplers = SchedulerFactory.get_step_aware_samplers(architecture, steps)

    return {
        "model_id": model_id,
        "architecture": architecture,
        "steps": steps,
        "samplers": samplers,
        "default": "Euler" if architecture == "zimage" else "Default (Recommended)"
    }

