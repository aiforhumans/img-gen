class GenerationCancelled(Exception):
    """Raised when a generation job is explicitly cancelled by the user."""
    pass

class ModelLoadError(Exception):
    """Raised when loading model weights fails or weights do not exist."""
    pass

class OOMRetryExhausted(Exception):
    """Raised when CUDA OOM retries have been exhausted across all VRAM strategies."""
    pass
