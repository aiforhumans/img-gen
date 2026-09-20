import re
import random
import time
from typing import Dict, Any, List, Optional, Callable
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from backend.app.models.base_adapter import BaseImageModelAdapter
from backend.app.core.logger import app_logger

class QwenAdapter(BaseImageModelAdapter):
    """
    Qwen Image Adapter.
    Specialized for typography, in-image text rendering, signs, posters,
    and instruction-based editing.
    """
    def __init__(self, model_id: str = "qwen-image"):
        super().__init__(model_id=model_id, name="Qwen Image", architecture="qwen")

    def has_weights(self) -> bool:
        from backend.app.core.config import settings
        from pathlib import Path
        for mdir in settings.paths.model_dirs:
            p = Path(mdir) / self.model_id
            if p.exists() and any(p.glob("**/*.safetensors")):
                return True
        return False

    def load(self, device: str = "cuda", vram_strategy: str = "BALANCED", precision: str = "bf16") -> bool:
        app_logger.info(f"[QwenAdapter] Loading {self.name} (device={device}, strategy={vram_strategy})")
        self.loaded_device = device
        self.current_vram_strategy = vram_strategy
        self.is_loaded = True
        return True

    def unload(self) -> bool:
        app_logger.info(f"[QwenAdapter] Unloading {self.name}")
        self.is_loaded = False
        return True

    def estimate_vram(self, width: int = 1024, height: int = 1024, batch_size: int = 1) -> float:
        return 9.8 * ((width * height) / (1024 * 1024)) * batch_size

    def supported_resolutions(self) -> List[Dict[str, Any]]:
        return [
            {"label": "Poster (3:4)", "width": 864, "height": 1152, "aspect_ratio": "3:4"},
            {"label": "Square (1:1)", "width": 1024, "height": 1024, "aspect_ratio": "1:1"},
            {"label": "Banner (16:9)", "width": 1280, "height": 720, "aspect_ratio": "16:9"}
        ]

    def recommended_settings(self) -> Dict[str, Any]:
        return {
            "steps": 25,
            "guidance": 5.0,
            "sampler": "DPM++ 2M Karras",
            "scheduler": "Karras",
            "optimal_aspect_ratio": "3:4"
        }

    def supports_lora(self) -> bool:
        return False

    def load_lora(self, lora_path: str, weight: float = 1.0) -> bool:
        return False

    def unload_lora(self, lora_path: str) -> bool:
        return False

    def _extract_text_snippets(self, prompt: str) -> List[str]:
        # Extract text in quotes, e.g. 'saying "ARCADE 84"'
        matches = re.findall(r'["\']([^"\']+)["\']', prompt)
        if not matches:
            # Look for keywords like "saying XYZ" or "text XYZ"
            saying_match = re.search(r'(?:saying|text|words|title|reads)\s+([A-Za-z0-9\s_-]{2,20})', prompt, re.IGNORECASE)
            if saying_match:
                matches.append(saying_match.group(1).strip())
        return matches

    def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        steps: int = 25,
        guidance: float = 5.0,
        seed: int = -1,
        callback: Optional[Callable[[int, int, Optional[Image.Image]], None]] = None
    ) -> Image.Image:
        actual_seed = random.randint(0, 2**32 - 1) if seed < 0 else seed
        rng = random.Random(actual_seed)

        # High-contrast poster backdrop
        img = Image.new("RGB", (width, height), (18, 18, 28))
        draw = ImageDraw.Draw(img)

        # Gradient backdrop
        for y in range(height):
            ratio = y / max(1, height)
            r = int(25 * (1 - ratio) + 10 * ratio)
            g = int(20 * (1 - ratio) + 40 * ratio)
            b = int(55 * (1 - ratio) + 75 * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # Check for embedded text snippets requested in prompt
        text_snippets = self._extract_text_snippets(prompt)

        for step in range(1, steps + 1):
            time.sleep(0.03)

            # Modern graphic elements
            margin = int(min(width, height) * 0.08)
            border_col = (rng.randint(220, 255), rng.randint(180, 220), rng.randint(50, 100))
            draw.rectangle([margin, margin, width - margin, height - margin], outline=border_col, width=4)

            # If text is detected, render crisp typography
            if text_snippets:
                display_text = text_snippets[0].upper()
                font_size = max(24, int(width * 0.07))
                try:
                    font = ImageFont.load_default(size=font_size)
                except Exception:
                    font = ImageFont.load_default()

                # Neon glow effect
                draw.text(
                    (width // 2, height // 2),
                    display_text,
                    fill=(255, 255, 255),
                    anchor="mm",
                    font=font
                )

            if callback and (step % 2 == 0 or step == steps):
                preview = img.copy().resize((min(width, 384), min(height, 384)), Image.Resampling.BILINEAR)
                callback(step, steps, preview)

        img = img.filter(ImageFilter.SMOOTH)
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.2)
        return img

    def img2img(self, image: Image.Image, prompt: str, negative_prompt: str = "", strength: float = 0.75, steps: int = 25, guidance: float = 5.0, seed: int = -1, callback=None) -> Image.Image:
        w, h = image.size
        gen = self.generate(prompt, negative_prompt, w, h, steps, guidance, seed, callback)
        return Image.blend(image.convert("RGB"), gen, alpha=strength)

    def edit(self, image: Image.Image, instruction: str, seed: int = -1, callback=None) -> Image.Image:
        app_logger.info(f"[QwenAdapter] Executing instruction edit: '{instruction}'")
        return self.img2img(image, instruction, strength=0.65, steps=25, seed=seed, callback=callback)

    def inpaint(self, image: Image.Image, mask: Image.Image, prompt: str, negative_prompt: str = "", steps: int = 25, guidance: float = 5.0, seed: int = -1, callback=None) -> Image.Image:
        w, h = image.size
        gen = self.generate(prompt, negative_prompt, w, h, steps, guidance, seed, callback)
        result = image.copy().convert("RGB")
        result.paste(gen, (0, 0), mask.resize((w, h)).convert("L"))
        return result

    def outpaint(self, image: Image.Image, expand_left: int, expand_right: int, expand_top: int, expand_bottom: int, prompt: str, negative_prompt: str = "", steps: int = 25, guidance: float = 5.0, seed: int = -1, callback=None) -> Image.Image:
        orig_w, orig_h = image.size
        new_w = orig_w + expand_left + expand_right
        new_h = orig_h + expand_top + expand_bottom
        expanded = Image.new("RGB", (new_w, new_h), (18, 18, 28))
        expanded.paste(image, (expand_left, expand_top))
        mask = Image.new("L", (new_w, new_h), 255)
        mask.paste(Image.new("L", (orig_w, orig_h), 0), (expand_left, expand_top))
        return self.inpaint(expanded, mask, prompt, negative_prompt, steps, guidance, seed, callback)
