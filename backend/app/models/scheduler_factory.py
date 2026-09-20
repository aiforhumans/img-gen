from typing import Dict, List, Any, Optional, Tuple
from backend.app.core.logger import app_logger

# Schedulers supported per model architecture
ARCHITECTURE_SCHEDULERS: Dict[str, List[str]] = {
    "sdxl": [
        "Default (Recommended)",
        "Euler",
        "Euler Ancestral",
        "DPM++ 2M Karras",
        "DDIM"
    ],
    "zimage": [
        "Default (Recommended)",
        "Euler",
        "DPM++ 2M Karras",
        "Euler Ancestral",
        "DDIM"
    ],
    "flux": [
        "Default (Recommended)",
        "FlowMatch Euler"
    ],
    "qwen": [
        "Default (Recommended)",
        "DPM++ 2M Karras",
        "Euler"
    ]
}

# Step-aware sampler compatibility for Lightning-distilled models (Z-Image Turbo).
# Lightning distillation was trained with specific noise schedules — using incompatible
# samplers at low step counts produces blurry/artifacted output because the noise
# trajectory doesn't match the distillation training.
ZIMAGE_STEP_SCHEDULERS: Dict[int, List[str]] = {
    2: ["Default (Recommended)", "Euler"],
    4: ["Default (Recommended)", "Euler", "DPM++ 2M Karras"],
    8: ["Default (Recommended)", "Euler", "DPM++ 2M Karras", "Euler Ancestral", "DDIM"],
}

# The universal safe fallback for Z-Image Turbo at any step count
ZIMAGE_SAFE_FALLBACK = "Euler"


class SchedulerFactory:
    """
    Centralized architecture-aware scheduler/sampler system.
    Ensures that only supported samplers are instantiated for a given model architecture,
    preventing runtime errors or silently ignored parameters.

    For Z-Image Turbo (Lightning-distilled), the factory enforces step-aware compatibility:
    - 2-step: Only Euler (trailing) is safe
    - 4-step: Euler (trailing) + DPM++ 2M Karras
    - 8-step: Full sampler menu
    """

    @classmethod
    def get_supported_samplers(cls, architecture: str) -> List[str]:
        return ARCHITECTURE_SCHEDULERS.get(architecture.lower(), ["Default (Recommended)"])

    @classmethod
    def get_step_aware_samplers(cls, architecture: str, steps: int) -> List[str]:
        """Returns the compatible sampler list for a given architecture and step count.

        For Z-Image Turbo, this filters the sampler list based on Lightning distillation
        compatibility at the requested step count. For other architectures, returns the
        full architecture-level list.
        """
        if architecture.lower() == "zimage":
            # Find the closest matching step tier (2, 4, 8)
            step_tier = cls._get_zimage_step_tier(steps)
            return ZIMAGE_STEP_SCHEDULERS.get(step_tier, ZIMAGE_STEP_SCHEDULERS[8])
        return cls.get_supported_samplers(architecture)

    @classmethod
    def _get_zimage_step_tier(cls, steps: int) -> int:
        """Maps an arbitrary step count to the nearest Lightning tier (2, 4, or 8)."""
        if steps <= 2:
            return 2
        elif steps <= 4:
            return 4
        else:
            return 8

    @classmethod
    def is_compatible(cls, architecture: str, sampler_name: str) -> bool:
        if not sampler_name or sampler_name in ["Default", "Default (Recommended)", "default"]:
            return True
        supported = cls.get_supported_samplers(architecture)
        normalized_supported = [s.lower() for s in supported]
        return sampler_name.lower() in normalized_supported

    @classmethod
    def is_step_compatible(cls, architecture: str, sampler_name: str, steps: int) -> bool:
        """Checks if a sampler is compatible with a specific step count for the architecture."""
        if not sampler_name or sampler_name in ["Default", "Default (Recommended)", "default"]:
            return True
        supported = cls.get_step_aware_samplers(architecture, steps)
        normalized_supported = [s.lower() for s in supported]
        return sampler_name.lower() in normalized_supported

    @classmethod
    def validate_sampler(cls, architecture: str, sampler_name: str):
        if not cls.is_compatible(architecture, sampler_name):
            supported = cls.get_supported_samplers(architecture)
            raise ValueError(
                f"Sampler '{sampler_name}' is not supported for architecture '{architecture}'. "
                f"Compatible samplers for {architecture}: {', '.join(supported)}"
            )

    @classmethod
    def validate_step_sampler(cls, architecture: str, sampler_name: str, steps: int) -> Tuple[bool, str]:
        """Validates sampler compatibility with step count. Returns (is_valid, resolved_sampler).

        If the sampler is incompatible with the step count for this architecture,
        returns (False, fallback_sampler) instead of raising an error.
        This enables soft fallback behavior in the generation pipeline.
        """
        if not sampler_name or sampler_name in ["Default", "Default (Recommended)", "default"]:
            return (True, ZIMAGE_SAFE_FALLBACK if architecture.lower() == "zimage" else sampler_name or "Default (Recommended)")

        if cls.is_step_compatible(architecture, sampler_name, steps):
            return (True, sampler_name)

        # Incompatible — return the safe fallback
        compatible = cls.get_step_aware_samplers(architecture, steps)
        app_logger.warning(
            f"[SchedulerFactory] Sampler '{sampler_name}' is incompatible with {steps}-step "
            f"{architecture} generation. Falling back to '{ZIMAGE_SAFE_FALLBACK}'. "
            f"Compatible samplers at {steps} steps: {', '.join(compatible)}"
        )
        return (False, ZIMAGE_SAFE_FALLBACK)

    @classmethod
    def create_scheduler(cls, pipeline_scheduler_config: Any, architecture: str, sampler_name: str, steps: int = 8) -> Any:
        """
        Instantiates the requested Diffusers scheduler from config.
        Falls back to recommended scheduler if 'Default (Recommended)' is passed.

        For Z-Image Turbo, enforces step-aware compatibility and falls back to
        Euler Trailing if the requested sampler is incompatible with the step count.
        """
        # Step-aware validation for Lightning-distilled models
        if architecture.lower() == "zimage":
            is_valid, resolved_sampler = cls.validate_step_sampler(architecture, sampler_name, steps)
            if not is_valid:
                sampler_name = resolved_sampler
        else:
            cls.validate_sampler(architecture, sampler_name)

        norm = (sampler_name or "default").lower()

        try:
            if "flowmatch" in norm:
                from diffusers import FlowMatchEulerDiscreteScheduler
                return FlowMatchEulerDiscreteScheduler.from_config(pipeline_scheduler_config)

            if "ancestral" in norm or norm == "euler a":
                from diffusers import EulerAncestralDiscreteScheduler
                return EulerAncestralDiscreteScheduler.from_config(pipeline_scheduler_config)

            if "dpm" in norm:
                from diffusers import DPMSolverMultistepScheduler
                return DPMSolverMultistepScheduler.from_config(
                    pipeline_scheduler_config,
                    use_karras_sigmas=True,
                    algorithm_type="dpmsolver++"
                )

            if "ddim" in norm:
                from diffusers import DDIMScheduler
                return DDIMScheduler.from_config(pipeline_scheduler_config)

            # Default or Euler
            from diffusers import EulerDiscreteScheduler
            if architecture.lower() == "zimage":
                return EulerDiscreteScheduler.from_config(
                    pipeline_scheduler_config,
                    timestep_spacing="trailing"
                )
            elif architecture.lower() == "flux":
                from diffusers import FlowMatchEulerDiscreteScheduler
                return FlowMatchEulerDiscreteScheduler.from_config(pipeline_scheduler_config)
            else:
                return EulerDiscreteScheduler.from_config(pipeline_scheduler_config)

        except Exception as e:
            app_logger.warning(f"Could not build scheduler '{sampler_name}' from config: {e}. Preserving pipeline scheduler.")
            return None
