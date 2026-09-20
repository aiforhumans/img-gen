from typing import Dict, List, Any, Optional
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
        "Euler"
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

class SchedulerFactory:
    """
    Centralized architecture-aware scheduler/sampler system.
    Ensures that only supported samplers are instantiated for a given model architecture,
    preventing runtime errors or silently ignored parameters.
    """

    @classmethod
    def get_supported_samplers(cls, architecture: str) -> List[str]:
        return ARCHITECTURE_SCHEDULERS.get(architecture.lower(), ["Default (Recommended)"])

    @classmethod
    def is_compatible(cls, architecture: str, sampler_name: str) -> bool:
        if not sampler_name or sampler_name in ["Default", "Default (Recommended)", "default"]:
            return True
        supported = cls.get_supported_samplers(architecture)
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
    def create_scheduler(cls, pipeline_scheduler_config: Any, architecture: str, sampler_name: str) -> Any:
        """
        Instantiates the requested Diffusers scheduler from config.
        Falls back to recommended scheduler if 'Default (Recommended)' is passed.
        """
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
