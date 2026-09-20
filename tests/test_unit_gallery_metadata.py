import pytest
from pathlib import Path
from PIL import Image

from backend.app.gallery.metadata_manager import create_png_info, extract_metadata_from_png
from backend.app.core.database import init_db, insert_generation, list_generations, toggle_favorite, delete_generation, get_generation_by_id

def test_png_metadata_full_roundtrip(tmp_path):
    img = Image.new("RGB", (128, 128), (50, 100, 150))
    metadata = {
        "id": "gen-12345",
        "created_at": "2026-09-20T12:00:00",
        "prompt": "futuristic neon skyline, 8k",
        "original_prompt": "neon skyline",
        "negative_prompt": "blurry, low quality",
        "model": "flux-klein-4b",
        "model_version": "FLUX.2 Klein 4B",
        "mode": "photo",
        "style": "cyberpunk",
        "aspect_ratio": "16:9",
        "quality": "maximum",
        "width": 1280,
        "height": 720,
        "steps": 28,
        "guidance": 3.5,
        "seed": 987654321,
        "sampler": "FlowMatch Euler",
        "scheduler": "FlowMatch",
        "vram_strategy": "FULL_GPU",
        "peak_vram_mb": 8450.5,
        "generation_time": 2.34,
        "oom_retries": 0,
        "loras": [{"path": "models/loras/neon.safetensors", "weight": 0.8}]
    }

    png_info = create_png_info(metadata)
    out_file = tmp_path / "test_full_meta.png"
    img.save(out_file, format="PNG", pnginfo=png_info)

    extracted = extract_metadata_from_png(out_file)
    assert extracted["id"] == "gen-12345"
    assert extracted["prompt"] == "futuristic neon skyline, 8k"
    assert extracted["seed"] == 987654321
    assert extracted["steps"] == 28
    assert extracted["peak_vram_mb"] == 8450.5
    assert extracted["sampler"] == "FlowMatch Euler"
    assert extracted["vram_strategy"] == "FULL_GPU"
    assert len(extracted["loras"]) == 1

@pytest.mark.asyncio
async def test_sqlite_gallery_lifecycle():
    await init_db()

    item_id = "test-gallery-item-777"
    record = {
        "id": item_id,
        "created_at": "2026-09-20T12:00:00",
        "prompt": "hyper-detailed obsidian crystalline tower in desert",
        "original_prompt": "obsidian tower in desert",
        "negative_prompt": "foggy, oversaturated",
        "model": "flux-klein-4b",
        "model_version": "FLUX.2 Klein 4B",
        "mode": "creative",
        "style": "cinematic",
        "aspect_ratio": "16:9",
        "quality": "balanced",
        "seed": 424242,
        "steps": 20,
        "guidance": 3.5,
        "sampler": "FlowMatch Euler",
        "scheduler": "FlowMatch",
        "width": 1024,
        "height": 1024,
        "generation_time": 3.12,
        "peak_vram_mb": 9120.0,
        "vram_strategy": "BALANCED",
        "oom_retries": 0,
        "image_path": "outputs/test.png",
        "thumbnail_path": "outputs/test_thumb.webp",
        "loras": [{"path": "models/loras/desert.safetensors", "weight": 0.7}]
    }

    # 1. Insert
    inserted = await insert_generation(record)
    assert inserted == item_id

    # 2. Get by ID
    item = await get_generation_by_id(item_id)
    assert item is not None
    assert item["id"] == item_id
    assert item["seed"] == 424242
    assert item["peak_vram_mb"] == 9120.0
    assert item["sampler"] == "FlowMatch Euler"
    assert item["style"] == "cinematic"
    assert isinstance(item["loras"], list)
    assert len(item["loras"]) == 1

    # 3. Search
    results, total = await list_generations(search_query="crystalline")
    assert total >= 1
    assert any(r["id"] == item_id for r in results)

    # 4. Toggle favorite
    fav = await toggle_favorite(item_id)
    assert fav is True
    updated = await get_generation_by_id(item_id)
    assert updated["is_favorite"] == 1

    # 5. Delete
    deleted = await delete_generation(item_id)
    assert deleted is True
    assert (await get_generation_by_id(item_id)) is None
