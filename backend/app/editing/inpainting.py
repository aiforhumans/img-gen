from typing import Tuple
from PIL import Image, ImageFilter, ImageOps

def prepare_inpaint_mask(mask: Image.Image, feather_radius: int = 4, invert: bool = False) -> Image.Image:
    """Preprocesses user drawn inpaint mask with optional inversion and edge feathering."""
    m = mask.convert("L")
    if invert:
        m = ImageOps.invert(m)
    if feather_radius > 0:
        m = m.filter(ImageFilter.GaussianBlur(radius=feather_radius))
    return m

def blend_inpainted_result(original: Image.Image, inpainted: Image.Image, mask: Image.Image) -> Image.Image:
    """Seamlessly composites generated inpaint output over the original image using the feathered mask."""
    w, h = original.size
    inp = inpainted.resize((w, h)).convert("RGB")
    m = mask.resize((w, h)).convert("L")
    result = original.copy().convert("RGB")
    result.paste(inp, (0, 0), m)
    return result
