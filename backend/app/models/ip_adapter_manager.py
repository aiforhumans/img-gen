"""
IP-Adapter Manager for Antigravity Diffusion Studio.

Manages IP-Adapter weight lifecycle, CLIP image encoding, and VRAM allocation
for style and subject reference image support on Z-Image Turbo (SDXL-based).

Architecture:
- Style Reference: Uses IP-Adapter base (CLIP-ViT-H global features) → aesthetic/mood transfer
- Subject Reference: Uses IP-Adapter Plus (local features) → face/object injection

VRAM Budget (RTX 5080 16GB):
- Base Z-Image pipeline: ~7.2 GB
- CLIP ViT-H encoder: ~1.7 GB
- IP-Adapter weights: ~0.1-0.15 GB each
- Total with adapter active: ~9.1 GB (leaves ~7GB headroom)
"""

import os
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any

from backend.app.core.config import PROJECT_ROOT, settings
from backend.app.core.logger import app_logger

# IP-Adapter weight file definitions
IP_ADAPTER_WEIGHTS: Dict[str, Dict[str, Any]] = {
    "style": {
        "repo_id": "h94/IP-Adapter",
        "subfolder": "sdxl_models",
        "filename": "ip-adapter_sdxl_vit-h.safetensors",
        "description": "IP-Adapter SDXL Style (CLIP-ViT-H global features, ~98MB)",
        "estimated_size_mb": 98,
    },
    "subject": {
        "repo_id": "h94/IP-Adapter",
        "subfolder": "sdxl_models",
        "filename": "ip-adapter-plus_sdxl_vit-h.safetensors",
        "description": "IP-Adapter Plus SDXL Subject (local features, ~98MB)",
        "estimated_size_mb": 98,
    },
}

CLIP_IMAGE_ENCODER = {
    "repo_id": "h94/IP-Adapter",
    "subfolder": "models/image_encoder",
    "description": "CLIP ViT-H/14 Image Encoder (~1.7GB)",
    "estimated_size_mb": 1700,
}


class IPAdapterManager:
    """
    Central IP-Adapter lifecycle manager for style and subject reference images.

    Handles:
    - Auto-downloading weights from HuggingFace on first use
    - Lazy loading/unloading of CLIP encoder and adapter weights
    - Reference image encoding through CLIP
    - Pipeline attachment/detachment for generation
    """

    def __init__(self):
        self._cache_dir = PROJECT_ROOT / "cache" / "ip-adapter"
        self._references_dir = PROJECT_ROOT / "cache" / "references"
        self._clip_encoder = None
        self._active_mode: Optional[str] = None
        self._is_downloading = False
        self._download_progress = 0.0
        self._download_lock = threading.Lock()

    @property
    def cache_dir(self) -> Path:
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        return self._cache_dir

    @property
    def references_dir(self) -> Path:
        self._references_dir.mkdir(parents=True, exist_ok=True)
        return self._references_dir

    def has_weights(self, mode: str) -> bool:
        """Check if IP-Adapter weights for the given mode exist locally."""
        weight_info = IP_ADAPTER_WEIGHTS.get(mode)
        if not weight_info:
            return False
        weight_path = self.cache_dir / weight_info["filename"]
        return weight_path.exists() and weight_path.stat().st_size > 1024 * 1024  # > 1MB

    def has_clip_encoder(self) -> bool:
        """Check if CLIP image encoder weights exist locally."""
        encoder_dir = self.cache_dir / "image_encoder"
        config_path = encoder_dir / "config.json"
        model_path = encoder_dir / "model.safetensors"
        # Check for either safetensors or pytorch model
        return config_path.exists() and (
            model_path.exists() or (encoder_dir / "pytorch_model.bin").exists()
        )

    def ensure_weights(self, mode: str) -> bool:
        """Ensures IP-Adapter weights are available. Downloads from HuggingFace if missing.

        Returns True if weights are ready, False if download failed.
        """
        if self.has_weights(mode) and self.has_clip_encoder():
            return True

        app_logger.info(f"[IPAdapterManager] Downloading IP-Adapter weights for mode '{mode}'...")
        return self._download_weights(mode)

    def _download_weights(self, mode: str) -> bool:
        """Downloads IP-Adapter weights and CLIP encoder from HuggingFace Hub."""
        with self._download_lock:
            if self._is_downloading:
                app_logger.warning("[IPAdapterManager] Download already in progress.")
                return False

            self._is_downloading = True
            self._download_progress = 0.0

        try:
            from huggingface_hub import hf_hub_download, snapshot_download
            from backend.app.models.downloader import get_hf_token

            token = get_hf_token()

            # Download adapter weights
            if not self.has_weights(mode):
                weight_info = IP_ADAPTER_WEIGHTS[mode]
                app_logger.info(f"[IPAdapterManager] Downloading {weight_info['description']}...")
                self._download_progress = 0.1

                hf_hub_download(
                    repo_id=weight_info["repo_id"],
                    subfolder=weight_info["subfolder"],
                    filename=weight_info["filename"],
                    local_dir=str(self.cache_dir),
                    token=token
                )
                self._download_progress = 0.5

            # Download CLIP image encoder
            if not self.has_clip_encoder():
                app_logger.info(f"[IPAdapterManager] Downloading {CLIP_IMAGE_ENCODER['description']}...")
                snapshot_download(
                    repo_id=CLIP_IMAGE_ENCODER["repo_id"],
                    allow_patterns=[
                        f"{CLIP_IMAGE_ENCODER['subfolder']}/*"
                    ],
                    local_dir=str(self.cache_dir),
                    token=token
                )
                self._download_progress = 0.9

            self._download_progress = 1.0
            app_logger.info(f"[IPAdapterManager] IP-Adapter weights for '{mode}' downloaded successfully!")
            return True

        except Exception as e:
            app_logger.error(f"[IPAdapterManager] Failed to download IP-Adapter weights: {e}", exc_info=True)
            return False
        finally:
            with self._download_lock:
                self._is_downloading = False

    def start_background_download(self, mode: str):
        """Starts a background thread to download IP-Adapter weights."""
        thread = threading.Thread(target=self._download_weights, args=(mode,), daemon=True)
        thread.start()

    def load_adapter(self, pipeline: Any, mode: str) -> bool:
        """Attaches IP-Adapter to an SDXL pipeline.

        Args:
            pipeline: A StableDiffusionXLPipeline instance
            mode: "style" or "subject"

        Returns True if adapter was loaded successfully.
        """
        if self._active_mode == mode:
            app_logger.debug(f"[IPAdapterManager] IP-Adapter '{mode}' already active, skipping reload.")
            return True

        if not self.ensure_weights(mode):
            app_logger.error(f"[IPAdapterManager] Cannot load adapter '{mode}': weights not available.")
            return False

        try:
            weight_info = IP_ADAPTER_WEIGHTS[mode]
            weight_name = weight_info["filename"]

            # Resolve the actual weight path (hf_hub_download puts it in subfolder)
            weight_path = self.cache_dir / weight_info["subfolder"] / weight_name
            if not weight_path.exists():
                weight_path = self.cache_dir / weight_name

            image_encoder_path = self.cache_dir / "models" / "image_encoder"
            if not image_encoder_path.exists():
                image_encoder_path = self.cache_dir / "image_encoder"

            app_logger.info(f"[IPAdapterManager] Loading IP-Adapter '{mode}' into pipeline...")

            # Unload existing adapter if switching modes
            if self._active_mode is not None:
                try:
                    pipeline.unload_ip_adapter()
                except Exception:
                    pass

            pipeline.load_ip_adapter(
                str(self.cache_dir),
                subfolder=weight_info["subfolder"],
                weight_name=weight_name,
                image_encoder_folder=str(image_encoder_path),
            )

            self._active_mode = mode
            app_logger.info(f"[IPAdapterManager] IP-Adapter '{mode}' loaded successfully!")
            return True

        except Exception as e:
            app_logger.error(f"[IPAdapterManager] Failed to load IP-Adapter '{mode}': {e}", exc_info=True)
            return False

    def unload_adapter(self, pipeline: Any) -> bool:
        """Detaches IP-Adapter from pipeline and frees VRAM."""
        if self._active_mode is None:
            return True

        try:
            pipeline.unload_ip_adapter()
            self._active_mode = None
            app_logger.info("[IPAdapterManager] IP-Adapter unloaded, VRAM reclaimed.")
            return True
        except Exception as e:
            app_logger.warning(f"[IPAdapterManager] Error unloading IP-Adapter: {e}")
            self._active_mode = None
            return False

    def encode_reference_image(self, image) -> Any:
        """Preprocesses and encodes a reference image for IP-Adapter.

        The image is resized and center-cropped to 224x224 for CLIP input.
        Returns the processed PIL Image ready for ip_adapter_image parameter.
        """
        from PIL import Image

        if not isinstance(image, Image.Image):
            image = Image.open(image).convert("RGB")
        else:
            image = image.convert("RGB")

        # CLIP expects 224x224 — resize while maintaining aspect ratio then center crop
        w, h = image.size
        scale = max(224 / w, 224 / h)
        new_w, new_h = int(w * scale), int(h * scale)
        image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # Center crop to 224x224
        left = (new_w - 224) // 2
        top = (new_h - 224) // 2
        image = image.crop((left, top, left + 224, top + 224))

        return image

    def get_status(self) -> Dict[str, Any]:
        """Returns current IP-Adapter system status."""
        return {
            "style_weights_available": self.has_weights("style"),
            "subject_weights_available": self.has_weights("subject"),
            "clip_encoder_loaded": self._clip_encoder is not None,
            "active_mode": self._active_mode,
            "downloading": self._is_downloading,
            "download_progress": self._download_progress,
        }

    def save_reference_image(self, image, filename: str) -> Path:
        """Saves a reference image to the cache directory with the given filename."""
        from PIL import Image

        if not isinstance(image, Image.Image):
            image = Image.open(image).convert("RGB")

        out_path = self.references_dir / filename
        image.save(out_path, format="PNG")
        return out_path


# Singleton instance
ip_adapter_manager = IPAdapterManager()
