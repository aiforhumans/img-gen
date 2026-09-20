# 🚀 Antigravity Diffusion Studio

[![Hardware](https://img.shields.io/badge/GPU-NVIDIA%20RTX%205080%20(16GB)-76B900?logo=nvidia&logoColor=white)](#hardware-optimization)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.14%2Bcu130%20(CUDA%2013.0)-EE4C2C?logo=pytorch&logoColor=white)](#technical-architecture)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19%20%2B%20Vite%20%2B%20TS-61DAFB?logo=react&logoColor=black)](https://vitejs.dev)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Antigravity Diffusion Studio** is an ultra-fast, hardened, production-grade local generative AI platform engineered specifically for **Windows 11** and modern NVIDIA RTX GPUs (optimized for the **NVIDIA GeForce RTX 5080 16 GB Blackwell architecture**). 

Combining the simplicity of modern web studios with industrial-grade reliability, it delivers **sub-2-second photorealistic image synthesis**, native FLUX diffusion, centralized deterministic seed resolution, architecture-aware scheduler swapping, active LoRA management, automatic CUDA OOM recovery, and a lossless searchable SQLite gallery.

---

## ⚡ Key Highlights

- **⚡ Sub-2-Second Photorealism (`Z-Image Turbo`)**:
  Pre-distilled 8-step, 4-step, and 2-step SDXL-Lightning & Juggernaut-XL pipelines running at **5.3+ it/s directly in VRAM**.
- **🌊 Native FLUX Diffusion Engine**:
  High-fidelity diffusion with FlowMatch scheduling and automated memory offload to fit large models smoothly into 16 GB VRAM.
- **🛡️ Intelligent VRAM Coordinator & Automatic OOM Recovery**:
  4-tier memory coordinator (`FULL_GPU`, `BALANCED`, `LOW_VRAM`, `CPU_OFFLOAD`) with automatic cache flushing, single-active-model residency, and **automatic sequential OOM step-down retry** with hardware telemetry logging.
- **🎯 Canonical GenerationConfig**:
  Strict parameter validation and dimension quantization (multiples of 8) across the entire stack:
  $$\text{React UI} \longrightarrow \text{API} \longrightarrow \text{GenerationConfig} \longrightarrow \text{Job Queue} \longrightarrow \text{Router} \longrightarrow \text{Model Adapter} \longrightarrow \text{Real Inference} \longrightarrow \text{Metadata} \longrightarrow \text{Gallery} \longrightarrow \text{Reuse Settings}$$
- **🛑 Clean Job Cancellation**:
  Guaranteed cancellation semantics (`WAITING`, `PREPARING`, `LOADING_MODEL`, `GENERATING` $\rightarrow$ `CANCELLED`), never falsely reported as `FAILED`.
- **🚫 Zero Silent Fake Generations in Production**:
  Simulation generator is strictly placed behind `DEV_SIMULATION_MODE=true`. In production, missing weights or load failures immediately raise actionable errors.
- **🎲 Centrally Resolved Deterministic Seeds**:
  Seeds (`seed = -1`) are centrally resolved prior to inference via cryptographically secure randomness, ensuring perfect reproducibility via "Reuse Settings".
- **🎛️ Architecture-Aware Scheduler Factory**:
  Model-specific schedulers (Euler, Euler Ancestral, DPM++ 2M Karras, FlowMatch Euler, DDIM) with dynamic frontend filtering and backend validation.
- **🧬 Complete LoRA Support**:
  Active LoRA management with live strength adjustment, cross-architecture compatibility checking, and guaranteed unloading to prevent weight leakage between jobs.
- **✨ "Magic Polish" Prompt Intelligence & Style Presets**:
  Compose curated styles without modifying the user's `original_prompt`, plus optional local LM Studio integration (`http://127.0.0.1:1234/v1`) using Gemma/DeepSeek.
- **🎨 Interactive Inpainting & Outpainting Canvas**:
  Full HTML5 canvas with zoom, pan, brush control, mask inversion, and directional expansion with real image/mask backend dispatch.
- **🔍 2x & 4K Real-Time Upscaler**:
  Built-in Lanczos + unsharp contrast enhancement upscaling images up to 4K resolution in ~1.2s.
- **📦 Lossless Metadata & SQLite Gallery**:
  Full generation parameters, seeds, LoRAs, and hardware telemetry embedded into PNG text chunks (`tEXt`/`zTXt`) and indexed in SQLite.
- **🖥️ Zero-Config Windows 11 Launchers**:
  One-click setup with `install.bat`, `start.bat`, `download_models.bat`, `update.bat`, and `diagnostics.bat`.

---

## 🖥️ Hardware & Runtime Requirements

| Component | Requirement | Optimal / Tested Environment |
| :--- | :--- | :--- |
| **OS** | Windows 10/11 (64-bit) | Windows 11 Pro 64-bit |
| **GPU** | NVIDIA GeForce RTX (>= 8 GB VRAM) | **NVIDIA GeForce RTX 5080 (16 GB GDDR7)** |
| **CUDA Driver** | 560.xx or newer | Driver 616.92+ |
| **PyTorch** | PyTorch 2.4+ with CUDA | **PyTorch 2.14.0+cu130 (CUDA 13.0, sm_120 Blackwell)** |
| **Python** | Python 3.10 – 3.12 (64-bit) | Python 3.12.10 |
| **Node.js** | Node.js v20+ (for building frontend) | Node.js v24.17.0 |
| **LLM (Optional)**| LM Studio local server | `http://127.0.0.1:1234/v1` |

---

## 🚀 Quickstart

### 1. Installation
Clone the repository and run the automated installer:
```bat
git clone https://github.com/your-username/antigravity-diffusion-studio.git
cd antigravity-diffusion-studio
install.bat
```
`install.bat` will:
1. Verify NVIDIA GPU drivers and CUDA capabilities.
2. Initialize a Python 3.12 `.venv` environment.
3. Install PyTorch with native CUDA 13.0 (`torch==2.14.0+cu130`) deterministically via `requirements-torch-cu130.txt`.
4. Install backend dependencies and compile the frontend Vite application.

### 2. Download Diffusion Models
Run the interactive downloader to acquire model weights:
```bat
download_models.bat
```
Select from:
- `zimage-turbo`: SDXL-Lightning 8-Step Complete Checkpoint (~6.9 GB) *(Sub-2s generations)*
- `flux-klein-4b`: FLUX.1 Schnell Fast Diffusion Engine (~12–24 GB)
- `sdxl`: SDXL Turbo / Juggernaut-XL Foundation Checkpoints

*(Alternatively, place your existing `.safetensors` files directly into the `models/` directory).*

### 3. Launch the Studio
```bat
start.bat
```
Your default browser will open automatically at **`http://127.0.0.1:7860`**.

---

## 🏗️ Technical Architecture

```
antigravity-diffusion-studio/
├── backend/                        # FastAPI Python 3.12 Core
│   ├── app/
│   │   ├── api/                    # REST Endpoints (generate, models, gallery, system, styles, loras)
│   │   ├── core/                   # GenerationConfig, JobQueue, VRAMManager, Exceptions, Database
│   │   │   ├── generation_config.py# Authoritative Pydantic configuration model
│   │   │   ├── exceptions.py       # GenerationCancelled, ModelLoadError, OOMRetryExhausted
│   │   │   ├── job_queue.py        # Queue worker, seed resolution, OOM auto-recovery, cancellation
│   │   │   ├── vram_manager.py     # Strategy coordinator and memory profiler
│   │   │   └── database.py         # SQLite 3 WAL async gallery database
│   │   ├── models/                 # Model Adapters & Scheduler Factory
│   │   │   ├── scheduler_factory.py# Architecture-aware scheduler coordinator
│   │   │   ├── registry.py         # Thread-safe single-resident model registry
│   │   │   ├── base_adapter.py     # Base adapter with DEV_SIMULATION_MODE & LoRA hooks
│   │   │   ├── zimage/             # Z-Image Turbo adapter (SDXL-Lightning)
│   │   │   ├── sdxl/               # SDXL Foundation adapter
│   │   │   ├── flux/               # FLUX.2 Klein / Schnell adapter
│   │   │   └── qwen/               # Qwen-Image adapter
│   │   ├── prompt_engine/          # StyleComposer + LM Studio Client + Rule Analyzer
│   │   ├── gallery/                # PNG metadata chunk reader/writer
│   │   └── editing/                # Inpainting, Outpainting, and 2x/4K Upscaler
│   ├── requirements.txt            # Core backend dependencies (excluding torch)
│   ├── requirements-torch-cu130.txt# Deterministic CUDA 13.0 / RTX 5080 torch
│   └── requirements-torch-cu126.txt# Deterministic CUDA 12.6 torch
├── frontend/                       # React 19 + TypeScript + Vite UI
│   ├── src/
│   │   ├── components/             # PromptBar, ImagePreview, InpaintCanvas, AdvancedSettings, Monitors
│   │   ├── pages/                  # GeneratePage, ModelsPage, GalleryPage, EditPage, LoRAPage, SystemPage
│   │   ├── services/               # Typed API Client & Adaptive Polling
│   │   └── types.ts                # TypeScript definitions mirroring GenerationConfig
├── config/                         # Configuration & Style Presets (Portable relative paths)
│   ├── default_settings.json       # Hardware defaults (FULL_GPU, aspect ratio, models/ outputs/ cache)
│   └── styles/                     # Curated Style JSON files (cinematic, anime, analog film, etc.)
├── scripts/                        # Utility & Diagnostic Scripts
│   ├── preflight_check.py          # Detailed CUDA & hardware telemetry check
│   └── download_models.py          # Terminal model downloader
├── tests/                          # Comprehensive PyTest Automated Test Suite (25/25 Passing)
│   ├── test_unit_config.py         # Config, styles, schedulers, LoRA compatibility tests
│   ├── test_unit_cancellation_and_lifecycle.py # Cancellation, seed resolution, OOM, LoRA lifecycle
│   ├── test_unit_gallery_metadata.py # PNG metadata roundtrip & SQLite tests
│   ├── test_backend_core.py        # Router, hardware detection, registry tests
│   ├── test_api_endpoints.py       # REST API endpoint integration tests
│   └── test_turbo_features.py      # Upscaler and prompt polish tests
├── install.bat                     # Windows 11 Installer
├── start.bat                       # Studio Launcher (Silent logs, port conflict resolver)
├── download_models.bat             # Model Downloader CLI
├── update.bat                      # Dependency updater
└── diagnostics.bat                 # Non-invasive hardware diagnostic generator
```

---

## ⚙️ Configuration & VRAM Strategies

Settings can be customized in `config/default_settings.json` or through the **Settings** tab in the UI:

```json
{
  "general": {
    "host": "127.0.0.1",
    "port": 7860,
    "theme": "dark"
  },
  "vram": {
    "default_strategy": "FULL_GPU",
    "auto_unload_inactive": true,
    "max_loaded_models": 1,
    "target_gpu_vram_gb": 16
  },
  "paths": {
    "model_dirs": ["models"],
    "output_dir": "outputs",
    "cache_dir": "cache"
  },
  "lm_studio": {
    "enabled": true,
    "base_url": "http://127.0.0.1:1234/v1"
  }
}
```

### VRAM Strategies
- **`FULL_GPU` (Recommended for RTX 5080 / 16GB)**: Model resides 100% in VRAM for maximum speed (~1.5s per image).
- **`BALANCED`**: Intelligently keeps medium models in VRAM and offloads 20GB+ pipelines (e.g. FLUX) between forward passes via `enable_model_cpu_offload()`.
- **`LOW_VRAM`**: Enables model offloading, VAE slicing, and VAE tiling for 8–12 GB GPUs.
- **`CPU_OFFLOAD`**: Sequential layer-by-layer offloading to system RAM for heavy multitasking.

### Automatic OOM Auto-Recovery
If a job encounters a CUDA out-of-memory condition during inference:
$$\text{FULL\_GPU} \xrightarrow{\text{OOM}} \text{BALANCED} \xrightarrow{\text{OOM}} \text{LOW\_VRAM} \xrightarrow{\text{OOM}} \text{CPU\_OFFLOAD}$$
The job queue flushes memory (`torch.cuda.empty_cache()`, `gc.collect()`), steps down the strategy, and automatically retries without user intervention, logging the retry telemetry directly into the image metadata.

---

## 🧪 Testing & Validation

### Backend Tests
Run the comprehensive PyTest test suite:
```bash
.venv\Scripts\python.exe -m pytest -v
```
All 25 tests validate:
- Canonical `GenerationConfig` validation and dimension quantization.
- Deterministic seed resolution before inference.
- Guaranteed `CANCELLED` job state persistence.
- Zero silent fakes when checkpoints are missing (`ModelLoadError`).
- Architecture-aware scheduler validation (`SchedulerFactory`).
- LoRA architecture compatibility matching and cross-job unloading.
- PNG metadata embedding (`tEXt`/`zTXt`) and SQLite gallery round-tripping.
- Automatic OOM strategy step-down logic.

### Frontend Validation
```bash
# Type check & production bundle build
npm --prefix frontend run build

# Code linting
npm --prefix frontend run lint
```

---

## 📜 License

Distributed under the MIT License. See [LICENSE](LICENSE) for more details.
