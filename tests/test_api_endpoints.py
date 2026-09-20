import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app

@pytest.mark.asyncio
async def test_api_system_and_models():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1:7860") as client:
        # Test system endpoint
        resp = await client.get("/api/system")
        assert resp.status_code == 200
        data = resp.json()
        assert "gpu" in data
        assert data["gpu"]["has_cuda"] is True

        # Test diagnostics endpoint
        diag_resp = await client.get("/api/system/diagnostics")
        assert diag_resp.status_code == 200
        diag = diag_resp.json()
        assert diag["environment"]["cuda_available"] is True

        # Test models endpoint
        models_resp = await client.get("/api/models")
        assert models_resp.status_code == 200
        models_data = models_resp.json()
        assert len(models_data["models"]) == 5

        # Test styles endpoint
        styles_resp = await client.get("/api/styles")
        assert styles_resp.status_code == 200
        assert len(styles_resp.json()["styles"]) >= 10

        # Test loras endpoint
        loras_resp = await client.get("/api/loras")
        assert loras_resp.status_code == 200

        # Test analyze prompt endpoint
        analyze_resp = await client.post("/api/analyze-prompt", json={
            "prompt": "A cinematic photograph of an abandoned 1980s arcade at night, wet floor, neon signs saying ARCADE 84."
        })
        assert analyze_resp.status_code == 200
        decision = analyze_resp.json()
        assert decision["model"] in ["qwen-image", "zimage-turbo", "flux-klein-4b"]
        assert decision["text_rendering"] is True # because of "saying ARCADE 84"

        # Test job submission
        gen_resp = await client.post("/api/generate", json={
            "prompt": "studio portrait of a person with dramatic soft lighting",
            "model": "auto",
            "mode": "photo",
            "steps": 4,
            "width": 512,
            "height": 512
        })
        assert gen_resp.status_code == 200
        job_info = gen_resp.json()
        assert "job_id" in job_info

        # Verify job list
        jobs_resp = await client.get("/api/jobs")
        assert jobs_resp.status_code == 200
        jobs = jobs_resp.json()
        assert any(j["id"] == job_info["job_id"] for j in jobs)
