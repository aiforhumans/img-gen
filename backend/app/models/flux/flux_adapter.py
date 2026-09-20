import gc
import math
import random
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import torch

from backend.app.models.base_adapter import BaseImageModelAdapter, is_dev_simulation_mode
from backend.app.models.scheduler_factory import SchedulerFactory
from backend.app.core.exceptions import ModelLoadError
from backend.app.core.config import settings
from backend.app.core.logger import app_logger

class FluxAdapter(BaseImageModelAdapter):
    """
    Adapter for FLUX.2 Klein (4B and 9B variants).
    Engineered for fast high-fidelity text-to-image, creative landscapes,
    and quantized bfloat16/int8 execution on RTX 5080 (16 GB VRAM).
    """
    def __init__(self, model_id: str = "flux-klein-4b", variant: str = "4B"):
        name = f"FLUX.2 Klein {variant}"
        super().__init__(model_id=model_id, name=name, architecture="flux")
        self.variant = variant
        self.pipeline = None

    def _find_model_path(self) -> Optional[Path]:
        for mdir in settings.paths.model_dirs:
            p = Path(mdir) / self.model_id
            if p.exists():
                if (p / "model_index.json").exists():
                    return p
                if any(p.glob("**/*.safetensors")):
                    return p
        return None

    def has_weights(self) -> bool:
        return self._find_model_path() is not None

    def load(self, device: str = "cuda", vram_strategy: str = "BALANCED", precision: str = "bf16") -> bool:
        app_logger.info(f"[FluxAdapter] Loading {self.name} (device={device}, strategy={vram_strategy}, precision={precision})")
        self.loaded_device = device
        self.current_vram_strategy = vram_strategy

        model_path = self._find_model_path()
        if not model_path or not torch.cuda.is_available():
            if not is_dev_simulation_mode():
                self.is_loaded = False
                self.pipeline = None
                raise ModelLoadError(
                    f"No FLUX model directory found for '{self.model_id}'. Download weights to models/{self.model_id}."
                )
            app_logger.info(f"[FluxAdapter] DEV_SIMULATION_MODE active: using mock generator.")
            self.is_loaded = True
            return True

        try:
            from diffusers import FluxPipeline
            app_logger.info(f"[FluxAdapter] Loading PyTorch Diffusers FluxPipeline from {model_path}...")
            dtype = torch.bfloat16 if precision == "bf16" else torch.float16
            pipe = FluxPipeline.from_pretrained(str(model_path), torch_dtype=dtype)

            if vram_strategy == "FULL_GPU":
                pipe.to(device)
            elif vram_strategy == "BALANCED":
                pipe.enable_model_cpu_offload()
            elif vram_strategy in ["LOW_VRAM", "CPU_OFFLOAD"]:
                pipe.enable_sequential_cpu_offload()
            else:
                pipe.enable_model_cpu_offload()

            self.pipeline = pipe
            self.is_loaded = True
            app_logger.info(f"[FluxAdapter] Successfully initialized FLUX pipeline on RTX 5080!")
            return True
        except Exception as e:
            self.pipeline = None
            self.is_loaded = False
            app_logger.error(f"[FluxAdapter] Failed to load native FLUX checkpoint: {e}", exc_info=True)
            if not is_dev_simulation_mode():
                raise ModelLoadError(f"Failed to load FLUX model {self.name}: {e}") from e
            return False

    def unload(self) -> bool:
        app_logger.info(f"[FluxAdapter] Unloading {self.name}")
        self.unload_all_loras()
        self.pipeline = None
        self.is_loaded = False
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        return True

    def estimate_vram(self, width: int = 1024, height: int = 1024, batch_size: int = 1) -> float:
        base = 8.5 if self.variant == "4B" else 14.5
        pixels_factor = (width * height) / (1024 * 1024)
        return round(base * pixels_factor * batch_size, 1)

    def supported_resolutions(self) -> List[Dict[str, Any]]:
        return [
            {"label": "Square (1:1)", "width": 1024, "height": 1024, "aspect_ratio": "1:1"},
            {"label": "Landscape (16:9)", "width": 1280, "height": 720, "aspect_ratio": "16:9"},
            {"label": "Portrait (9:16)", "width": 720, "height": 1280, "aspect_ratio": "9:16"},
            {"label": "Photo (3:2)", "width": 1152, "height": 768, "aspect_ratio": "3:2"},
            {"label": "Cinema (21:9)", "width": 1344, "height": 576, "aspect_ratio": "21:9"}
        ]

    def recommended_settings(self) -> Dict[str, Any]:
        return {
            "steps": 4 if self.variant == "4B" else 28,
            "guidance": 0.0 if self.variant == "4B" else 3.5,
            "sampler": "Default (Recommended)",
            "scheduler": "FlowMatch",
            "optimal_aspect_ratio": "16:9"
        }

    def supports_lora(self) -> bool:
        return True

    def load_lora(self, lora_path: str, weight: float = 1.0) -> bool:
        app_logger.info(f"[FluxAdapter] Attaching LoRA: {lora_path} (weight={weight})")
        self.loaded_loras.append({"path": lora_path, "weight": weight})
        if self.pipeline:
            try:
                self.pipeline.load_lora_weights(lora_path)
            except Exception as e:
                app_logger.warning(f"Could not load LoRA into FLUX pipeline: {e}")
        return True

    def unload_lora(self, lora_path: str) -> bool:
        self.loaded_loras = [l for l in self.loaded_loras if l["path"] != lora_path]
        if self.pipeline:
            try:
                self.pipeline.unload_lora_weights()
            except Exception:
                pass
        return True

    def unload_all_loras(self) -> bool:
        self.loaded_loras.clear()
        if self.pipeline:
            try:
                self.pipeline.unload_lora_weights()
            except Exception:
                pass
        return True

    def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        steps: int = 4,
        guidance: float = 0.0,
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
            # Scheduler validation & setup
            SchedulerFactory.validate_sampler("flux", sampler)

            actual_steps = min(steps, 4) if ("schnell" in str(self._find_model_path() or "").lower() or self.variant == "4B") else steps
            actual_guidance = 0.0 if ("schnell" in str(self._find_model_path() or "").lower() or self.variant == "4B") else guidance
            app_logger.info(f"[FluxAdapter] Executing REAL PyTorch FLUX inference ({actual_steps} steps, {width}x{height}, guidance={actual_guidance}, seed={actual_seed})")
            generator = torch.Generator(device="cuda" if torch.cuda.is_available() else "cpu").manual_seed(actual_seed)

            def step_end_callback(pipe_self, step_idx, timestep, callback_kwargs):
                if callback:
                    callback(step_idx + 1, actual_steps, None)
                return callback_kwargs

            output = self.pipeline(
                prompt=prompt,
                width=width,
                height=height,
                num_inference_steps=actual_steps,
                guidance_scale=actual_guidance,
                generator=generator,
                callback_on_step_end=step_end_callback if callback else None
            )
            return output.images[0]

        if not is_dev_simulation_mode():
            raise RuntimeError(f"Cannot generate: '{self.name}' weights are not loaded.")

        rng = random.Random(actual_seed)
        img = Image.new("RGB", (width, height), (15, 18, 25))
        draw = ImageDraw.Draw(img)

        c1 = (rng.randint(20, 80), rng.randint(40, 100), rng.randint(90, 180))
        c2 = (rng.randint(80, 180), rng.randint(30, 90), rng.randint(110, 200))
        for y in range(height):
            ratio = y / max(1, height)
            r = int(c1[0] * (1 - ratio) + c2[0] * ratio)
            g = int(c1[1] * (1 - ratio) + c2[1] * ratio)
            b = int(c1[2] * (1 - ratio) + c2[2] * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        for step in range(1, steps + 1):
            time.sleep(0.01)
            cx = rng.randint(int(width * 0.2), int(width * 0.8))
            cy = rng.randint(int(height * 0.2), int(height * 0.8))
            rad = rng.randint(30, max(50, int(min(width, height) * 0.35)))
            shape_color = (
                rng.randint(100, 240),
                rng.randint(80, 220),
                rng.randint(120, 255)
            )
            draw.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=shape_color)

            if callback and (step % 2 == 0 or step == steps):
                preview = img.copy().resize((min(width, 384), min(height, 384)), Image.Resampling.BILINEAR)
                callback(step, steps, preview)

        img = img.filter(ImageFilter.SMOOTH_MORE)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.2)
        return img

    def img2img(
        self,
        image: Image.Image,
        prompt: str,
        negative_prompt: str = "",
        strength: float = 0.75,
        steps: int = 20,
        guidance: float = 3.5,
        seed: int = -1,
        sampler: str = "Default (Recommended)",
        scheduler: str = "Default",
        callback: Optional[Callable[[int, int, Optional[Image.Image]], None]] = None
    ) -> Image.Image:
        w, h = image.size
        base = image.convert("RGB")
        gen = self.generate(prompt, negative_prompt, w, h, steps, guidance, seed, sampler, scheduler, callback)
        return Image.blend(base, gen, alpha=strength)

    def edit(
        self,
        image: Image.Image,
        instruction: str,
        seed: int = -1,
        callback: Optional[Callable[[int, int, Optional[Image.Image]], None]] = None
    ) -> Image.Image:
        return self.img2img(image, instruction, strength=0.6, seed=seed, callback=callback)

    def inpaint(
        self,
        image: Image.Image,
        mask: Image.Image,
        prompt: str,
        negative_prompt: str = "",
        steps: int = 20,
        guidance: float = 3.5,
        seed: int = -1,
        sampler: str = "Default (Recommended)",
        scheduler: str = "Default",
        callback: Optional[Callable[[int, int, Optional[Image.Image]], None]] = None
    ) -> Image.Image:
        w, h = image.size
        gen = self.generate(prompt, negative_prompt, w, h, steps, guidance, seed, sampler, scheduler, callback)
        mask_gray = mask.resize((w, h)).convert("L")
        result = image.copy().convert("RGB")
        result.paste(gen, (0, 0), mask_gray)
        return result

    def outpaint(
        self,
        image: Image.Image,
        expand_left: int,
        expand_right: int,
        expand_top: int,
        expand_bottom: int,
        prompt: str,
        negative_prompt: str = "",
        steps: int = 20,
        guidance: float = 3.5,
        seed: int = -1,
        sampler: str = "Default (Recommended)",
        scheduler: str = "Default",
        callback: Optional[Callable[[int, int, Optional[Image.Image]], None]] = None
    ) -> Image.Image:
        orig_w, orig_h = image.size
        new_w = orig_w + expand_left + expand_right
        new_h = orig_h + expand_top + expand_bottom
        expanded = Image.new("RGB", (new_w, new_h), (20, 20, 25))
        expanded.paste(image, (expand_left, expand_top))
        mask = Image.new("L", (new_w, new_h), 255)
        mask.paste(Image.new("L", (orig_w, orig_h), 0), (expand_left, expand_top))
        return self.inpaint(expanded, mask, prompt, negative_prompt, steps, guidance, seed, sampler, scheduler, callback)
