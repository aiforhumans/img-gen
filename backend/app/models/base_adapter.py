from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable
from PIL import Image

class BaseImageModelAdapter(ABC):
    """
    Common Model Interface required for all architecture backends.
    Any engine (FLUX.2, Z-Image Turbo, Qwen Image, SDXL, or custom models)
    must implement this interface.
    """
    def __init__(self, model_id: str, name: str, architecture: str):
        self.model_id = model_id
        self.name = name
        self.architecture = architecture
        self.is_loaded: bool = False
        self.loaded_device: str = "cpu"
        self.current_vram_strategy: str = "BALANCED"
        self.loaded_loras: List[Dict[str, Any]] = []

    @abstractmethod
    def load(self, device: str = "cuda", vram_strategy: str = "BALANCED", precision: str = "fp16") -> bool:
        """Loads model weights into memory/VRAM according to strategy."""
        pass

    def has_weights(self) -> bool:
        """Returns True if local weights exist on disk for this model."""
        return False

    @abstractmethod
    def unload(self) -> bool:
        """Unloads model weights from VRAM and reclaims memory."""
        pass

    @abstractmethod
    def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        steps: int = 20,
        guidance: float = 7.0,
        seed: int = -1,
        callback: Optional[Callable[[int, int, Optional[Image.Image]], None]] = None
    ) -> Image.Image:
        """Performs Text-to-Image synthesis with optional step preview callback."""
        pass

    @abstractmethod
    def img2img(
        self,
        image: Image.Image,
        prompt: str,
        negative_prompt: str = "",
        strength: float = 0.75,
        steps: int = 20,
        guidance: float = 7.0,
        seed: int = -1,
        callback: Optional[Callable[[int, int, Optional[Image.Image]], None]] = None
    ) -> Image.Image:
        """Performs Image-to-Image transformation."""
        pass

    @abstractmethod
    def edit(
        self,
        image: Image.Image,
        instruction: str,
        seed: int = -1,
        callback: Optional[Callable[[int, int, Optional[Image.Image]], None]] = None
    ) -> Image.Image:
        """Performs instruction-based image editing."""
        pass

    @abstractmethod
    def inpaint(
        self,
        image: Image.Image,
        mask: Image.Image,
        prompt: str,
        negative_prompt: str = "",
        steps: int = 20,
        guidance: float = 7.0,
        seed: int = -1,
        callback: Optional[Callable[[int, int, Optional[Image.Image]], None]] = None
    ) -> Image.Image:
        """Performs localized inpainting on masked region."""
        pass

    @abstractmethod
    def outpaint(
        self,
        image: Image.Image,
        expand_left: int,
        expand_right: int,
        expand_top: int,
        expand_bottom: int,
        prompt: str,
        negative_prompt: str = "",
        steps: int = 20,
        guidance: float = 7.0,
        seed: int = -1,
        callback: Optional[Callable[[int, int, Optional[Image.Image]], None]] = None
    ) -> Image.Image:
        """Performs canvas extension and seamless boundary blending."""
        pass

    @abstractmethod
    def supports_lora(self) -> bool:
        """Returns True if this model architecture supports LoRA adaptation."""
        pass

    @abstractmethod
    def load_lora(self, lora_path: str, weight: float = 1.0) -> bool:
        """Attaches a LoRA adapter."""
        pass

    @abstractmethod
    def unload_lora(self, lora_path: str) -> bool:
        """Detaches a specific LoRA or all LoRAs."""
        pass

    @abstractmethod
    def estimate_vram(self, width: int = 1024, height: int = 1024, batch_size: int = 1) -> float:
        """Returns estimated required VRAM in GB."""
        pass

    @abstractmethod
    def supported_resolutions(self) -> List[Dict[str, Any]]:
        """Returns recommended aspect ratios and pixel resolutions."""
        pass

    @abstractmethod
    def recommended_settings(self) -> Dict[str, Any]:
        """Returns default steps, guidance, sampler, and scheduler."""
        pass
