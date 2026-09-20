import sys
import os
import json
import platform
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.vram_manager import vram_manager
from backend.app.models.registry import model_registry
from backend.app.core.config import settings

def run_diagnostics():
    print("======================================================================")
    print(f"      ANTIGRAVITY DIFFUSION STUDIO - SYSTEM DIAGNOSTICS REPORT        ")
    print("======================================================================")

    # 1. Operating System & Python
    print(f"[OS] Platform: {platform.platform()} ({platform.architecture()[0]})")
    print(f"[Python] Host Version: {sys.version.split()[0]}")
    print(f"[Python] Executable: {sys.executable}")

    # 2. PyTorch & CUDA
    gpu_info = vram_manager.get_gpu_info()
    print("\n--- Hardware & Acceleration ---")
    print(f"[PyTorch] Version: {gpu_info.get('torch_version')}")
    print(f"[CUDA] Available: {gpu_info.get('has_cuda')}")
    print(f"[CUDA] Version: {gpu_info.get('cuda_version')}")
    print(f"[NVIDIA Driver]: {gpu_info.get('driver_version')}")
    print(f"[Target GPU]: {gpu_info.get('gpu_name')}")
    print(f"[VRAM Total]: {gpu_info.get('vram_total_mb')} MB ({(gpu_info.get('vram_total_mb', 0)/1024):.1f} GB)")
    print(f"[VRAM Allocated]: {gpu_info.get('vram_allocated_mb')} MB")
    print(f"[VRAM Reserved]: {gpu_info.get('vram_reserved_mb')} MB")
    print(f"[VRAM Free]: {gpu_info.get('vram_free_mb')} MB")
    print(f"[Active Memory Strategy]: {vram_manager.current_strategy.value}")

    # 3. Model Adapters
    print("\n--- Modular Model Adapters ---")
    models = model_registry.list_models()
    for m in models:
        loaded_str = "[LOADED]" if m["is_loaded"] else "[READY]"
        print(f"  {loaded_str} {m['name']} ({m['architecture']}) - Est. VRAM: {m['estimated_vram_gb']} GB")

    # 4. Storage & LM Studio
    print("\n--- Configuration & Endpoints ---")
    print(f"[Output Directory]: {settings.paths.output_dir}")
    print(f"[Models Directory]: {settings.paths.model_dirs}")
    print(f"[LM Studio Base URL]: {settings.lm_studio.base_url} (Enabled: {settings.lm_studio.enabled})")

    # Output to logs/diagnostics.txt
    diag_path = PROJECT_ROOT / "logs" / "diagnostics.txt"
    diag_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "os": platform.platform(),
        "python": sys.version,
        "gpu": gpu_info,
        "models": [m["name"] for m in models],
        "settings": settings.model_dump()
    }
    with open(diag_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport written to: {diag_path}")
    print("======================================================================")

if __name__ == "__main__":
    run_diagnostics()
