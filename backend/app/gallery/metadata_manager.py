import json
from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image
from PIL.PngImagePlugin import PngInfo
from backend.app.core.logger import app_logger

def create_png_info(metadata: Dict[str, Any]) -> PngInfo:
    """Creates PNG metadata chunk containing both standard WebUI parameters and full JSON metadata."""
    pnginfo = PngInfo()

    prompt = metadata.get("prompt", "")
    neg_prompt = metadata.get("negative_prompt", "")
    steps = metadata.get("steps", 20)
    guidance = metadata.get("guidance", 7.0)
    seed = metadata.get("seed", -1)
    width = metadata.get("width", 1024)
    height = metadata.get("height", 1024)
    model = metadata.get("model", "unknown")
    sampler = metadata.get("sampler", "euler_a")

    # Standard format compatible with CivitAI / WebUI / Fooocus readers
    params_str = (
        f"{prompt}\n"
        f"Negative prompt: {neg_prompt}\n"
        f"Steps: {steps}, Sampler: {sampler}, CFG scale: {guidance}, Seed: {seed}, "
        f"Size: {width}x{height}, Model: {model}"
    )

    pnginfo.add_text("parameters", params_str)
    pnginfo.add_text("prompt", prompt)
    if neg_prompt:
        pnginfo.add_text("negative_prompt", neg_prompt)

    # Full structured lossless JSON payload
    pnginfo.add_text("antigravity_metadata", json.dumps(metadata, ensure_ascii=False))

    return pnginfo

def extract_metadata_from_png(image_path: Path) -> Dict[str, Any]:
    """Reads embedded generation metadata from PNG file."""
    try:
        with Image.open(image_path) as img:
            info = img.info or {}

            # First priority: structured JSON
            if "antigravity_metadata" in info:
                try:
                    return json.loads(info["antigravity_metadata"])
                except Exception as e:
                    app_logger.warning(f"Failed to parse JSON metadata from {image_path}: {e}")

            # Second priority: standard parameters string
            if "parameters" in info:
                return parse_webui_parameters(info["parameters"])

    except Exception as e:
        app_logger.warning(f"Could not extract PNG metadata from {image_path}: {e}")

    return {}

def parse_webui_parameters(raw_text: str) -> Dict[str, Any]:
    """Parses standard Fooocus / WebUI parameters text into structured dictionary."""
    lines = raw_text.strip().split("\n")
    if not lines:
        return {}

    data: Dict[str, Any] = {"prompt": lines[0]}
    neg_prompt = ""

    for line in lines[1:]:
        if line.startswith("Negative prompt:"):
            neg_prompt = line.replace("Negative prompt:", "").strip()
        elif "Steps:" in line:
            parts = [p.strip() for p in line.split(",")]
            for part in parts:
                if ":" in part:
                    k, v = part.split(":", 1)
                    k = k.strip().lower()
                    v = v.strip()
                    if k == "steps":
                        data["steps"] = int(v) if v.isdigit() else 20
                    elif k in ["cfg scale", "cfg", "guidance"]:
                        try: data["guidance"] = float(v)
                        except ValueError: pass
                    elif k == "seed":
                        try: data["seed"] = int(v)
                        except ValueError: pass
                    elif k == "sampler":
                        data["sampler"] = v
                    elif k == "model":
                        data["model"] = v
                    elif k == "size":
                        if "x" in v:
                            w, h = v.split("x")
                            try:
                                data["width"] = int(w)
                                data["height"] = int(h)
                            except ValueError: pass

    data["negative_prompt"] = neg_prompt
    return data
