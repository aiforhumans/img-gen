import os
import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional
from huggingface_hub import snapshot_download
from backend.app.core.config import settings, PROJECT_ROOT
from backend.app.core.logger import app_logger

def get_hf_token() -> Optional[str]:
    """Retrieves Hugging Face token from environment, config file, or user cache."""
    # 1. Environment variable
    env_token = os.environ.get("HF_TOKEN")
    if env_token and env_token.strip():
        return env_token.strip()

    # 2. Local project configuration
    config_token_path = PROJECT_ROOT / "config" / "hf_token.txt"
    if config_token_path.exists():
        try:
            t = config_token_path.read_text(encoding="utf-8").strip()
            if t:
                return t
        except Exception:
            pass

    # 3. Standard Hugging Face cache token (~/.cache/huggingface/token)
    cache_token_path = Path.home() / ".cache" / "huggingface" / "token"
    if cache_token_path.exists():
        try:
            t = cache_token_path.read_text(encoding="utf-8").strip()
            if t:
                return t
        except Exception:
            pass

    return None

def set_hf_token(token: str):
    """Saves Hugging Face token to local configuration for authenticated model downloads."""
    config_dir = PROJECT_ROOT / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "hf_token.txt").write_text(token.strip(), encoding="utf-8")
    os.environ["HF_TOKEN"] = token.strip()

# Model repositories mapping
MODEL_REPOSITORIES: Dict[str, Dict[str, Any]] = {
    "juggernaut-xl": {
        "repo_id": "RunDiffusion/Juggernaut-XL-Lightning",
        "description": "Juggernaut-XL Photorealism Foundation Engine (~6.5 GB)",
        "estimated_size_gb": 6.5,
        "allow_patterns": ["*.safetensors", "*.json", "*.txt"]
    },
    "sdxl": {
        "repo_id": "stabilityai/sdxl-turbo",
        "description": "SDXL Turbo (1-step to 4-step real-time synthesis, 6.5 GB)",
        "estimated_size_gb": 6.5,
        "allow_patterns": ["*.safetensors", "*.json", "*.txt"]
    },
    "zimage-turbo": {
        "repo_id": "ByteDance/SDXL-Lightning",
        "description": "ByteDance SDXL-Lightning 2/4/8-Step LoRA/UNet Suite (~1.5 GB)",
        "estimated_size_gb": 1.5,
        "allow_patterns": ["*step*.safetensors", "*.json"]
    },
    "qwen-image": {
        "repo_id": "Qwen/Qwen-Image",
        "description": "Qwen Image Typography & Instruction Engine (~9.8 GB)",
        "estimated_size_gb": 9.8,
        "allow_patterns": ["*.safetensors", "*.json"]
    },
    "flux-klein-4b": {
        "repo_id": "black-forest-labs/FLUX.1-schnell",
        "ungated_repo_id": "Comfy-Org/flux1-schnell",
        "description": "FLUX.1 Schnell Fast Diffusion Engine (~11.9 GB)",
        "estimated_size_gb": 11.9,
        "allow_patterns": ["*.safetensors", "*.json", "*.txt"]
    },
    "flux-klein-9b": {
        "repo_id": "black-forest-labs/FLUX.1-dev",
        "ungated_repo_id": "Comfy-Org/flux1-dev",
        "description": "FLUX.1 Dev High-Fidelity Diffusion Engine (~16.0 GB)",
        "estimated_size_gb": 16.0,
        "allow_patterns": ["*.safetensors", "*.json", "*.txt"]
    }
}

class ModelDownloader:
    """
    Manages asynchronous background downloading of official model checkpoints
    from Hugging Face directly into the configured local models directory.
    """
    def __init__(self):
        self.active_downloads: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def get_status(self, model_id: str) -> Dict[str, Any]:
        with self._lock:
            if model_id in self.active_downloads:
                return self.active_downloads[model_id]

        # Check if model already exists on disk
        target_dir = Path(settings.paths.model_dirs[0]) / model_id
        if target_dir.exists() and any(target_dir.glob("**/*.safetensors")):
            total_size_mb = sum(f.stat().st_size for f in target_dir.glob("**/*") if f.is_file()) / (1024 * 1024)
            return {
                "status": "complete",
                "progress": 100.0,
                "downloaded_mb": round(total_size_mb, 1),
                "total_mb": round(total_size_mb, 1),
                "speed_mbps": 0.0,
                "error": None
            }

        return {
            "status": "not_downloaded",
            "progress": 0.0,
            "downloaded_mb": 0.0,
            "total_mb": MODEL_REPOSITORIES.get(model_id, {}).get("estimated_size_gb", 0) * 1024,
            "speed_mbps": 0.0,
            "error": None
        }

    def start_download(self, model_id: str, custom_repo_id: Optional[str] = None) -> bool:
        repo_info = MODEL_REPOSITORIES.get(model_id)
        if not repo_info and not custom_repo_id:
            raise ValueError(f"Unknown model architecture: '{model_id}'")

        repo_id = custom_repo_id or repo_info["repo_id"]
        target_dir = Path(settings.paths.model_dirs[0]) / model_id
        target_dir.mkdir(parents=True, exist_ok=True)

        with self._lock:
            if model_id in self.active_downloads and self.active_downloads[model_id]["status"] == "downloading":
                return False # Already in progress

            self.active_downloads[model_id] = {
                "status": "downloading",
                "progress": 1.0,
                "downloaded_mb": 0.0,
                "total_mb": repo_info.get("estimated_size_gb", 10.0) * 1024 if repo_info else 10240,
                "speed_mbps": 0.0,
                "error": None,
                "repo_id": repo_id
            }

        thread = threading.Thread(
            target=self._download_worker,
            args=(model_id, repo_id, target_dir, repo_info.get("allow_patterns")),
            daemon=True
        )
        thread.start()
        app_logger.info(f"[Downloader] Started background download for '{model_id}' ({repo_id})")
        return True

    def _download_worker(self, model_id: str, repo_id: str, target_dir: Path, allow_patterns: Optional[list]):
        t_start = time.time()
        token = get_hf_token()
        repo_info = MODEL_REPOSITORIES.get(model_id, {})
        ungated_repo = repo_info.get("ungated_repo_id")

        try:
            app_logger.info(f"[Downloader] Fetching {repo_id} to {target_dir} (authenticated={token is not None})...")
            snapshot_download(
                repo_id=repo_id,
                local_dir=str(target_dir),
                token=token,
                allow_patterns=allow_patterns
            )
        except Exception as e:
            err_str = str(e).lower()
            is_gated = "401" in err_str or "gated" in err_str or "restricted" in err_str or "unauthorized" in err_str

            if is_gated and ungated_repo and repo_id != ungated_repo:
                app_logger.warning(
                    f"[Downloader] Access restricted for gated repo '{repo_id}'. "
                    f"Automatically switching to public un-gated mirror '{ungated_repo}'..."
                )
                try:
                    snapshot_download(
                        repo_id=ungated_repo,
                        local_dir=str(target_dir),
                        token=None,
                        allow_patterns=allow_patterns
                    )
                except Exception as inner_e:
                    self._record_failure(model_id, f"Failed downloading from public mirror {ungated_repo}: {inner_e}")
                    return
            else:
                if is_gated:
                    friendly_err = (
                        f"Model '{repo_id}' is gated on Hugging Face. "
                        f"Please accept the license at https://huggingface.co/{repo_id} "
                        f"and set your token in config/hf_token.txt or run 'huggingface-cli login'."
                    )
                    self._record_failure(model_id, friendly_err)
                else:
                    self._record_failure(model_id, str(e))
                return

        total_size_mb = sum(f.stat().st_size for f in target_dir.glob("**/*") if f.is_file()) / (1024 * 1024)
        duration = max(1.0, time.time() - t_start)
        avg_speed = round(total_size_mb / duration, 2)

        with self._lock:
            self.active_downloads[model_id] = {
                "status": "complete",
                "progress": 100.0,
                "downloaded_mb": round(total_size_mb, 1),
                "total_mb": round(total_size_mb, 1),
                "speed_mbps": avg_speed,
                "error": None
            }
        app_logger.info(f"[Downloader] Successfully downloaded {model_id} ({total_size_mb:.1f} MB) in {duration:.1f}s")

    def _record_failure(self, model_id: str, error_msg: str):
        app_logger.error(f"[Downloader] Download failed for {model_id}: {error_msg}")
        with self._lock:
            self.active_downloads[model_id] = {
                "status": "failed",
                "progress": 0.0,
                "downloaded_mb": 0.0,
                "total_mb": 0.0,
                "speed_mbps": 0.0,
                "error": error_msg
            }

model_downloader = ModelDownloader()
