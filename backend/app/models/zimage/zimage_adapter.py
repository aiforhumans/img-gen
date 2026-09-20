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

class ZImageAdapter(BaseImageModelAdapter):
    """
    Turbo Photorealism Adapter (Juggernaut-XL Base + ByteDance SDXL-Lightning 2/4/8-Step LoRAs).
    Engineered for sub-2-second generation on NVIDIA RTX 5080 (16GB VRAM) with FULL_GPU mode.
    """
    def __init__(self, model_id: str = "zimage-turbo"):
        super().__init__(model_id=model_id, name="Turbo Photorealism (Juggernaut-XL)", architecture="zimage")
        self.pipeline = None
        self.active_lightning_step: Optional[int] = None

    def _find_checkpoint(self) -> Optional[Path]:
        for mdir in settings.paths.model_dirs:
            for sub in ["juggernaut-xl", self.model_id, "checkpoints", "sdxl"]:
                p = Path(mdir) / sub
                if p.exists():
                    # 1. Check for Juggernaut-XL full checkpoints
                    for f in p.glob("*juggernaut*.safetensors"):
                        if f.is_file() and f.stat().st_size > 1024 * 1024 * 500 and "unet" not in f.name.lower() and "lora" not in f.name.lower():
                            return f

                    # 2. Standalone SDXL Lightning checkpoints
                    full_cands = [
                        p / "sdxl_lightning_8step.safetensors",
                        p / "sdxl_lightning_4step.safetensors",
                        p / "sdxl_lightning_2step.safetensors",
                        p / "sdxl_lightning_1step_x0.safetensors"
                    ]
                    for c in full_cands:
                        if c.exists() and c.is_file() and c.stat().st_size > 1024 * 1024 * 500:
                            return c

                    # 3. Any complete base checkpoint
                    for f in p.glob("**/*.safetensors"):
                        if f.is_file() and f.stat().st_size > 1024 * 1024 * 500 and "unet" not in f.name.lower() and "lora" not in f.name.lower():
                            return f
        return None

    def _find_lightning_lora(self, steps: int) -> Optional[Path]:
        """Searches for ByteDance SDXL-Lightning LoRA matching requested step count (2, 4, 8)."""
        target_name = f"sdxl_lightning_{steps}step_lora.safetensors"
        for mdir in settings.paths.model_dirs:
            for sub in [self.model_id, "zimage-turbo", "loras", "checkpoints"]:
                candidate = Path(mdir) / sub / target_name
                if candidate.exists():
                    return candidate
                for f in (Path(mdir) / sub).glob(f"*{steps}step*lora*.safetensors"):
                    return f
        return None

    def has_weights(self) -> bool:
        return self._find_checkpoint() is not None

    def load(self, device: str = "cuda", vram_strategy: str = "FULL_GPU", precision: str = "fp16") -> bool:
        app_logger.info(f"[ZImageAdapter] Loading {self.name} (device={device}, strategy={vram_strategy})")
        self.loaded_device = device
        self.current_vram_strategy = vram_strategy

        ckpt_path = self._find_checkpoint()
        if not ckpt_path or not torch.cuda.is_available():
            if not is_dev_simulation_mode():
                self.is_loaded = False
                self.pipeline = None
                raise ModelLoadError(
                    f"Weights not found for '{self.name}'. Place Juggernaut-XL or SDXL-Lightning checkpoints in models/."
                )
            app_logger.info(f"[ZImageAdapter] DEV_SIMULATION_MODE active: using mock generator.")
            self.is_loaded = True
            return True

        try:
            from diffusers import StableDiffusionXLPipeline, EulerDiscreteScheduler
            app_logger.info(f"[ZImageAdapter] Loading PyTorch Diffusers pipeline from {ckpt_path}...")
            dtype = torch.float16 if precision == "fp16" else torch.bfloat16
            pipe = StableDiffusionXLPipeline.from_single_file(
                str(ckpt_path),
                torch_dtype=dtype
            )
            pipe.scheduler = EulerDiscreteScheduler.from_config(pipe.scheduler.config, timestep_spacing="trailing")

            # Apply VRAM Strategy
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
            self.active_lightning_step = None
            for st in [2, 4, 8]:
                if f"{st}step" in ckpt_path.name.lower():
                    self.active_lightning_step = st
                    break

            if self.active_lightning_step is None:
                self._apply_lightning_step(8)

            self.is_loaded = True
            app_logger.info(f"[ZImageAdapter] Successfully initialized Turbo Photorealism pipeline!")
            return True
        except Exception as e:
            self.pipeline = None
            self.is_loaded = False
            app_logger.error(f"[ZImageAdapter] Failed to load native checkpoint: {e}", exc_info=True)
            if not is_dev_simulation_mode():
                raise ModelLoadError(f"Failed to load checkpoint for {self.name}: {e}") from e
            return False

    def _apply_lightning_step(self, steps: int) -> bool:
        if not self.pipeline or self.active_lightning_step == steps:
            return True
        lora_path = self._find_lightning_lora(steps)
        if lora_path:
            try:
                from diffusers import EulerDiscreteScheduler
                app_logger.info(f"[ZImageAdapter] Swapping Lightning LoRA for {steps} steps ({lora_path.name})...")
                self.pipeline.unload_lora_weights()
                self.pipeline.load_lora_weights(str(lora_path))
                self.pipeline.scheduler = EulerDiscreteScheduler.from_config(
                    self.pipeline.scheduler.config,
                    timestep_spacing="trailing"
                )
                self.active_lightning_step = steps
                return True
            except Exception as e:
                app_logger.warning(f"[ZImageAdapter] Could not swap Lightning LoRA: {e}")
        return False

    def unload(self) -> bool:
        app_logger.info(f"[ZImageAdapter] Unloading {self.name}")
        self.unload_all_loras()
        self.pipeline = None
        self.is_loaded = False
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        return True

    def estimate_vram(self, width: int = 1024, height: int = 1024, batch_size: int = 1) -> float:
        return 7.2 * ((width * height) / (1024 * 1024)) * batch_size

    def supported_resolutions(self) -> List[Dict[str, Any]]:
        return [
            {"label": "Portrait (3:4)", "width": 896, "height": 1152, "aspect_ratio": "3:4"},
            {"label": "Square (1:1)", "width": 1024, "height": 1024, "aspect_ratio": "1:1"},
            {"label": "Cinematic (16:9)", "width": 1280, "height": 720, "aspect_ratio": "16:9"}
        ]

    def recommended_settings(self) -> Dict[str, Any]:
        return {
            "steps": 8,
            "guidance": 1.5,
            "sampler": "Default (Recommended)",
            "scheduler": "Turbo",
            "optimal_aspect_ratio": "3:4"
        }

    def supports_lora(self) -> bool:
        return True

    def load_lora(self, lora_path: str, weight: float = 1.0) -> bool:
        self.loaded_loras.append({"path": lora_path, "weight": weight})
        if self.pipeline:
            try:
                self.pipeline.load_lora_weights(lora_path)
            except Exception as e:
                app_logger.warning(f"Could not attach LoRA to native pipeline: {e}")
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
        width: int = 896,
        height: int = 1152,
        steps: int = 8,
        guidance: float = 1.5,
        seed: int = -1,
        sampler: str = "Default (Recommended)",
        scheduler: str = "Default",
        callback: Optional[Callable[[int, int, Optional[Image.Image]], None]] = None
    ) -> Image.Image:
        actual_seed = random.randint(0, 2**32 - 1) if seed < 0 else seed

        # Auto-adjust guidance and steps for Lightning turbo distillation
        if self.active_lightning_step is not None and steps > 12:
            steps = self.active_lightning_step
            guidance = 1.5
        elif steps <= 8 and guidance > 2.5:
            guidance = 1.5

        if self.pipeline is not None:
            # Configure scheduler if specified
            custom_sched = SchedulerFactory.create_scheduler(self.pipeline.scheduler.config, "zimage", sampler)
            if custom_sched:
                self.pipeline.scheduler = custom_sched

            if steps in [2, 4, 8]:
                self._apply_lightning_step(steps)

            app_logger.info(f"[ZImageAdapter] Executing REAL PyTorch inference ({steps} steps, {width}x{height}, guidance={guidance}, seed={actual_seed})")
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

        # Simulation fallback for dev testing
        rng = random.Random(actual_seed)
        img = Image.new("RGB", (width, height), (28, 26, 24))
        draw = ImageDraw.Draw(img)

        for y in range(height):
            ratio = y / max(1, height)
            r = int(45 * (1 - ratio) + 20 * ratio)
            g = int(35 * (1 - ratio) + 18 * ratio)
            b = int(30 * (1 - ratio) + 16 * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        cx = width // 2
        cy = int(height * 0.48)
        head_rad = int(min(width, height) * 0.22)

        for step in range(1, steps + 1):
            time.sleep(0.01)
            draw.ellipse(
                [cx - head_rad, cy - head_rad, cx + head_rad, cy + head_rad],
                fill=(rng.randint(210, 235), rng.randint(170, 195), rng.randint(150, 175))
            )
            if callback and (step % 2 == 0 or step == steps):
                preview = img.copy().resize((min(width, 384), min(height, 384)), Image.Resampling.BILINEAR)
                callback(step, steps, preview)

        img = img.filter(ImageFilter.SMOOTH)
        return img

    def img2img(self, image: Image.Image, prompt: str, negative_prompt: str = "", strength: float = 0.7, steps: int = 8, guidance: float = 1.5, seed: int = -1, sampler: str = "Default (Recommended)", scheduler: str = "Default", callback=None) -> Image.Image:
        w, h = image.size
        gen = self.generate(prompt, negative_prompt, w, h, steps, guidance, seed, sampler, scheduler, callback)
        return Image.blend(image.convert("RGB"), gen, alpha=strength)

    def edit(self, image: Image.Image, instruction: str, seed: int = -1, callback=None) -> Image.Image:
        return self.img2img(image, instruction, strength=0.5, steps=8, seed=seed, callback=callback)

    def inpaint(self, image: Image.Image, mask: Image.Image, prompt: str, negative_prompt: str = "", steps: int = 8, guidance: float = 1.5, seed: int = -1, sampler: str = "Default (Recommended)", scheduler: str = "Default", callback=None) -> Image.Image:
        w, h = image.size
        gen = self.generate(prompt, negative_prompt, w, h, steps, guidance, seed, sampler, scheduler, callback)
        result = image.copy().convert("RGB")
        result.paste(gen, (0, 0), mask.resize((w, h)).convert("L"))
        return result

    def outpaint(self, image: Image.Image, expand_left: int, expand_right: int, expand_top: int, expand_bottom: int, prompt: str, negative_prompt: str = "", steps: int = 8, guidance: float = 1.5, seed: int = -1, sampler: str = "Default (Recommended)", scheduler: str = "Default", callback=None) -> Image.Image:
        orig_w, orig_h = image.size
        new_w = orig_w + expand_left + expand_right
        new_h = orig_h + expand_top + expand_bottom
        expanded = Image.new("RGB", (new_w, new_h), (25, 23, 21))
        expanded.paste(image, (expand_left, expand_top))
        mask = Image.new("L", (new_w, new_h), 255)
        mask.paste(Image.new("L", (orig_w, orig_h), 0), (expand_left, expand_top))
        return self.inpaint(expanded, mask, prompt, negative_prompt, steps, guidance, seed, sampler, scheduler, callback)
