import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from backend.app.models.base_adapter import BaseImageModelAdapter
from backend.app.models.flux.flux_adapter import FluxAdapter
from backend.app.models.zimage.zimage_adapter import ZImageAdapter
from backend.app.models.qwen.qwen_adapter import QwenAdapter
from backend.app.models.sdxl.sdxl_adapter import SDXLAdapter
from backend.app.core.vram_manager import vram_manager
from backend.app.core.logger import app_logger

class ModelRegistry:
    """
    Central registry and lifecycle manager for all image generation models.
    Supports on-demand loading, VRAM enforcement, and architecture discovery.
    """
    def __init__(self):
        self.adapters: Dict[str, BaseImageModelAdapter] = {
            "flux-klein-4b": FluxAdapter(model_id="flux-klein-4b", variant="4B"),
            "flux-klein-9b": FluxAdapter(model_id="flux-klein-9b", variant="9B"),
            "zimage-turbo": ZImageAdapter(model_id="zimage-turbo"),
            "qwen-image": QwenAdapter(model_id="qwen-image"),
            "sdxl": SDXLAdapter(model_id="sdxl")
        }
        self.active_model_id: Optional[str] = None

    def get_adapter(self, model_id: str) -> Optional[BaseImageModelAdapter]:
        return self.adapters.get(model_id)

    def load_model(self, model_id: str, vram_strategy: Optional[str] = None, precision: str = "fp16") -> BaseImageModelAdapter:
        adapter = self.get_adapter(model_id)
        if not adapter:
            raise ValueError(f"Model ID '{model_id}' is not registered.")

        if adapter.is_loaded and self.active_model_id == model_id:
            return adapter

        strategy = vram_strategy or vram_manager.current_strategy.value

        # Unload any previously loaded model in VRAM manager
        vram_manager.register_loaded_model(model_id, adapter)

        success = adapter.load(device="cuda" if vram_manager.has_cuda() else "cpu", vram_strategy=strategy, precision=precision)
        if success:
            self.active_model_id = model_id
            app_logger.info(f"Model '{model_id}' is now active in memory ({strategy}).")
        return adapter

    def unload_model(self, model_id: str) -> bool:
        adapter = self.get_adapter(model_id)
        if adapter and adapter.is_loaded:
            adapter.unload()
            if self.active_model_id == model_id:
                self.active_model_id = None
            vram_manager.safe_empty_cache()
            return True
        return False

    def list_models(self) -> List[Dict[str, Any]]:
        result = []
        for mid, adapter in self.adapters.items():
            rec = adapter.recommended_settings()
            resolutions = adapter.supported_resolutions()
            vram_req = adapter.estimate_vram(1024, 1024)

            capabilities = ["text_to_image", "image_to_image", "inpainting", "outpainting"]
            if mid == "qwen-image":
                capabilities.append("text_rendering")
                capabilities.append("instruction_editing")
            elif mid == "zimage-turbo":
                capabilities.append("photorealism_turbo")
            if adapter.supports_lora():
                capabilities.append("lora")

            result.append({
                "id": adapter.model_id,
                "name": adapter.name,
                "architecture": adapter.architecture,
                "is_loaded": adapter.is_loaded,
                "has_weights": adapter.has_weights(),
                "loaded_device": adapter.loaded_device,
                "estimated_vram_gb": vram_req,
                "precision": "bf16" if "flux" in mid else "fp16",
                "quantization": "int8/nf4 compatible" if mid == "flux-klein-9b" else "none",
                "capabilities": capabilities,
                "recommended_settings": rec,
                "supported_resolutions": resolutions
            })
        return result

model_registry = ModelRegistry()
