import gc
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

class SDXLAdapter(BaseImageModelAdapter):
    """
    SDXL / SDXL Turbo Adapter.
    Specialized for legacy checkpoint compatibility, extensive CivitAI LoRA ecosystem,
    and ControlNet integrations.
    """
    def __init__(self, model_id: str = "sdxl"):
        super().__init__(model_id=model_id, name="Stable Diffusion XL", architecture="sdxl")
        self.pipeline = None

    def _find_checkpoint(self) -> Optional[Path]:
        for mdir in settings.paths.model_dirs:
            subdirs = [self.model_id]
            if self.model_id in ["sdxl", "zimage-turbo"]:
                subdirs.extend(["zimage-turbo", "checkpoints"])
            for sub in subdirs:
                p = Path(mdir) / sub
                if p.exists():
                    cands = [
                        p / "sdxl_lightning_8step.safetensors",
                        p / "sdxl_lightning_4step.safetensors",
                        p / "sdxl_lightning_2step.safetensors"
                    ]
                    for c in cands:
                        if c.exists() and c.stat().st_size > 1024 * 1024 * 500:
                            return c
                    for f in p.glob("**/*.safetensors"):
                        if f.stat().st_size > 1024 * 1024 * 500 and "unet" not in f.name.lower() and "lora" not in f.name.lower():
                            return f
        return None

    def has_weights(self) -> bool:
        return self._find_checkpoint() is not None

    def load(self, device: str = "cuda", vram_strategy: str = "BALANCED", precision: str = "fp16") -> bool:
        app_logger.info(f"[SDXLAdapter] Loading {self.name} (device={device}, strategy={vram_strategy})")
        self.loaded_device = device
        self.current_vram_strategy = vram_strategy

        ckpt_path = self._find_checkpoint()
        if not ckpt_path or not torch.cuda.is_available():
            if not is_dev_simulation_mode():
                self.is_loaded = False
                self.pipeline = None
                raise ModelLoadError(f"No checkpoint weights found for '{self.name}'. Place model in models/sdxl/.")
            app_logger.info(f"[SDXLAdapter] DEV_SIMULATION_MODE active: using mock generator.")
            self.is_loaded = True
            return True

        try:
            from diffusers import StableDiffusionXLPipeline, EulerDiscreteScheduler
            app_logger.info(f"[SDXLAdapter] Loading Diffusers pipeline from {ckpt_path}...")
            dtype = torch.float16 if precision == "fp16" else torch.bfloat16
            pipe = StableDiffusionXLPipeline.from_single_file(
                str(ckpt_path),
                torch_dtype=dtype
            )
            pipe.scheduler = EulerDiscreteScheduler.from_config(pipe.scheduler.config, timestep_spacing="trailing")

            if vram_strategy == "FULL_GPU":
                pipe.to(device)
            elif vram_strategy == "BALANCED":
                pipe.enable_model_cpu_offload()
            elif vram_strategy == "LOW_VRAM":
                pipe.enable_model_cpu_offload()
                if hasattr(pipe, "enable_vae_tiling"):
                    pipe.enable_vae_tiling()
                elif hasattr(pipe, "vae") and hasattr(pipe.vae, "enable_tiling"):
                    pipe.vae.enable_tiling()
                if hasattr(pipe, "enable_vae_slicing"):
                    pipe.enable_vae_slicing()
                elif hasattr(pipe, "vae") and hasattr(pipe.vae, "enable_slicing"):
                    pipe.vae.enable_slicing()
            elif vram_strategy == "CPU_OFFLOAD":
                pipe.enable_sequential_cpu_offload()
                if hasattr(pipe, "enable_vae_tiling"):
                    pipe.enable_vae_tiling()
                elif hasattr(pipe, "vae") and hasattr(pipe.vae, "enable_tiling"):
                    pipe.vae.enable_tiling()
            else:
                pipe.to(device)

            self.pipeline = pipe
            self.is_loaded = True
            app_logger.info(f"[SDXLAdapter] Successfully loaded SDXL pipeline into memory!")
            return True
        except Exception as e:
            self.pipeline = None
            self.is_loaded = False
            app_logger.error(f"[SDXLAdapter] Failed to load SDXL checkpoint: {e}", exc_info=True)
            if not is_dev_simulation_mode():
                raise ModelLoadError(f"Failed to load checkpoint for {self.name}: {e}") from e
            return False

    def unload(self) -> bool:
        app_logger.info(f"[SDXLAdapter] Unloading {self.name}")
        self.unload_all_loras()
        self.pipeline = None
        self.is_loaded = False
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        return True

    def estimate_vram(self, width: int = 1024, height: int = 1024, batch_size: int = 1) -> float:
        return 7.0 * ((width * height) / (1024 * 1024)) * batch_size

    def supported_resolutions(self) -> List[Dict[str, Any]]:
        return [
            {"label": "Square (1:1)", "width": 1024, "height": 1024, "aspect_ratio": "1:1"},
            {"label": "Landscape (16:9)", "width": 1152, "height": 648, "aspect_ratio": "16:9"},
            {"label": "Portrait (9:16)", "width": 648, "height": 1152, "aspect_ratio": "9:16"},
            {"label": "Photo (3:2)", "width": 1152, "height": 768, "aspect_ratio": "3:2"}
        ]

    def recommended_settings(self) -> Dict[str, Any]:
        return {
            "steps": 25,
            "guidance": 7.0,
            "sampler": "Default (Recommended)",
            "scheduler": "Normal",
            "optimal_aspect_ratio": "1:1"
        }

    def supports_lora(self) -> bool:
        return True

    def load_lora(self, lora_path: str, weight: float = 1.0) -> bool:
        app_logger.info(f"[SDXLAdapter] Attaching SDXL LoRA '{lora_path}' (weight={weight})")
        self.loaded_loras.append({"path": lora_path, "weight": weight})
        if self.pipeline:
            try:
                self.pipeline.load_lora_weights(lora_path)
            except Exception as e:
                app_logger.warning(f"Could not load LoRA into pipeline: {e}")
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
        steps: int = 25,
        guidance: float = 7.0,
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
            # Wire sampler
            custom_sched = SchedulerFactory.create_scheduler(self.pipeline.scheduler.config, "sdxl", sampler)
            if custom_sched:
                self.pipeline.scheduler = custom_sched

            app_logger.info(f"[SDXLAdapter] Executing REAL PyTorch inference ({steps} steps, {width}x{height}, seed={actual_seed})")
            generator = torch.Generator(device="cuda" if torch.cuda.is_available() else "cpu").manual_seed(actual_seed)

            def step_end_callback(pipe_self, step_idx, timestep, callback_kwargs):
                if callback:
                    callback(step_idx + 1, steps, None)
                return callback_kwargs

            output = self.pipeline(
                prompt=prompt,
                negative_prompt=negative_prompt if negative_prompt else None,
                width=width,
                height=height,
                num_inference_steps=steps,
                guidance_scale=guidance,
                generator=generator,
                callback_on_step_end=step_end_callback if callback else None
            )
            return output.images[0]

        if not is_dev_simulation_mode():
            raise RuntimeError(f"Cannot generate: '{self.name}' weights are not loaded.")

        rng = random.Random(actual_seed)
        img = Image.new("RGB", (width, height), (22, 22, 30))
        draw = ImageDraw.Draw(img)

        c1 = (rng.randint(30, 90), rng.randint(20, 60), rng.randint(40, 100))
        c2 = (rng.randint(50, 120), rng.randint(80, 150), rng.randint(120, 200))
        for y in range(height):
            ratio = y / max(1, height)
            r = int(c1[0] * (1 - ratio) + c2[0] * ratio)
            g = int(c1[1] * (1 - ratio) + c2[1] * ratio)
            b = int(c1[2] * (1 - ratio) + c2[2] * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        for step in range(1, steps + 1):
            time.sleep(0.01)
            x1 = rng.randint(0, width // 2)
            y1 = rng.randint(0, height // 2)
            x2 = rng.randint(x1 + 50, width)
            y2 = rng.randint(y1 + 50, height)
            fill_col = (rng.randint(60, 220), rng.randint(70, 210), rng.randint(80, 240))
            draw.ellipse([x1, y1, x2, y2], outline=fill_col, width=3)

            if callback and (step % 2 == 0 or step == steps):
                preview = img.copy().resize((min(width, 384), min(height, 384)), Image.Resampling.BILINEAR)
                callback(step, steps, preview)

        img = img.filter(ImageFilter.SMOOTH)
        return img

    def img2img(self, image: Image.Image, prompt: str, negative_prompt: str = "", strength: float = 0.75, steps: int = 25, guidance: float = 7.0, seed: int = -1, sampler: str = "Default (Recommended)", scheduler: str = "Default", callback=None) -> Image.Image:
        w, h = image.size
        gen = self.generate(prompt, negative_prompt, w, h, steps, guidance, seed, sampler, scheduler, callback)
        return Image.blend(image.convert("RGB"), gen, alpha=strength)

    def edit(self, image: Image.Image, instruction: str, seed: int = -1, callback=None) -> Image.Image:
        return self.img2img(image, instruction, strength=0.6, steps=25, seed=seed, callback=callback)

    def inpaint(self, image: Image.Image, mask: Image.Image, prompt: str, negative_prompt: str = "", steps: int = 25, guidance: float = 7.0, seed: int = -1, sampler: str = "Default (Recommended)", scheduler: str = "Default", callback=None) -> Image.Image:
        w, h = image.size
        gen = self.generate(prompt, negative_prompt, w, h, steps, guidance, seed, sampler, scheduler, callback)
        result = image.copy().convert("RGB")
        result.paste(gen, (0, 0), mask.resize((w, h)).convert("L"))
        return result

    def outpaint(self, image: Image.Image, expand_left: int, expand_right: int, expand_top: int, expand_bottom: int, prompt: str, negative_prompt: str = "", steps: int = 25, guidance: float = 7.0, seed: int = -1, sampler: str = "Default (Recommended)", scheduler: str = "Default", callback=None) -> Image.Image:
        orig_w, orig_h = image.size
        new_w = orig_w + expand_left + expand_right
        new_h = orig_h + expand_top + expand_bottom
        expanded = Image.new("RGB", (new_w, new_h), (22, 22, 30))
        expanded.paste(image, (expand_left, expand_top))
        mask = Image.new("L", (new_w, new_h), 255)
        mask.paste(Image.new("L", (orig_w, orig_h), 0), (expand_left, expand_top))
        return self.inpaint(expanded, mask, prompt, negative_prompt, steps, guidance, seed, sampler, scheduler, callback)
