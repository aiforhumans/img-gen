import gc
import os
import sys
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple
from backend.app.core.logger import app_logger, error_logger

class VRAMStrategy(str, Enum):
    FULL_GPU = "FULL_GPU"          # Whole model in VRAM (fastest, requires <12GB)
    BALANCED = "BALANCED"          # Model weights in VRAM, selective offloading
    LOW_VRAM = "LOW_VRAM"          # Sequential CPU offload + dynamic attention
    CPU_OFFLOAD = "CPU_OFFLOAD"    # Aggressive model CPU offloading

class VRAMManager:
    """
    Central VRAM Manager specifically engineered for RTX 5080 (16 GB VRAM)
    and dynamic diffusion model lifecycle management.
    """
    def __init__(self, target_vram_gb: float = 16.0):
        self.target_vram_gb = target_vram_gb
        self.current_strategy: VRAMStrategy = VRAMStrategy.FULL_GPU
        self.loaded_models: Dict[str, Any] = {} # model_id -> adapter
        self.peak_vram_mb: float = 0.0

    def has_cuda(self) -> bool:
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def get_gpu_info(self) -> Dict[str, Any]:
        info = {
            "has_cuda": False,
            "gpu_name": "CPU Fallback / No CUDA",
            "vram_total_mb": 0.0,
            "vram_allocated_mb": 0.0,
            "vram_reserved_mb": 0.0,
            "vram_free_mb": 0.0,
            "vram_strategy": self.current_strategy.value,
            "cuda_version": "N/A",
            "torch_version": "N/A",
            "driver_version": "N/A"
        }

        try:
            import torch
            info["torch_version"] = torch.__version__
            if torch.cuda.is_available():
                info["has_cuda"] = True
                info["cuda_version"] = torch.version.cuda or "Unknown"
                info["gpu_name"] = torch.cuda.get_device_name(0)

                total_b = torch.cuda.get_device_properties(0).total_memory
                allocated_b = torch.cuda.memory_allocated(0)
                reserved_b = torch.cuda.memory_reserved(0)

                info["vram_total_mb"] = round(total_b / (1024 * 1024), 1)
                info["vram_allocated_mb"] = round(allocated_b / (1024 * 1024), 1)
                info["vram_reserved_mb"] = round(reserved_b / (1024 * 1024), 1)
                info["vram_free_mb"] = round((total_b - reserved_b) / (1024 * 1024), 1)
        except Exception as e:
            app_logger.warning(f"Error querying GPU info: {e}")

        # Try to parse driver version if on windows with nvidia-smi
        try:
            import subprocess
            res = subprocess.run(
                ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=2
            )
            if res.returncode == 0:
                info["driver_version"] = res.stdout.strip()
        except Exception:
            pass

        return info

    def safe_empty_cache(self):
        """Safely cleans CUDA cache and executes python garbage collection."""
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
        except Exception as e:
            app_logger.debug(f"Cache flush notice: {e}")

    def determine_strategy(self, estimated_vram_gb: float) -> VRAMStrategy:
        """
        Dynamically chooses the optimal memory strategy based on the 16 GB RTX 5080 headroom.
        """
        gpu_info = self.get_gpu_info()
        total_vram = gpu_info.get("vram_total_mb", 16384) / 1024.0

        if estimated_vram_gb <= 8.0 and total_vram >= 14.0:
            return VRAMStrategy.FULL_GPU
        elif estimated_vram_gb <= 13.0 and total_vram >= 14.0:
            return VRAMStrategy.BALANCED
        elif estimated_vram_gb <= 17.0:
            return VRAMStrategy.LOW_VRAM
        else:
            return VRAMStrategy.CPU_OFFLOAD

    def register_loaded_model(self, model_id: str, adapter: Any):
        # Enforce maximum 1 active heavy model in VRAM at a time
        for existing_id, existing_adapter in list(self.loaded_models.items()):
            if existing_id != model_id:
                app_logger.info(f"[VRAMManager] Unloading inactive model '{existing_id}' to free VRAM")
                try:
                    existing_adapter.unload()
                except Exception as e:
                    app_logger.error(f"Error unloading '{existing_id}': {e}")
                self.loaded_models.pop(existing_id, None)

        self.loaded_models[model_id] = adapter
        self.safe_empty_cache()

    def unload_all(self):
        for model_id, adapter in list(self.loaded_models.items()):
            try:
                adapter.unload()
            except Exception as e:
                app_logger.error(f"Error unloading model {model_id}: {e}")
        self.loaded_models.clear()
        self.safe_empty_cache()

    def record_peak_vram(self) -> float:
        try:
            import torch
            if torch.cuda.is_available():
                max_mem = torch.cuda.max_memory_allocated(0) / (1024 * 1024)
                self.peak_vram_mb = max(self.peak_vram_mb, max_mem)
                return round(max_mem, 1)
        except Exception:
            pass
        return 0.0

    def reset_peak_vram(self):
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.reset_peak_memory_stats(0)
        except Exception:
            pass
        self.peak_vram_mb = 0.0

    def step_down_strategy(self) -> Optional[VRAMStrategy]:
        """
        Escalates memory conservatism upon OOM or memory pressure.
        """
        return self.step_down_strategy_from(self.current_strategy.value)

    def step_down_strategy_from(self, strat_str: str) -> Optional[VRAMStrategy]:
        """
        Steps down from a specific strategy string:
        FULL_GPU -> BALANCED -> LOW_VRAM -> CPU_OFFLOAD -> None
        """
        progression = {
            VRAMStrategy.FULL_GPU: VRAMStrategy.BALANCED,
            VRAMStrategy.BALANCED: VRAMStrategy.LOW_VRAM,
            VRAMStrategy.LOW_VRAM: VRAMStrategy.CPU_OFFLOAD,
            VRAMStrategy.CPU_OFFLOAD: None
        }
        try:
            curr = VRAMStrategy(strat_str)
        except Exception:
            curr = VRAMStrategy.BALANCED

        next_strat = progression.get(curr)
        if next_strat:
            app_logger.warning(
                f"[VRAMManager] Stepping down strategy from {curr.value} to {next_strat.value}"
            )
            self.current_strategy = next_strat
        return next_strat

vram_manager = VRAMManager()
