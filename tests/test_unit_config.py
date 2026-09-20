import pytest
from pydantic import ValidationError

from backend.app.core.generation_config import GenerationConfig, LoRAConfig
from backend.app.prompt_engine.style_composer import style_composer
from backend.app.models.scheduler_factory import SchedulerFactory
from backend.app.lora.lora_scanner import lora_scanner
from backend.app.core.vram_manager import vram_manager, VRAMStrategy
from backend.app.routing.auto_router import auto_router

def test_generation_config_valid():
    cfg = GenerationConfig(
        prompt="neon arcade at night",
        negative_prompt="blurry",
        model="sdxl",
        mode="photo",
        style="cinematic",
        aspect_ratio="16:9",
        width=1280,
        height=720,
        quality="maximum",
        steps=30,
        guidance=7.5,
        seed=42,
        sampler="Euler",
        vram_strategy="BALANCED",
        loras=[LoRAConfig(path="models/loras/retro.safetensors", weight=0.8)]
    )
    assert cfg.prompt == "neon arcade at night"
    assert cfg.original_prompt == "neon arcade at night"
    assert cfg.width == 1280
    assert cfg.height == 720
    assert cfg.steps == 30
    assert cfg.guidance == 7.5
    assert cfg.seed == 42
    assert len(cfg.loras) == 1
    assert cfg.loras[0].weight == 0.8

def test_generation_config_reference_image_fields():
    """Validates IP-Adapter reference image configuration fields."""
    # Valid reference config
    cfg = GenerationConfig(
        prompt="portrait photo",
        reference_image_path="/cache/references/abc123.png",
        reference_mode="style",
        reference_strength=0.8
    )
    assert cfg.reference_image_path == "/cache/references/abc123.png"
    assert cfg.reference_mode == "style"
    assert cfg.reference_strength == 0.8

    # Dual reference
    cfg2 = GenerationConfig(
        prompt="portrait photo",
        reference_image_path="/cache/ref1.png",
        reference_mode="style",
        reference_strength=0.6,
        reference_image_path_2="/cache/ref2.png",
        reference_mode_2="subject",
        reference_strength_2=0.4
    )
    assert cfg2.reference_mode_2 == "subject"
    assert cfg2.reference_strength_2 == 0.4

    # Defaults when no reference
    cfg3 = GenerationConfig(prompt="simple test")
    assert cfg3.reference_image_path is None
    assert cfg3.reference_mode is None
    assert cfg3.reference_strength == 0.6

    # Strength out of range
    with pytest.raises(ValidationError):
        GenerationConfig(prompt="test", reference_strength=2.0)
    with pytest.raises(ValidationError):
        GenerationConfig(prompt="test", reference_strength=-0.5)

def test_generation_config_dimension_quantization():
    # Width and height not multiples of 8 should be snapped
    cfg = GenerationConfig(prompt="test", width=1023, height=769)
    assert cfg.width % 8 == 0
    assert cfg.height % 8 == 0

def test_generation_config_validation_failures():
    # Empty prompt
    with pytest.raises(ValidationError):
        GenerationConfig(prompt="   ")

    # Steps out of range
    with pytest.raises(ValidationError):
        GenerationConfig(prompt="valid", steps=0)

    with pytest.raises(ValidationError):
        GenerationConfig(prompt="valid", steps=500)

    # Invalid VRAM strategy
    with pytest.raises(ValidationError):
        GenerationConfig(prompt="valid", vram_strategy="ULTRA_FAST")

    # Invalid Mode
    with pytest.raises(ValidationError):
        GenerationConfig(prompt="valid", mode="invalid_mode")

    # Invalid Quality
    with pytest.raises(ValidationError):
        GenerationConfig(prompt="valid", quality="super_quality")

    # Invalid LoRA strength
    with pytest.raises(ValidationError):
        LoRAConfig(path="lora.safetensors", weight=10.0)

def test_style_composition():
    comp = style_composer.compose(
        prompt="a girl standing in the rain",
        style_id="cinematic",
        user_negative_prompt="cartoon"
    )
    assert comp.original_prompt == "a girl standing in the rain"
    assert "cinematic film still" in comp.style_prompt
    assert "a girl standing in the rain" in comp.style_prompt
    assert "cartoon" in comp.negative_prompt
    assert "cheap video" in comp.negative_prompt

    # Unknown or none style preserves prompt without alteration
    none_comp = style_composer.compose(
        prompt="simple prompt",
        style_id="none",
        user_negative_prompt="bad quality"
    )
    assert none_comp.style_prompt == "simple prompt"
    assert none_comp.negative_prompt == "bad quality"

def test_scheduler_factory_architecture_compatibility():
    # SDXL supports Euler, Euler Ancestral, DPM++ 2M Karras, DDIM
    assert SchedulerFactory.is_compatible("sdxl", "Euler") is True
    assert SchedulerFactory.is_compatible("sdxl", "Euler Ancestral") is True
    assert SchedulerFactory.is_compatible("sdxl", "DPM++ 2M Karras") is True
    assert SchedulerFactory.is_compatible("sdxl", "DDIM") is True
    # SDXL rejects FlowMatch Euler
    assert SchedulerFactory.is_compatible("sdxl", "FlowMatch Euler") is False
    with pytest.raises(ValueError):
        SchedulerFactory.validate_sampler("sdxl", "FlowMatch Euler")

    # FLUX supports FlowMatch Euler
    assert SchedulerFactory.is_compatible("flux", "FlowMatch Euler") is True
    # FLUX rejects DPM++ 2M Karras
    assert SchedulerFactory.is_compatible("flux", "DPM++ 2M Karras") is False
    with pytest.raises(ValueError):
        SchedulerFactory.validate_sampler("flux", "DPM++ 2M Karras")

    # Z-Image supports Euler and Default
    assert SchedulerFactory.is_compatible("zimage", "Euler") is True
    assert SchedulerFactory.is_compatible("zimage", "Default (Recommended)") is True
    assert SchedulerFactory.is_compatible("zimage", "DDIM") is True
    assert SchedulerFactory.is_compatible("zimage", "DPM++ 2M Karras") is True
    # Z-Image rejects FlowMatch Euler
    assert SchedulerFactory.is_compatible("zimage", "FlowMatch Euler") is False

def test_zimage_step_aware_sampler_filtering():
    """Verifies step-aware sampler filtering for Lightning-distilled Z-Image Turbo."""
    # 2-step: Only Default + Euler
    samplers_2 = SchedulerFactory.get_step_aware_samplers("zimage", 2)
    assert "Euler" in samplers_2
    assert "Default (Recommended)" in samplers_2
    assert "DPM++ 2M Karras" not in samplers_2
    assert "Euler Ancestral" not in samplers_2
    assert "DDIM" not in samplers_2

    # 4-step: Default + Euler + DPM++ 2M Karras
    samplers_4 = SchedulerFactory.get_step_aware_samplers("zimage", 4)
    assert "Euler" in samplers_4
    assert "DPM++ 2M Karras" in samplers_4
    assert "Euler Ancestral" not in samplers_4
    assert "DDIM" not in samplers_4

    # 8-step: Full menu
    samplers_8 = SchedulerFactory.get_step_aware_samplers("zimage", 8)
    assert "Euler" in samplers_8
    assert "DPM++ 2M Karras" in samplers_8
    assert "Euler Ancestral" in samplers_8
    assert "DDIM" in samplers_8

    # Non-zimage architectures are unaffected by step count
    samplers_sdxl = SchedulerFactory.get_step_aware_samplers("sdxl", 2)
    assert samplers_sdxl == SchedulerFactory.get_supported_samplers("sdxl")

def test_zimage_step_sampler_fallback():
    """Verifies incompatible step/sampler combos fall back to Euler Trailing."""
    # DPM++ at 2-step should be rejected and fall back to Euler
    is_valid, fallback = SchedulerFactory.validate_step_sampler("zimage", "DPM++ 2M Karras", 2)
    assert is_valid is False
    assert fallback == "Euler"

    # Euler at 2-step should pass through
    is_valid, sampler = SchedulerFactory.validate_step_sampler("zimage", "Euler", 2)
    assert is_valid is True
    assert sampler == "Euler"

    # DDIM at 4-step should be rejected
    is_valid, fallback = SchedulerFactory.validate_step_sampler("zimage", "DDIM", 4)
    assert is_valid is False
    assert fallback == "Euler"

    # DDIM at 8-step should pass through
    is_valid, sampler = SchedulerFactory.validate_step_sampler("zimage", "DDIM", 8)
    assert is_valid is True
    assert sampler == "DDIM"

    # Default always passes through
    is_valid, sampler = SchedulerFactory.validate_step_sampler("zimage", "Default (Recommended)", 2)
    assert is_valid is True

def test_lora_scanner_compatibility():
    # SDXL LoRA on SDXL backend -> valid
    lora_scanner.validate_compatibility("sdxl", {"path": "models/loras/vintage_anime_sdxl.safetensors"})

    # SDXL LoRA on FLUX backend -> invalid, must raise ValueError
    with pytest.raises(ValueError) as exc:
        lora_scanner.validate_compatibility("flux", {"path": "models/loras/vintage_anime_sdxl.safetensors"})
    assert "incompatible" in str(exc.value).lower()

    # FLUX LoRA on FLUX backend -> valid
    lora_scanner.validate_compatibility("flux", {"path": "models/loras/cyberpunk_neon_v2.safetensors"})

    # Qwen does not support LoRA
    with pytest.raises(ValueError):
        lora_scanner.validate_compatibility("qwen", {"path": "models/loras/vintage_anime_sdxl.safetensors"})

def test_vram_strategy_progression():
    vram_manager.current_strategy = VRAMStrategy.FULL_GPU
    assert vram_manager.step_down_strategy() == VRAMStrategy.BALANCED
    assert vram_manager.step_down_strategy() == VRAMStrategy.LOW_VRAM
    assert vram_manager.step_down_strategy() == VRAMStrategy.CPU_OFFLOAD
    assert vram_manager.step_down_strategy() is None

    # Step down from explicit strategy
    assert vram_manager.step_down_strategy_from("FULL_GPU") == VRAMStrategy.BALANCED
    assert vram_manager.step_down_strategy_from("BALANCED") == VRAMStrategy.LOW_VRAM
    assert vram_manager.step_down_strategy_from("LOW_VRAM") == VRAMStrategy.CPU_OFFLOAD
    assert vram_manager.step_down_strategy_from("CPU_OFFLOAD") is None

def test_auto_router_categories():
    d1 = auto_router.analyze("portrait photo of a scientist in high resolution")
    assert d1.model == "zimage-turbo"
    assert d1.category == "photorealism"

    d2 = auto_router.analyze("poster with typography reading 'SUMMER VIBES'")
    assert d2.model == "qwen-image"
    assert d2.text_rendering is True

    d3 = auto_router.analyze("surreal fantasy world with flying whales and nebula")
    assert "flux" in d3.model
