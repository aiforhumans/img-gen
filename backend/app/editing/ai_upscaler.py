import os
import math
import time
import urllib.request
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
import numpy as np

from backend.app.core.logger import app_logger

# ---------------------------------------------------------------------------
# Pure PyTorch RRDBNet Architecture (Real-ESRGAN)
# Zero external binary / basicsr dependencies needed.
# ---------------------------------------------------------------------------

class ResidualDenseBlock(nn.Module):
    def __init__(self, num_feat: int = 64, num_grow_ch: int = 32):
        super().__init__()
        self.conv1 = nn.Conv2d(num_feat, num_grow_ch, 3, 1, 1)
        self.conv2 = nn.Conv2d(num_feat + num_grow_ch, num_grow_ch, 3, 1, 1)
        self.conv3 = nn.Conv2d(num_feat + 2 * num_grow_ch, num_grow_ch, 3, 1, 1)
        self.conv4 = nn.Conv2d(num_feat + 3 * num_grow_ch, num_grow_ch, 3, 1, 1)
        self.conv5 = nn.Conv2d(num_feat + 4 * num_grow_ch, num_feat, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(negative_slope=0.2, inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x1 = self.lrelu(self.conv1(x))
        x2 = self.lrelu(self.conv2(torch.cat((x, x1), 1)))
        x3 = self.lrelu(self.conv3(torch.cat((x, x1, x2), 1)))
        x4 = self.lrelu(self.conv4(torch.cat((x, x1, x2, x3), 1)))
        x5 = self.conv5(torch.cat((x, x1, x2, x3, x4), 1))
        return x5 * 0.2 + x


class RRDB(nn.Module):
    def __init__(self, num_feat: int = 64, num_grow_ch: int = 32):
        super().__init__()
        self.rdb1 = ResidualDenseBlock(num_feat, num_grow_ch)
        self.rdb2 = ResidualDenseBlock(num_feat, num_grow_ch)
        self.rdb3 = ResidualDenseBlock(num_feat, num_grow_ch)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.rdb1(x)
        out = self.rdb2(out)
        out = self.rdb3(out)
        return out * 0.2 + x


class RRDBNet(nn.Module):
    def __init__(
        self,
        num_in_ch: int = 3,
        num_out_ch: int = 3,
        num_feat: int = 64,
        num_block: int = 23,
        num_grow_ch: int = 32,
        scale: int = 4
    ):
        super().__init__()
        self.scale = scale
        self.conv_first = nn.Conv2d(num_in_ch, num_feat, 3, 1, 1)
        self.body = nn.Sequential(*[RRDB(num_feat, num_grow_ch) for _ in range(num_block)])
        self.conv_body = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        # upsampling
        self.conv_up1 = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        self.conv_up2 = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        self.conv_hr = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        self.conv_last = nn.Conv2d(num_feat, num_out_ch, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(negative_slope=0.2, inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        feat = self.conv_first(x)
        body_feat = self.conv_body(self.body(feat))
        feat = feat + body_feat
        # 2x upsample
        feat = self.lrelu(self.conv_up1(F.interpolate(feat, scale_factor=2, mode='nearest')))
        # 4x upsample
        feat = self.lrelu(self.conv_up2(F.interpolate(feat, scale_factor=2, mode='nearest')))
        out = self.conv_last(self.lrelu(self.conv_hr(feat)))
        return out


# ---------------------------------------------------------------------------
# Weight URLs & Directories
# ---------------------------------------------------------------------------

MODELS_DIR = Path("models/upscalers")
WEIGHT_URLS = {
    "realesrgan_photo": {
        "filename": "RealESRGAN_x4plus.pth",
        "url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
        "num_block": 23,
    },
    "realesrgan_anime": {
        "filename": "RealESRGAN_x4plus_anime_6B.pth",
        "url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth",
        "num_block": 6,
    }
}


class AIUpscaler:
    """
    Production-grade AI Latent Super-Resolution engine.
    Supports tiled inference, 2x/4x scaling, model hot-swapping, and memory-safe VRAM offloading.
    """

    def __init__(self):
        self.current_engine_name: Optional[str] = None
        self.model: Optional[RRDBNet] = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def _download_weights(self, engine_name: str) -> Path:
        info = WEIGHT_URLS.get(engine_name)
        if not info:
            raise ValueError(f"Unknown upscaler engine: {engine_name}")

        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        dest_path = MODELS_DIR / info["filename"]

        if not dest_path.exists():
            app_logger.info(f"[AIUpscaler] Downloading weights for {engine_name} from {info['url']}...")
            try:
                urllib.request.urlretrieve(info["url"], str(dest_path))
                app_logger.info(f"[AIUpscaler] Downloaded {dest_path.name} successfully.")
            except Exception as e:
                if dest_path.exists():
                    dest_path.unlink()
                raise RuntimeError(f"Failed to download upscaler weights {info['filename']}: {e}")

        return dest_path

    def load_model(self, engine_name: str = "realesrgan_photo") -> None:
        if self.current_engine_name == engine_name and self.model is not None:
            return

        is_sim = os.environ.get("DEV_SIMULATION_MODE", "false").lower() == "true"
        if is_sim:
            app_logger.info(f"[AIUpscaler] [SIMULATION] Loaded {engine_name} model.")
            self.current_engine_name = engine_name
            return

        weight_path = self._download_weights(engine_name)
        num_block = WEIGHT_URLS[engine_name]["num_block"]

        app_logger.info(f"[AIUpscaler] Loading {engine_name} (RRDBNet blocks={num_block}) onto {self.device}...")
        model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=num_block, num_grow_ch=32, scale=4)
        
        loadnet = torch.load(str(weight_path), map_location="cpu")
        if "params_ema" in loadnet:
            keyname = "params_ema"
        elif "params" in loadnet:
            keyname = "params"
        else:
            keyname = None

        state_dict = loadnet[keyname] if keyname else loadnet
        model.load_state_dict(state_dict, strict=True)
        model.eval()

        dtype = torch.bfloat16 if (torch.cuda.is_available() and torch.cuda.is_bf16_supported()) else torch.float16
        if self.device.type == "cpu":
            dtype = torch.float32

        model = model.to(device=self.device, dtype=dtype)
        self.model = model
        self.current_engine_name = engine_name
        app_logger.info(f"[AIUpscaler] {engine_name} loaded successfully ({dtype}).")

    def unload(self) -> None:
        if self.model is not None:
            self.model.cpu()
            del self.model
            self.model = None
            self.current_engine_name = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            app_logger.info("[AIUpscaler] Unloaded upscaler from VRAM.")

    def _tile_process(self, img_tensor: torch.Tensor, tile_size: int = 512, tile_pad: int = 32) -> torch.Tensor:
        """
        Process large tensor in overlapping tiles to prevent VRAM spikes.
        """
        batch, channel, height, width = img_tensor.shape
        scale = 4
        output_height = height * scale
        output_width = width * scale
        output_tensor = torch.zeros(
            (batch, channel, output_height, output_width),
            dtype=img_tensor.dtype,
            device=img_tensor.device
        )
        tiles_x = math.ceil(width / tile_size)
        tiles_y = math.ceil(height / tile_size)

        for y in range(tiles_y):
            for x in range(tiles_x):
                # Calculate tile input coords with padding
                ofs_x = x * tile_size
                ofs_y = y * tile_size
                input_start_x = ofs_x
                input_end_x = min(ofs_x + tile_size, width)
                input_start_y = ofs_y
                input_end_y = min(ofs_y + tile_size, height)

                # Padded coords
                input_start_x_pad = max(input_start_x - tile_pad, 0)
                input_end_x_pad = min(input_end_x + tile_pad, width)
                input_start_y_pad = max(input_start_y - tile_pad, 0)
                input_end_y_pad = min(input_end_y + tile_pad, height)

                pad_left = input_start_x - input_start_x_pad
                pad_top = input_start_y - input_start_y_pad

                tile_in = img_tensor[:, :, input_start_y_pad:input_end_y_pad, input_start_x_pad:input_end_x_pad]
                with torch.no_grad():
                    tile_out = self.model(tile_in)

                # Crop out padding from output tile
                out_start_x = input_start_x * scale
                out_end_x = input_end_x * scale
                out_start_y = input_start_y * scale
                out_end_y = input_end_y * scale

                tile_crop_x = pad_left * scale
                tile_crop_y = pad_top * scale
                tile_w = (input_end_x - input_start_x) * scale
                tile_h = (input_end_y - input_start_y) * scale

                output_tensor[:, :, out_start_y:out_end_y, out_start_x:out_end_x] = tile_out[
                    :, :, tile_crop_y:tile_crop_y + tile_h, tile_crop_x:tile_crop_x + tile_w
                ]

        return output_tensor

    def upscale(
        self,
        image: Image.Image,
        scale: int = 4,
        engine_name: str = "realesrgan_photo"
    ) -> Image.Image:
        """
        Run neural super-resolution on a PIL image.
        """
        is_sim = os.environ.get("DEV_SIMULATION_MODE", "false").lower() == "true"
        w, h = image.size
        target_w = w * scale
        target_h = h * scale

        if is_sim:
            # High-quality bicubic simulation with slight sharpening for unit tests
            from PIL import ImageFilter
            sim_img = image.resize((target_w, target_h), Image.Resampling.BICUBIC)
            sim_img = sim_img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=120, threshold=3))
            return sim_img

        self.load_model(engine_name)

        t0 = time.time()
        img_np = np.array(image.convert("RGB")).astype(np.float32) / 255.0
        # HWC -> CHW -> NCHW
        img_t = torch.from_numpy(img_np).permute(2, 0, 1).unsqueeze(0)
        
        dtype = next(self.model.parameters()).dtype
        img_t = img_t.to(device=self.device, dtype=dtype)

        # Decide whether to tile: if width or height > 640px, use safe tiling
        if w > 640 or h > 640:
            out_t = self._tile_process(img_t, tile_size=512, tile_pad=32)
        else:
            with torch.no_grad():
                out_t = self.model(img_t)

        out_t = torch.clamp(out_t, 0.0, 1.0)
        out_np = (out_t.squeeze(0).permute(1, 2, 0).float().cpu().numpy() * 255.0).round().astype(np.uint8)
        result_img = Image.fromarray(out_np)

        # If 2x requested, downscale the 4x result with Lanczos for pristine supersampled fidelity
        if scale == 2:
            result_img = result_img.resize((target_w, target_h), Image.Resampling.LANCZOS)

        elapsed = time.time() - t0
        app_logger.info(f"[AIUpscaler] {engine_name} {scale}x upscale complete in {elapsed:.2f}s ({target_w}x{target_h}).")
        return result_img


ai_upscaler = AIUpscaler()
