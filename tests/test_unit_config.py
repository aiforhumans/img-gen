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
    assert SchedulerFactory.is_compatible("zimage", "DDIM") is False

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
