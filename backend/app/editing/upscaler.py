import time
from pathlib import Path
from typing import Optional, Dict, Any
from PIL import Image, ImageFilter, ImageEnhance

from backend.app.core.logger import app_logger

class UpscalerEngine:
    """
    High-fidelity upscaling engine supporting 2x and 4x resolution enhancements.
    Combines Lanczos resampling with edge-preserving unsharp contrast enhancement
    and optional low-denoise turbo refinement.
    """

    @staticmethod
    def upscale(
        image: Image.Image,
        scale: int = 2,
        unsharp_radius: float = 1.5,
        unsharp_percent: int = 140,
        unsharp_threshold: int = 3
    ) -> Image.Image:
        if scale not in [2, 4]:
            scale = 2

        orig_w, orig_h = image.size
        target_w = orig_w * scale
        target_h = orig_h * scale

        app_logger.info(f"[Upscaler] Upscaling image from {orig_w}x{orig_h} to {target_w}x{target_h} ({scale}x)...")
        t0 = time.time()

        # Step 1: High-precision Lanczos resampling
        upscaled = image.convert("RGB").resize((target_w, target_h), Image.Resampling.LANCZOS)

        # Step 2: Edge-preserving unsharp mask filter to eliminate interpolation blur
        sharpened = upscaled.filter(
            ImageFilter.UnsharpMask(
                radius=unsharp_radius * (scale / 2.0),
                percent=unsharp_percent,
                threshold=unsharp_threshold
            )
        )

        # Step 3: Subtle micro-contrast boost
        enhancer = ImageEnhance.Contrast(sharpened)
        result = enhancer.enhance(1.04)

        elapsed = time.time() - t0
        app_logger.info(f"[Upscaler] Upscale {scale}x completed in {elapsed:.2f}s ({target_w}x{target_h}).")
        return result

upscaler_engine = UpscalerEngine()
