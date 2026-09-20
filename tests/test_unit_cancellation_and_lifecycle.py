import os
import pytest
import asyncio
from unittest.mock import MagicMock, patch

from backend.app.core.job_queue import JobQueue, GenerationJob, JobState
from backend.app.core.exceptions import GenerationCancelled, ModelLoadError, OOMRetryExhausted
from backend.app.models.registry import ModelRegistry
from backend.app.models.base_adapter import BaseImageModelAdapter
from backend.app.core.vram_manager import vram_manager, VRAMStrategy

class DummyAdapter(BaseImageModelAdapter):
    def __init__(self, model_id="dummy", fail_load=False):
        super().__init__(model_id=model_id, name="Dummy Adapter", architecture="sdxl")
        self.fail_load = fail_load

    def load(self, device="cuda", vram_strategy="BALANCED", precision="fp16"):
        if self.fail_load:
            self.is_loaded = False
            return False
        self.is_loaded = True
        return True

    def unload(self):
        self.is_loaded = False
        return True

    def generate(self, *args, **kwargs):
        from PIL import Image
        return Image.new("RGB", (64, 64), (100, 100, 100))

    def img2img(self, *args, **kwargs):
        from PIL import Image
        return Image.new("RGB", (64, 64), (100, 100, 100))

    def edit(self, *args, **kwargs):
        from PIL import Image
        return Image.new("RGB", (64, 64), (100, 100, 100))

    def inpaint(self, *args, **kwargs):
        from PIL import Image
        return Image.new("RGB", (64, 64), (100, 100, 100))

    def outpaint(self, *args, **kwargs):
        from PIL import Image
        return Image.new("RGB", (64, 64), (100, 100, 100))

    def supports_lora(self):
        return True

    def load_lora(self, lora_path, weight=1.0):
        self.loaded_loras.append({"path": lora_path, "weight": weight})
        return True

    def unload_lora(self, lora_path):
        self.loaded_loras = [l for l in self.loaded_loras if l["path"] != lora_path]
        return True

    def estimate_vram(self, width=1024, height=1024, batch_size=1):
        return 4.0

    def supported_resolutions(self):
        return [{"label": "Square (1:1)", "width": 512, "height": 512, "aspect_ratio": "1:1"}]

    def recommended_settings(self):
        return {"steps": 10, "guidance": 5.0, "sampler": "Euler", "scheduler": "Normal"}

@pytest.mark.asyncio
async def test_job_cancellation_stays_cancelled():
    jq = JobQueue()
    job = GenerationJob(
        prompt="test prompt for cancellation",
        model="dummy",
        seed=1234
    )
    jid = jq.submit_job(job)

    # Cancel immediately
    cancelled = jq.cancel_job(jid)
    assert cancelled is True
    assert job.state == JobState.CANCELLED
    assert "cancelled" in job.error_message.lower()

    # Process queue with cancelled job
    # Job should remain CANCELLED, never FAILED
    await jq.queue.join() if jq.queue.empty() else None
    assert job.state == JobState.CANCELLED

@pytest.mark.asyncio
async def test_seed_resolution_before_inference():
    jq = JobQueue()
    job = GenerationJob(
        prompt="test prompt for seed resolution",
        seed=-1
    )
    assert job.seed == -1

    # Mock _execute_job internal resolution
    with patch("backend.app.models.registry.model_registry.get_adapter") as mock_get_adapter:
        dummy = DummyAdapter()
        mock_get_adapter.return_value = dummy
        with patch("backend.app.models.registry.model_registry.load_model") as mock_load:
            mock_load.return_value = dummy

            # Execute job partially
            await jq._execute_job(job)

            # Resolved seed must be a valid integer between 0 and 2**32
            assert job.seed >= 0
            assert isinstance(job.seed, int)
            assert job.seed != -1

def test_model_load_failure_never_marks_active():
    reg = ModelRegistry()
    failing_adapter = DummyAdapter(model_id="fail-model", fail_load=True)
    reg.adapters["fail-model"] = failing_adapter

    # In production mode (DEV_SIMULATION_MODE=false)
    os.environ["DEV_SIMULATION_MODE"] = "false"
    with pytest.raises(ModelLoadError):
        reg.load_model("fail-model")

    # The failing model must NOT be marked as active!
    assert reg.active_model_id != "fail-model"
    assert "fail-model" not in vram_manager.loaded_models
    assert failing_adapter.is_loaded is False

def test_lora_clean_unload_lifecycle():
    adapter = DummyAdapter(model_id="lora-test")
    adapter.load_lora("models/loras/test_lora_1.safetensors", weight=0.8)
    adapter.load_lora("models/loras/test_lora_2.safetensors", weight=0.5)
    assert len(adapter.loaded_loras) == 2

    # Unload all
    adapter.unload_all_loras()
    assert len(adapter.loaded_loras) == 0

def test_real_adapters_fail_without_weights_in_production():
    from backend.app.models.sdxl.sdxl_adapter import SDXLAdapter
    from backend.app.models.flux.flux_adapter import FluxAdapter

    os.environ["DEV_SIMULATION_MODE"] = "false"
    sdxl = SDXLAdapter(model_id="nonexistent-sdxl")
    flux = FluxAdapter(model_id="nonexistent-flux")

    # If no weights exist on disk, load must fail with ModelLoadError and never report success
    with pytest.raises(ModelLoadError):
        sdxl.load()
    assert sdxl.is_loaded is False

    with pytest.raises(ModelLoadError):
        flux.load()
    assert flux.is_loaded is False
