import pytest
import asyncio
from pathlib import Path
from PIL import Image

from backend.app.routing.auto_router import auto_router
from backend.app.core.vram_manager import vram_manager, VRAMStrategy
from backend.app.models.registry import model_registry
from backend.app.core.database import init_db, insert_generation, list_generations
from backend.app.gallery.metadata_manager import create_png_info, extract_metadata_from_png
from backend.app.prompt_engine.local_analyzer import local_analyzer

def test_auto_router_decisions():
    # 1. Portrait photograph -> Z-Image Turbo
    d1 = auto_router.analyze("professional portrait photograph of a woman in a studio")
    assert d1.model == "zimage-turbo", f"Expected zimage-turbo, got {d1.model}"
    assert d1.category == "photorealism"

    # 2. Typography / poster with quotes or saying -> Qwen Image
    d2 = auto_router.analyze("poster saying GRAND OPENING with futuristic typography")
    assert d2.model == "qwen-image", f"Expected qwen-image, got {d2.model}"
    assert d2.text_rendering is True

    # 3. Epic creative concept / fantasy -> FLUX.2 Klein
    d3 = auto_router.analyze("fantasy landscape with massive floating cities")
    assert "flux-klein" in d3.model, f"Expected flux-klein, got {d3.model}"

    # 4. Instruction editing -> Editing engine
    d4 = auto_router.analyze("change her jacket to red")
    assert d4.editing is True

    # 5. SDXL LoRA -> SDXL
    d5 = auto_router.analyze("use SDXL LoRA cyberpunk_v2")
    assert d5.model == "sdxl", f"Expected sdxl, got {d5.model}"

@pytest.mark.gpu
def test_vram_manager_hardware():
    gpu_info = vram_manager.get_gpu_info()
    if not gpu_info.get("has_cuda"):
        pytest.skip("Physical CUDA GPU not available")
    assert gpu_info["has_cuda"] is True
    assert gpu_info["vram_total_mb"] > 0

def test_vram_strategy_escalation():
    vram_manager.current_strategy = VRAMStrategy.FULL_GPU
    next_s = vram_manager.step_down_strategy()
    assert next_s == VRAMStrategy.BALANCED
    next_s2 = vram_manager.step_down_strategy()
    assert next_s2 == VRAMStrategy.LOW_VRAM

def test_model_registry_and_adapters(monkeypatch):
    monkeypatch.setenv("DEV_SIMULATION_MODE", "true")
    models = model_registry.list_models()
    assert len(models) == 5 # 4B, 9B, zimage, qwen, sdxl
    adapter = model_registry.load_model("zimage-turbo")
    assert adapter.is_loaded is True
    # Test fast generation
    img = adapter.generate("test portrait", steps=2, width=256, height=256)
    assert img.size == (256, 256)

def test_png_metadata_roundtrip(tmp_path):
    img = Image.new("RGB", (100, 100), (255, 0, 0))
    meta = {
        "id": "test-id-123",
        "prompt": "neon arcade 1984",
        "negative_prompt": "blurry",
        "seed": 42,
        "steps": 20,
        "guidance": 3.5,
        "model": "flux-klein-4b",
        "width": 100,
        "height": 100
    }
    pnginfo = create_png_info(meta)
    out_file = tmp_path / "test.png"
    img.save(out_file, format="PNG", pnginfo=pnginfo)

    recovered = extract_metadata_from_png(out_file)
    assert recovered["id"] == "test-id-123"
    assert recovered["prompt"] == "neon arcade 1984"
    assert recovered["seed"] == 42

@pytest.mark.asyncio
async def test_sqlite_gallery():
    await init_db()
    record = {
        "id": "test-gen-999",
        "created_at": "2026-09-20T00:00:00",
        "prompt": "futuristic flying car",
        "model": "flux-klein-4b",
        "seed": 12345,
        "steps": 20,
        "guidance": 3.5,
        "width": 1024,
        "height": 1024,
        "image_path": "outputs/test.png"
    }
    inserted_id = await insert_generation(record)
    assert inserted_id == "test-gen-999"

    items, total = await list_generations(search_query="flying car")
    assert total >= 1
    assert any(item["id"] == "test-gen-999" for item in items)
