from typing import Dict, Tuple
from PIL import Image

PRESET_CONVERSIONS = {
    "square_to_portrait": {"left": 0, "right": 0, "top": 128, "bottom": 128}, # 1:1 -> 3:4
    "square_to_landscape": {"left": 192, "right": 192, "top": 0, "bottom": 0}, # 1:1 -> 16:9
    "landscape_to_phone": {"left": 0, "right": 0, "top": 300, "bottom": 300}, # 16:9 -> 9:16
    "portrait_to_cinema": {"left": 350, "right": 350, "top": 0, "bottom": 0}  # 3:4 -> 21:9
}

def calculate_expansion_for_preset(preset_key: str, width: int, height: int) -> Dict[str, int]:
    """Calculates directional pixel padding based on target aspect-ratio presets."""
    if preset_key in PRESET_CONVERSIONS:
        return PRESET_CONVERSIONS[preset_key]
    return {"left": 128, "right": 128, "top": 0, "bottom": 0}

def create_outpaint_canvas(
    image: Image.Image,
    expand_left: int,
    expand_right: int,
    expand_top: int,
    expand_bottom: int
) -> Tuple[Image.Image, Image.Image]:
    """
    Expands an image canvas and creates a binary mask where:
    - 0 represents original pixels
    - 255 represents expanded region to be generated
    """
    orig_w, orig_h = image.size
    new_w = orig_w + expand_left + expand_right
    new_h = orig_h + expand_top + expand_bottom

    canvas = Image.new("RGB", (new_w, new_h), (20, 20, 25))
    canvas.paste(image, (expand_left, expand_top))

    mask = Image.new("L", (new_w, new_h), 255)
    inner = Image.new("L", (orig_w, orig_h), 0)
    mask.paste(inner, (expand_left, expand_top))

    return canvas, mask
