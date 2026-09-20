import json
import os
from pathlib import Path
from typing import Dict, Any, List
from backend.app.core.config import settings
from backend.app.core.logger import app_logger

class LoRAScanner:
    """
    Scans configured directories for LoRA weights (.safetensors)
    and extracts metadata, trigger words, and base model compatibility.
    """
    def __init__(self):
        self.cached_loras: List[Dict[str, Any]] = []

    def scan_folders(self) -> List[Dict[str, Any]]:
        loras = []
        for lora_dir_str in settings.paths.lora_dirs:
            p = Path(lora_dir_str)
            if not p.exists():
                p.mkdir(parents=True, exist_ok=True)
                continue

            for file_path in p.glob("**/*"):
                if file_path.suffix.lower() in [".safetensors", ".pt", ".bin"]:
                    lora_info = self._parse_lora(file_path)
                    loras.append(lora_info)

        # Include sample reference LoRAs for UI out-of-the-box demonstration
        if not loras:
            loras = [
                {
                    "id": "cyberpunk_neon_v2",
                    "name": "Cyberpunk Neon Aesthetics",
                    "filename": "cyberpunk_neon_v2.safetensors",
                    "path": str(Path(settings.paths.lora_dirs[0]) / "cyberpunk_neon_v2.safetensors"),
                    "base_architecture": "flux",
                    "trigger_words": ["cyberpunk style", "neon glow", "night city"],
                    "file_size_mb": 142.5,
                    "default_strength": 0.8,
                    "is_favorite": True
                },
                {
                    "id": "cinematic_portrait_realism",
                    "name": "Cinematic Portrait Realism",
                    "filename": "cinematic_portrait_realism.safetensors",
                    "path": str(Path(settings.paths.lora_dirs[0]) / "cinematic_portrait_realism.safetensors"),
                    "base_architecture": "zimage",
                    "trigger_words": ["kodak portra", "studio headshot", "catchlight"],
                    "file_size_mb": 220.0,
                    "default_strength": 0.7,
                    "is_favorite": True
                },
                {
                    "id": "vintage_anime_sdxl",
                    "name": "90s Retro Anime SDXL",
                    "filename": "vintage_anime_sdxl.safetensors",
                    "path": str(Path(settings.paths.lora_dirs[0]) / "vintage_anime_sdxl.safetensors"),
                    "base_architecture": "sdxl",
                    "trigger_words": ["retro anime", "90s cel shading", "grain"],
                    "file_size_mb": 185.2,
                    "default_strength": 0.85,
                    "is_favorite": False
                }
            ]

        self.cached_loras = loras
        return loras

    def _parse_lora(self, file_path: Path) -> Dict[str, Any]:
        size_mb = round(file_path.stat().st_size / (1024 * 1024), 1)
        name = file_path.stem.replace("_", " ").replace("-", " ").title()

        arch = "flux"
        f_lower = file_path.stem.lower()
        if "sdxl" in f_lower:
            arch = "sdxl"
        elif "zimage" in f_lower or "portrait" in f_lower:
            arch = "zimage"

        return {
            "id": file_path.stem,
            "name": name,
            "filename": file_path.name,
            "path": str(file_path),
            "base_architecture": arch,
            "trigger_words": [file_path.stem.replace("_", " ")],
            "file_size_mb": size_mb,
            "default_strength": 1.0,
            "is_favorite": False
        }

lora_scanner = LoRAScanner()
