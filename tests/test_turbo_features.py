import pytest
import asyncio
from pathlib import Path
from PIL import Image
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.models.zimage.zimage_adapter import ZImageAdapter
from backend.app.editing.upscaler import upscaler_engine
from backend.app.core.config import PROJECT_ROOT

@pytest.mark.asyncio
async def test_magic_polish_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/prompt/polish", json={"prompt": "cyberpunk street at night"})
        assert res.status_code == 200
        data = res.json()
        assert data["original"] == "cyberpunk street at night"
        assert len(data["polished"]) > len("cyberpunk street at night")
        assert "diff_summary" in data

@pytest.mark.asyncio
async def test_upscale_endpoint():
    # Create a small dummy test image in outputs
    test_dir = PROJECT_ROOT / "outputs" / "test_run"
    test_dir.mkdir(parents=True, exist_ok=True)
    img_path = test_dir / "test_orig.png"
    
    img = Image.new("RGB", (64, 64), color=(100, 150, 200))
    img.save(img_path, format="PNG")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/upscale", json={
            "image_path": str(img_path),
            "scale": 2
        })
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["width"] == 128
        assert data["height"] == 128
        assert data["scale"] == 2
        assert Path(data["output_path"]).exists()

        # Test upscaling via gallery URL with simulated database record
        from backend.app.core.database import insert_generation
        gen_id = "test_upscale_job_123"
        await insert_generation({
            "id": gen_id,
            "prompt": "Test prompt for upscale",
            "model": "zimage-turbo",
            "image_path": str(img_path),
            "width": 64,
            "height": 64
        })

        res_url = await client.post("/api/upscale", json={
            "image_url": f"/api/gallery/image/{gen_id}",
            "scale": 4
        })
        assert res_url.status_code == 200
        data_url = res_url.json()
        assert data_url["success"] is True
        assert data_url["width"] == 256
        assert data_url["height"] == 256
        assert data_url["scale"] == 4
        assert Path(data_url["output_path"]).exists()

        # Test upscaling via full http host URL
        res_host = await client.post("/api/upscale", json={
            "image_url": f"http://127.0.0.1:7860/api/gallery/image/{gen_id}",
            "scale": 2
        })
        assert res_host.status_code == 200
        assert res_host.json()["success"] is True

def test_zimage_adapter_lightning():
    adapter = ZImageAdapter()
    assert adapter.architecture == "zimage"
    assert adapter.recommended_settings()["steps"] == 8
    assert adapter.recommended_settings()["guidance"] == 1.5

    # Test standalone upscaler engine
    sample = Image.new("RGB", (50, 50), color=(50, 100, 150))
    up2 = upscaler_engine.upscale(sample, scale=2)
    assert up2.size == (100, 100)
    up4 = upscaler_engine.upscale(sample, scale=4)
    assert up4.size == (200, 200)
