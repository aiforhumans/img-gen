from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

class LoRAConfig(BaseModel):
    path: str
    id: Optional[str] = None
    weight: float = Field(default=1.0, ge=-3.0, le=3.0)

class GenerationConfig(BaseModel):
    """
    Canonical, authoritative generation configuration used across:
    Frontend -> API -> JobQueue -> Router -> ModelAdapter -> PNG metadata -> SQLite Gallery -> Reuse Settings.
    """
    prompt: str = Field(..., min_length=1, description="Primary positive prompt")
    original_prompt: str = Field(default="", description="User entered raw prompt before style/polishing")
    negative_prompt: str = Field(default="", description="Negative prompt instructions")
    enhanced_prompt: Optional[str] = Field(default="", description="LM Studio or rule-expanded prompt")
    model: str = Field(default="zimage-turbo", description="Model backend ID (default: Turbo Photorealism)")
    mode: str = Field(default="photo", description="Generation mode")
    style: str = Field(default="none", description="Style preset ID from config/styles")
    aspect_ratio: str = Field(default="1:1", description="Aspect ratio tag: 1:1, 16:9, 9:16, 3:4, 21:9, custom")
    width: int = Field(default=1024, ge=64, le=4096, description="Pixel width (multiple of 8)")
    height: int = Field(default=1024, ge=64, le=4096, description="Pixel height (multiple of 8)")
    quality: str = Field(default="balanced", description="Quality preset: fast, balanced, quality, maximum")
    steps: int = Field(default=8, ge=1, le=150, description="Denoising inference steps (8 for Turbo)")
    guidance: float = Field(default=1.5, ge=0.0, le=30.0, description="CFG guidance scale (1.5 for Turbo)")
    seed: int = Field(default=-1, description="Random seed (-1 for randomized)")
    sampler: str = Field(default="Default (Recommended)", description="Denoising sampler algorithm")
    scheduler: str = Field(default="Default", description="Step scheduler algorithm")
    loras: List[LoRAConfig] = Field(default_factory=list, description="List of attached LoRA adapters")
    vram_strategy: str = Field(default="FULL_GPU", description="RTX 5080 VRAM Strategy")
    precision: str = Field(default="fp16", description="Execution precision (fp16 or bf16)")

    # Optional image editing fields
    edit_mode: Optional[str] = Field(default=None, description="Edit operation: inpaint, outpaint, img2img, instruct")
    init_image: Optional[str] = Field(default=None, description="Base64 or file path of source image for editing")
    mask_image: Optional[str] = Field(default=None, description="Base64 or file path of mask image for inpainting")
    strength: float = Field(default=0.75, ge=0.0, le=1.0, description="Denoising strength for img2img")
    expand_left: int = Field(default=0, ge=0, le=2048)
    expand_right: int = Field(default=0, ge=0, le=2048)
    expand_top: int = Field(default=0, ge=0, le=2048)
    expand_bottom: int = Field(default=0, ge=0, le=2048)

    # IP-Adapter reference image fields
    reference_image_path: Optional[str] = Field(default=None, description="Path to reference image for IP-Adapter style/subject guidance")
    reference_mode: Optional[str] = Field(default=None, description="IP-Adapter mode: 'style' or 'subject'")
    reference_strength: float = Field(default=0.6, ge=0.0, le=1.5, description="IP-Adapter influence strength (0.0-1.5)")
    reference_image_path_2: Optional[str] = Field(default=None, description="Path to second reference image (e.g. style + subject combo)")
    reference_mode_2: Optional[str] = Field(default=None, description="Second IP-Adapter mode: 'style' or 'subject'")
    reference_strength_2: float = Field(default=0.6, ge=0.0, le=1.5, description="Second reference influence strength")

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Prompt cannot be empty.")
        return s

    @field_validator("width", "height")
    @classmethod
    def validate_dimensions(cls, v: int) -> int:
        if v % 8 != 0:
            # Snap to nearest multiple of 8
            v = int(round(v / 8.0) * 8)
        return max(64, min(4096, v))

    @field_validator("vram_strategy")
    @classmethod
    def validate_vram_strategy(cls, v: str) -> str:
        valid = ["FULL_GPU", "BALANCED", "LOW_VRAM", "CPU_OFFLOAD"]
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"Invalid vram_strategy '{v}'. Must be one of {valid}")
        return upper

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        valid = ["auto", "photo", "creative", "design", "edit"]
        lower = v.lower()
        if lower not in valid:
            raise ValueError(f"Invalid mode '{v}'. Must be one of {valid}")
        return lower

    @field_validator("quality")
    @classmethod
    def validate_quality(cls, v: str) -> str:
        valid = ["fast", "balanced", "quality", "maximum"]
        lower = v.lower()
        if lower not in valid:
            raise ValueError(f"Invalid quality '{v}'. Must be one of {valid}")
        return lower

    @model_validator(mode="after")
    def set_original_prompt_if_empty(self) -> "GenerationConfig":
        if not self.original_prompt:
            self.original_prompt = self.prompt
        return self
