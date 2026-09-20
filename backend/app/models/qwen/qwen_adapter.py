import gc
import re
import random
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import torch

from backend.app.models.base_adapter import BaseImageModelAdapter, is_dev_simulation_mode
from backend.app.models.scheduler_factory import SchedulerFactory
from backend.app.core.exceptions import ModelLoadError
from backend.app.core.config import settings
from backend.app.core.logger import app_logger

class QwenAdapter(BaseImageModelAdapter):
    """
    Qwen Image Adapter.
    Specialized for typography, in-image text rendering, signs, posters,
    and instruction-based editing.
    """
    def __init__(self, model_id: str = "qwen-image"):
        super().__init__(model_id=model_id, name="Qwen Image", architecture="qwen")
        self.pipeline = None

    def _find_model_path(self) -> Optional[Path]:
        for mdir in settings.paths.model_dirs:
            p = Path(mdir) / self.model_id
            if p.exists() and any(p.glob("**/*.safetensors")):
                return p
        return None

    def has_weights(self) -> bool:
        return self._find_model_path() is not None

    def load(self, device: str = "cuda", vram_strategy: str = "BALANCED", precision: str = "bf16") -> bool:
        app_logger.info(f"[QwenAdapter] Loading {self.name} (device={device}, strategy={vram_strategy})")
        self.loaded_device = device
        self.current_vram_strategy = vram_strategy

        model_path = self._find_model_path()
        if not model_path or not torch.cuda.is_available():
            if not is_dev_simulation_mode():
                self.is_loaded = False
                self.pipeline = None
                raise ModelLoadError(
                    f"No model weights found for '{self.name}'. Place Qwen safetensors in models/{self.model_id}."
                )
            app_logger.info(f"[QwenAdapter] DEV_SIMULATION_MODE active: using mock generator.")
            self.is_loaded = True
            return True

        try:
            # If native Qwen diffusers pipeline is installed, load it
            from diffusers import DiffusionPipeline
            app_logger.info(f"[QwenAdapter] Loading pipeline from {model_path}...")
            pipe = DiffusionPipeline.from_pretrained(str(model_path), torch_dtype=torch.bfloat16)
            if vram_strategy == "FULL_GPU":
                pipe.to(device)
            else:
                pipe.enable_model_cpu_offload()
            self.pipeline = pipe
            self.is_loaded = True
            return True
        except Exception as e:
            app_logger.warning(f"[QwenAdapter] Could not load native pipeline from {model_path}: {e}")
            if not is_dev_simulation_mode():
                self.is_loaded = False
                raise ModelLoadError(f"Failed to load Qwen pipeline: {e}") from e
            self.is_loaded = True
            return True

    def unload(self) -> bool:
        app_logger.info(f"[QwenAdapter] Unloading {self.name}")
        self.pipeline = None
        self.is_loaded = False
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
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
            "sampler": "Default (Recommended)",
            "scheduler": "Karras",
            "optimal_aspect_ratio": "3:4"
        }

    def supports_lora(self) -> bool:
        return False

    def load_lora(self, lora_path: str, weight: float = 1.0) -> bool:
        return False

    def unload_lora(self, lora_path: str) -> bool:
        return False

    def unload_all_loras(self) -> bool:
        self.loaded_loras.clear()
        return True

    def _extract_text_snippets(self, prompt: str) -> List[str]:
        matches = re.findall(r'["\']([^"\']+)["\']', prompt)
        if not matches:
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
        sampler: str = "Default (Recommended)",
        callback: Optional[Callable[[int, int, Optional[Image.Image]], None]] = None,
        reference_image: Optional[Image.Image] = None,
        reference_mode: Optional[str] = None,
        reference_strength: float = 0.6,
        reference_image_2: Optional[Image.Image] = None,
        reference_mode_2: Optional[str] = None,
        reference_strength_2: float = 0.6,
        **kwargs: Any
    ) -> Image.Image:
        actual_seed = random.randint(0, 2**32 - 1) if seed < 0 else seed

        if self.pipeline is not None:
            SchedulerFactory.validate_sampler("qwen", sampler)
            custom_sched = SchedulerFactory.create_scheduler(self.pipeline.scheduler.config, "qwen", sampler)
            if custom_sched:
                self.pipeline.scheduler = custom_sched

            generator = torch.Generator(device="cuda" if torch.cuda.is_available() else "cpu").manual_seed(actual_seed)
            output = self.pipeline(
                prompt=prompt,
                negative_prompt=negative_prompt if negative_prompt else None,
                width=width,
                height=height,
                num_inference_steps=steps,
                guidance_scale=guidance,
                generator=generator
            )
            return output.images[0]

        if not is_dev_simulation_mode():
            raise RuntimeError(f"Cannot generate: '{self.name}' weights are not loaded.")

        rng = random.Random(actual_seed)
        img = Image.new("RGB", (width, height), (18, 18, 28))
        draw = ImageDraw.Draw(img)

        for y in range(height):
            ratio = y / max(1, height)
            r = int(25 * (1 - ratio) + 10 * ratio)
            g = int(20 * (1 - ratio) + 40 * ratio)
            b = int(55 * (1 - ratio) + 75 * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        text_snippets = self._extract_text_snippets(prompt)

        for step in range(1, steps + 1):
            time.sleep(0.01)
            margin = int(min(width, height) * 0.08)
            border_col = (rng.randint(220, 255), rng.randint(180, 220), rng.randint(50, 100))
            draw.rectangle([margin, margin, width - margin, height - margin], outline=border_col, width=4)

            if text_snippets:
                display_text = text_snippets[0].upper()
                font_size = max(24, int(width * 0.07))
                try:
                    font = ImageFont.load_default(size=font_size)
                except Exception:
                    font = ImageFont.load_default()

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

    def img2img(self, image: Image.Image, prompt: str, negative_prompt: str = "", strength: float = 0.75, steps: int = 25, guidance: float = 5.0, seed: int = -1, sampler: str = "Default (Recommended)", scheduler: str = "Default", callback=None) -> Image.Image:
        w, h = image.size
        gen = self.generate(prompt, negative_prompt, w, h, steps, guidance, seed, sampler, scheduler, callback)
        return Image.blend(image.convert("RGB"), gen, alpha=strength)

    def edit(self, image: Image.Image, instruction: str, seed: int = -1, callback=None) -> Image.Image:
        app_logger.info(f"[QwenAdapter] Executing instruction edit: '{instruction}'")
        return self.img2img(image, instruction, strength=0.65, steps=25, seed=seed, callback=callback)

    def inpaint(self, image: Image.Image, mask: Image.Image, prompt: str, negative_prompt: str = "", steps: int = 25, guidance: float = 5.0, seed: int = -1, sampler: str = "Default (Recommended)", scheduler: str = "Default", callback=None) -> Image.Image:
        w, h = image.size
        gen = self.generate(prompt, negative_prompt, w, h, steps, guidance, seed, sampler, scheduler, callback)
        result = image.copy().convert("RGB")
        result.paste(gen, (0, 0), mask.resize((w, h)).convert("L"))
        return result

    def outpaint(self, image: Image.Image, expand_left: int, expand_right: int, expand_top: int, expand_bottom: int, prompt: str, negative_prompt: str = "", steps: int = 25, guidance: float = 5.0, seed: int = -1, sampler: str = "Default (Recommended)", scheduler: str = "Default", callback=None) -> Image.Image:
        orig_w, orig_h = image.size
        new_w = orig_w + expand_left + expand_right
        new_h = orig_h + expand_top + expand_bottom
        expanded = Image.new("RGB", (new_w, new_h), (18, 18, 28))
        expanded.paste(image, (expand_left, expand_top))
        mask = Image.new("L", (new_w, new_h), 255)
        mask.paste(Image.new("L", (orig_w, orig_h), 0), (expand_left, expand_top))
        return self.inpaint(expanded, mask, prompt, negative_prompt, steps, guidance, seed, sampler, scheduler, callback)
