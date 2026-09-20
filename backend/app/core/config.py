import json
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "default_settings.json"
USER_CONFIG_PATH = PROJECT_ROOT / "config" / "user_settings.json"

class GeneralConfig(BaseModel):
    app_name: str = "Antigravity Diffusion Studio"
    version: str = "1.0.0"
    host: str = "127.0.0.1"
    port: int = 7860
    theme: str = "dark"

class PathsConfig(BaseModel):
    model_dirs: List[str] = [str(PROJECT_ROOT / "models")]
    lora_dirs: List[str] = [str(PROJECT_ROOT / "models" / "loras")]
    output_dir: str = str(PROJECT_ROOT / "outputs")
    cache_dir: str = str(PROJECT_ROOT / "cache")

class GenerationConfig(BaseModel):
    default_model: str = "auto"
    default_aspect_ratio: str = "1:1"
    default_quality: str = "balanced"
    default_mode: str = "auto"
    live_preview: bool = True
    preview_frequency: int = 2
    low_res_preview: bool = True
    save_metadata_to_png: bool = True

class VRAMConfig(BaseModel):
    default_strategy: str = "FULL_GPU"
    auto_unload_inactive: bool = True
    max_loaded_models: int = 1
    target_gpu_vram_gb: int = 16
    oom_retry_enabled: bool = True

class LMStudioConfig(BaseModel):
    enabled: bool = True
    base_url: str = "http://127.0.0.1:1234/v1"
    timeout_seconds: int = 15
    preferred_model: str = "auto"

class AppSettings(BaseModel):
    general: GeneralConfig = Field(default_factory=GeneralConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    vram: VRAMConfig = Field(default_factory=VRAMConfig)
    lm_studio: LMStudioConfig = Field(default_factory=LMStudioConfig)

def load_settings() -> AppSettings:
    settings_dict = {}
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                settings_dict = json.load(f)
        except Exception as e:
            print(f"Warning: Could not read default_settings.json: {e}")

    if USER_CONFIG_PATH.exists():
        try:
            with open(USER_CONFIG_PATH, "r", encoding="utf-8") as f:
                user_dict = json.load(f)
                # Deep merge top-level keys
                for k, v in user_dict.items():
                    if isinstance(v, dict) and k in settings_dict:
                        settings_dict[k].update(v)
                    else:
                        settings_dict[k] = v
        except Exception as e:
            print(f"Warning: Could not read user_settings.json: {e}")

    try:
        return AppSettings.model_validate(settings_dict)
    except Exception as e:
        print(f"Error parsing configuration: {e}, using defaults.")
        return AppSettings()

def save_user_settings(settings: AppSettings) -> bool:
    try:
        USER_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(USER_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(settings.model_dump(), f, indent=2)
        return True
    except Exception as e:
        print(f"Failed to save user settings: {e}")
        return False

settings = load_settings()
