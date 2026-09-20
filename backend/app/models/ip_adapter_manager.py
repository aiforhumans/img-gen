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
from typing import Optional, Dict, Any, List, Union

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

    def load_adapter(self, pipeline: Any, mode: Union[str, List[str]]) -> bool:
        """Attaches IP-Adapter to an SDXL pipeline. Supports single or multi-mode.

        Args:
            pipeline: A StableDiffusionXLPipeline instance
            mode: "style", "subject", or a list like ["style", "subject"]

        Returns True if at least one adapter was loaded successfully.
        """
        if isinstance(mode, str):
            modes = [mode]
        else:
            # Deduplicate preserving order
            modes = list(dict.fromkeys(mode))

        # Filter to modes whose weights are available
        available_modes = [m for m in modes if self.ensure_weights(m)]
        if not available_modes:
            app_logger.error(f"[IPAdapterManager] Cannot load any adapter from {modes}: weights not available.")
            return False

        # If already loaded with the same modes, skip reloading
        if self._active_mode == available_modes or (len(available_modes) == 1 and self._active_mode == available_modes[0]):
            app_logger.debug(f"[IPAdapterManager] IP-Adapter '{available_modes}' already active, skipping reload.")
            return True

        try:
            image_encoder_path = self.cache_dir / "models" / "image_encoder"
            if not image_encoder_path.exists():
                image_encoder_path = self.cache_dir / "image_encoder"

            # Unload existing adapter if loaded
            if self._active_mode is not None:
                try:
                    pipeline.unload_ip_adapter()
                except Exception:
                    pass
                self._active_mode = None

            if len(available_modes) == 1:
                single_mode = available_modes[0]
                weight_info = IP_ADAPTER_WEIGHTS[single_mode]
                weight_name = weight_info["filename"]
                subfolder = weight_info["subfolder"]

                app_logger.info(f"[IPAdapterManager] Loading single IP-Adapter '{single_mode}' into pipeline...")
                pipeline.load_ip_adapter(
                    str(self.cache_dir),
                    subfolder=subfolder,
                    weight_name=weight_name,
                    image_encoder_folder=str(image_encoder_path),
                )
                self._active_mode = single_mode
            else:
                pretrained_paths = [str(self.cache_dir)] * len(available_modes)
                subfolders = [IP_ADAPTER_WEIGHTS[m]["subfolder"] for m in available_modes]
                weight_names = [IP_ADAPTER_WEIGHTS[m]["filename"] for m in available_modes]

                app_logger.info(f"[IPAdapterManager] Loading dual IP-Adapters {available_modes} into pipeline...")
                pipeline.load_ip_adapter(
                    pretrained_paths,
                    subfolder=subfolders,
                    weight_name=weight_names,
                    image_encoder_folder=str(image_encoder_path),
                )
                self._active_mode = available_modes

            app_logger.info(f"[IPAdapterManager] IP-Adapter '{self._active_mode}' loaded successfully!")
            return True

        except Exception as e:
            app_logger.error(f"[IPAdapterManager] Failed to load IP-Adapter '{available_modes}': {e}", exc_info=True)
            return False

    @staticmethod
    def get_num_ip_adapters(pipeline: Any) -> int:
        """Returns the number of loaded IP-Adapters in the pipeline."""
        try:
            unet = getattr(pipeline, "unet", None)
            if unet and hasattr(unet, "attn_processors"):
                for proc in unet.attn_processors.values():
                    if hasattr(proc, "scale"):
                        return len(proc.scale)
            if unet and hasattr(unet, "encoder_hid_proj") and unet.encoder_hid_proj is not None:
                if hasattr(unet.encoder_hid_proj, "image_projection_layers"):
                    return len(unet.encoder_hid_proj.image_projection_layers)
        except Exception:
            pass
        return 1

    def unload_adapter(self, pipeline: Any) -> bool:
        """Detaches IP-Adapter from pipeline and frees VRAM."""
        try:
            if hasattr(pipeline, "unload_ip_adapter"):
                pipeline.unload_ip_adapter()
            if hasattr(pipeline, "unet") and hasattr(pipeline.unet, "config"):
                pipeline.unet.config.encoder_hid_dim_type = None
                pipeline.unet.encoder_hid_proj = None
            self._active_mode = None
            app_logger.info("[IPAdapterManager] IP-Adapter unloaded, VRAM reclaimed.")
            return True
        except Exception as e:
            app_logger.warning(f"[IPAdapterManager] Error unloading IP-Adapter: {e}")
            if hasattr(pipeline, "unet") and hasattr(pipeline.unet, "config"):
                pipeline.unet.config.encoder_hid_dim_type = None
                pipeline.unet.encoder_hid_proj = None
            self._active_mode = None
            return False

    def encode_reference_image(self, image, mode: str = "subject") -> Any:
        """Preprocesses and encodes a reference image for IP-Adapter.

        The image is resized and cropped to 224x224 for CLIP input.
        In 'subject' mode on portrait/vertical images, applies top-bias cropping
        to isolate the face and head, avoiding scene background and chest framing.
        """
        from PIL import Image

        if not isinstance(image, Image.Image):
            image = Image.open(image).convert("RGB")
        else:
            image = image.convert("RGB")

        w, h = image.size

        # In subject mode on portrait/vertical images, crop focused on the head/face
        if mode == "subject" and h > w:
            scale = max(224 / w, 224 / h)
            new_w, new_h = int(w * scale), int(h * scale)
            image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
            left = (new_w - 224) // 2
            # Focus on upper region where the face resides
            top = max(0, min(new_h - 224, int((new_h - 224) * 0.2)))
            image = image.crop((left, top, left + 224, top + 224))
        else:
            scale = max(224 / w, 224 / h)
            new_w, new_h = int(w * scale), int(h * scale)
            image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
            left = (new_w - 224) // 2
            top = (new_h - 224) // 2
            image = image.crop((left, top, left + 224, top + 224))

        return image

    def get_status(self) -> Dict[str, Any]:
        """Returns current IP-Adapter system status."""
        active_str = None
        if isinstance(self._active_mode, list):
            active_str = ", ".join(self._active_mode)
        elif self._active_mode:
            active_str = str(self._active_mode)

        return {
            "style_weights_available": self.has_weights("style"),
            "subject_weights_available": self.has_weights("subject"),
            "clip_encoder_loaded": self._clip_encoder is not None,
            "active_mode": active_str,
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
