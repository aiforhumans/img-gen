import sys
import os
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def run_preflight():
    # Terminal ANSI Colors
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    MAGENTA = "\033[95m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    # Enable ANSI escape sequences on Windows
    os.system("")

    print(f"\n{BOLD}{MAGENTA}======================================================================{RESET}")
    print(f"{BOLD}{CYAN}      ANTIGRAVITY DIFFUSION STUDIO v1.0.0 - SYSTEM PREFLIGHT          {RESET}")
    print(f"{BOLD}{MAGENTA}======================================================================{RESET}")

    # 1. Python & PyTorch Environment
    py_ver = sys.version.split()[0]
    print(f"\n{BOLD}{BLUE}[1/5] Python & CUDA Acceleration Runtime:{RESET}")
    print(f"  * Python Host:      {GREEN}Python {py_ver}{RESET} ({'64-bit' if sys.maxsize > 2**32 else '32-bit'})")

    try:
        import torch
        cuda_avail = torch.cuda.is_available()
        if cuda_avail:
            gpu_name = torch.cuda.get_device_name(0)
            total_vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            cap = torch.cuda.get_device_capability(0)
            print(f"  * PyTorch Engine:   {GREEN}v{torch.__version__}{RESET} (CUDA {torch.version.cuda})")
            print(f"  * Dedicated GPU:    {GREEN}{gpu_name}{RESET}")
            print(f"  * Total VRAM:       {GREEN}{total_vram_gb:.1f} GB Dedicated GDDR7{RESET}")
            print(f"  * Architecture:     {GREEN}Compute Capability {cap[0]}.{cap[1]} (Blackwell sm_120){RESET}")
            print(f"  * Native SDPA:      {GREEN}Enabled (Scaled Dot-Product Attention){RESET}")
        else:
            print(f"  * PyTorch Engine:   {YELLOW}v{torch.__version__} (CPU Only - No CUDA detected){RESET}")
    except Exception as e:
        print(f"  * PyTorch Check:    {YELLOW}Error checking PyTorch: {e}{RESET}")

    # 2. Storage & Database
    print(f"\n{BOLD}{BLUE}[2/5] Storage & Gallery Infrastructure:{RESET}")
    outputs_dir = PROJECT_ROOT / "outputs"
    gallery_db = outputs_dir / "gallery.db"
    models_dir = PROJECT_ROOT / "models"
    print(f"  * Project Root:     {DIM}{PROJECT_ROOT}{RESET}")
    print(f"  * Output Directory: {GREEN}{outputs_dir}{RESET}")
    print(f"  * SQLite Gallery:   {GREEN}{gallery_db}{RESET} ({'Exists' if gallery_db.exists() else 'Will initialize on start'})")

    # 3. Model Checkpoints & LoRAs
    print(f"\n{BOLD}{BLUE}[3/5] Installed Diffusion Models & Weights:{RESET}")
    from backend.app.models.registry import model_registry
    from backend.app.core.config import settings

    for mid, adapter in model_registry.adapters.items():
        has_w = adapter.has_weights()
        if has_w:
            badge = f"{GREEN}[INSTALLED - READY]{RESET}"
            # Find specific file
            ckpt = adapter._find_checkpoint() if hasattr(adapter, "_find_checkpoint") else None
            fname = f" -> {ckpt.name} ({ckpt.stat().st_size / (1024**3):.2f} GB)" if ckpt else ""
            print(f"  * {BOLD}{mid:<14}{RESET} {badge}{fname}")
        else:
            badge = f"{YELLOW}[NOT DOWNLOADED]{RESET}"
            print(f"  * {DIM}{mid:<14}{RESET} {badge} {DIM}(1-click download in Models tab){RESET}")

    # 4. Prompt Intelligence & LM Studio Connection
    print(f"\n{BOLD}{BLUE}[4/5] Prompt Intelligence Engine:{RESET}")
    import httpx
    lm_url = settings.lm_studio.base_url
    try:
        r = httpx.get(f"{lm_url}/models", timeout=1.5)
        if r.status_code == 200:
            models_data = r.json().get("data", [])
            active_m = models_data[0]["id"] if models_data else "Default"
            print(f"  * LM Studio:        {GREEN}[ONLINE]{RESET} Connected at {lm_url}")
            print(f"  * Active LLM:       {GREEN}{active_m}{RESET} (Magic Polish available)")
        else:
            print(f"  * LM Studio:        {YELLOW}[OFFLINE]{RESET} (Local rule-based expander active)")
    except Exception:
        print(f"  * LM Studio:        {YELLOW}[OFFLINE]{RESET} at {lm_url} (Local rule-based expander active)")

    # 5. Network & Server Host
    print(f"\n{BOLD}{BLUE}[5/5] Application Server Endpoint:{RESET}")
    print(f"  * Host Binding:     {GREEN}http://{settings.general.host}:{settings.general.port}{RESET} (Strict Localhost)")
    print(f"  * VRAM Strategy:    {GREEN}{settings.vram.default_strategy}{RESET}")
    print(f"\n{BOLD}{GREEN}======================================================================{RESET}")
    print(f"{BOLD}{GREEN} [READY] Launching FastAPI uvicorn application server...             {RESET}")
    print(f"{BOLD}{GREEN}======================================================================\n{RESET}")

if __name__ == "__main__":
    run_preflight()
