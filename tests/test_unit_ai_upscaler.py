import os
import pytest
import torch
from pathlib import Path
from PIL import Image
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.core.config import PROJECT_ROOT
from backend.app.editing.ai_upscaler import RRDBNet, ai_upscaler
from backend.app.editing.face_restorer import face_restorer
from backend.app.editing.upscaler import upscaler_engine
from backend.app.gallery.metadata_manager import extract_metadata_from_png

os.environ["DEV_SIMULATION_MODE"] = "true"


def test_rrdbnet_architecture_shapes():
    """Verify RRDBNet architecture forward pass produces exact 4x spatial dimensions."""
    # 3 channels, 16x16 input
    dummy_input = torch.randn(1, 3, 16, 16)
    # Lightweight 2-block test net
    model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=16, num_block=2, num_grow_ch=8, scale=4)
    model.eval()
    with torch.no_grad():
        out = model(dummy_input)
    assert out.shape == (1, 3, 64, 64), f"Expected (1, 3, 64, 64), got {out.shape}"


def test_ai_upscaler_simulation_execution():
    """Verify AIUpscaler runs correctly in simulation mode."""
    img = Image.new("RGB", (32, 32), color=(200, 100, 50))
    upscaled_2x = ai_upscaler.upscale(img, scale=2, engine_name="realesrgan_photo")
    assert upscaled_2x.size == (64, 64)

    upscaled_4x = ai_upscaler.upscale(img, scale=4, engine_name="realesrgan_anime")
    assert upscaled_4x.size == (128, 128)


def test_face_restorer_fidelity_blending():
    """Verify FaceRestorer processes images across fidelity thresholds."""
    img = Image.new("RGB", (64, 64), color=(180, 140, 120))
    restored_high_fidelity = face_restorer.restore_faces(img, fidelity=0.9)
    assert restored_high_fidelity.size == (64, 64)

    restored_high_enhance = face_restorer.restore_faces(img, fidelity=0.1)
    assert restored_high_enhance.size == (64, 64)


def test_upscaler_engine_multi_stage_pipeline():
    """Verify full multi-stage coordinator with face restore and diffusion refine."""
    img = Image.new("RGB", (48, 48), color=(90, 120, 150))
    
    # Run full AI pipeline
    result = upscaler_engine.upscale(
        image=img,
        scale=2,
        engine="realesrgan_photo",
        enable_face_restore=True,
        face_fidelity=0.75,
        enable_diffusion_refine=True,
        diffusion_denoise=0.30
    )
    assert result.size == (96, 96)

    # Run classic Lanczos mode
    result_lanczos = upscaler_engine.upscale(
        image=img,
        scale=4,
        engine="classic_lanczos"
    )
    assert result_lanczos.size == (192, 192)


@pytest.mark.asyncio
async def test_upscale_api_endpoint_with_rich_parameters():
    """Test /api/upscale endpoint with the new AI Super-Resolution & Detailer parameters."""
    test_dir = PROJECT_ROOT / "outputs" / "test_ai_upscale"
    test_dir.mkdir(parents=True, exist_ok=True)
    source_path = test_dir / "orig_sample.png"

    img = Image.new("RGB", (32, 32), color=(120, 80, 220))
    img.save(source_path, format="PNG")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/upscale", json={
            "image_path": str(source_path),
            "scale": 2,
            "engine": "realesrgan_photo",
            "enable_face_restore": True,
            "face_fidelity": 0.65,
            "enable_diffusion_refine": True,
            "diffusion_denoise": 0.25
        })
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["scale"] == 2
        assert data["engine"] == "realesrgan_photo"
        assert data["face_restore"] is True
        assert data["diffusion_refine"] is True
        assert data["width"] == 64
        assert data["height"] == 64

        # Verify metadata was embedded into saved PNG
        out_file = Path(data["output_path"])
        assert out_file.exists()
        meta = extract_metadata_from_png(out_file)
        assert meta is not None
        assert "realesrgan_photo" in meta.get("upscaled", "")
        assert meta.get("upscale_engine") == "realesrgan_photo"
        assert meta.get("face_restore") is True


def test_decode_latents_to_preview_pil():
    """Verify sub-millisecond latent-to-RGB preview produces valid PIL image."""
    from backend.app.models.latent_preview import decode_latents_to_preview_pil
    dummy_sdxl_latents = torch.randn(1, 4, 32, 32)
    preview = decode_latents_to_preview_pil(dummy_sdxl_latents, target_size=128)
    assert preview is not None
    assert isinstance(preview, Image.Image)
    assert preview.size == (128, 128)


def test_adapter_step_callback_emits_every_step():
    """Verify that every single step invokes the callback with an image preview."""
    from backend.app.models.zimage.zimage_adapter import ZImageAdapter
    adapter = ZImageAdapter(model_id="zimage-turbo")

    steps_recorded = []
    previews_recorded = []

    def on_step(step, total, preview):
        steps_recorded.append((step, total))
        if preview is not None:
            previews_recorded.append(preview)

    target_steps = 4
    adapter.generate(
        prompt="A testing prompt",
        width=128,
        height=128,
        steps=target_steps,
        guidance=1.5,
        seed=42,
        callback=on_step
    )

    assert len(steps_recorded) == target_steps, f"Expected {target_steps} steps, got {len(steps_recorded)}"
    assert [s[0] for s in steps_recorded] == [1, 2, 3, 4]
    assert len(previews_recorded) == target_steps, f"Expected {target_steps} previews, got {len(previews_recorded)}"

