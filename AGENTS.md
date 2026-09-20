# 🤖 AGENTS.md — Agent & Developer Operational Manual

> **Repository**: Antigravity Diffusion Studio (`aiforhumans/img-gen`)  
> **Platform Target**: Windows 11 (x64) • NVIDIA RTX 5080 (16 GB GDDR7, sm_120 Blackwell) • CUDA 13.0  
> **Core Stack**: Python 3.12, FastAPI, PyTorch 2.14+cu130, React 19 + TypeScript + Vite, SQLite 3 WAL  

Welcome, AI agent! This document specifies the architectural invariants, core conventions, development commands, and design rules you MUST follow when modifying or extending this codebase.

---

## 🏛️ System Architecture Overview

Antigravity Diffusion Studio is a hardened, production-grade local diffusion engine with a unified generation contract:

$$\text{React 19 UI} \xrightarrow{\text{JSON API}} \text{FastAPI} \xrightarrow{\text{Pydantic}} \text{GenerationConfig} \xrightarrow{\text{Async}} \text{JobQueue} \xrightarrow{\text{Resolved Seed}} \text{ModelRegistry} \xrightarrow{\text{Adapter}} \text{Inference} \xrightarrow{\text{PNG Chunks}} \text{SQLite Gallery}$$

### Component Breakdown
- **`backend/app/core/generation_config.py`**: The authoritative single source of truth for all generation parameters.
- **`backend/app/core/job_queue.py`**: Background asynchronous task executor. Resolves seeds, executes sequential OOM step-down retries, manages cancellation signals, and records execution telemetry.
- **`backend/app/core/vram_manager.py`**: 4-tier memory manager (`FULL_GPU`, `BALANCED`, `LOW_VRAM`, `CPU_OFFLOAD`) coordinating PyTorch memory, garbage collection, and offloading.
- **`backend/app/models/registry.py`**: Thread-safe model registry enforcing **single-active-model residency** in VRAM.
- **`backend/app/models/scheduler_factory.py`**: Architecture- and step-aware noise scheduler creator with automatic soft fallbacks.
- **`backend/app/models/ip_adapter_manager.py`**: Central manager for IP-Adapter weights, CLIP image encoder, and dual-reference conditioning.
- **`backend/app/gallery/metadata.py`**: Lossless metadata embedding using PNG standard `tEXt` and `zTXt` chunks.
- **`frontend/`**: Vite + React 19 + TypeScript studio with dark-mode glassmorphic UI, real-time telemetry polling, inpainting canvas, and settings reuse.

---

## ⚠️ Non-Negotiable Invariants

When implementing features or refactoring, you must preserve these core rules:

### 1. Zero Silent Fakes in Production
- **RULE**: Never fall back to mock generation or black dummy images when model weights are missing or corrupted in normal operation.
- Dummy generation is strictly guarded behind `DEV_SIMULATION_MODE=true` for lightweight CI/unit tests.
- When weights are missing or inference fails in production, raise explicit, actionable exceptions (`ModelLoadError`, `RuntimeError`).

### 2. Canonical `GenerationConfig`
- All generation requests MUST deserialize into `GenerationConfig`.
- Width and height must be strictly quantized to **multiples of 8** (`value - (value % 8)`).
- Never add fields to the API or Frontend without corresponding validation in `GenerationConfig` and mapping in `types.ts`.

### 3. Centralized Seed Resolution
- The user can specify `seed: -1` for a random seed.
- Random seeds MUST be resolved centrally inside `JobQueue` to a deterministic unsigned 32-bit integer (`random.randint(0, 2**32 - 1)`) **before** invoking the adapter.
- The resolved seed must be saved in the database record and PNG metadata so that "Reuse Settings" produces identical output.

### 4. Guaranteed Cancellation Semantics
- When a user cancels a job, its state must transition cleanly:
  $$\text{WAITING} \mid \text{PREPARING} \mid \text{LOADING\_MODEL} \mid \text{GENERATING} \longrightarrow \text{CANCELLED}$$
- A cancelled job must NEVER be logged as `FAILED` or reported as an error.
- Check `self.is_cancelled(job_id)` before heavy operations and inside diffusion step loops.

### 5. Automatic VRAM OOM Recovery
- The VRAM coordinator manages 4 strategies:
  `FULL_GPU` $\rightarrow$ `BALANCED` $\rightarrow$ `LOW_VRAM` $\rightarrow$ `CPU_OFFLOAD`
- If a `torch.cuda.OutOfMemoryError` occurs during generation:
  1. Catch the exception.
  2. Call `torch.cuda.empty_cache()` and `gc.collect()`.
  3. Step down to the next lower strategy.
  4. Automatically retry the job with the same resolved seed.
  5. Record the downgrade telemetry in `vram_strategy_used`.
  6. If all tiers are exhausted, raise `OOMRetryExhausted`.

### 6. Architecture- & Step-Aware Schedulers
- Never assume every scheduler works with every model.
- For `zimage` (SDXL-Lightning):
  - **2 steps**: Euler only (strict distillation schedule).
  - **4 steps**: Euler, DPM++ 2M Karras.
  - **8 steps**: Full high-speed suite (Euler, DPM++ 2M Karras, Euler Ancestral, DDIM).
- If an incompatible scheduler is requested, `SchedulerFactory` must log a warning and provide a **soft fallback to Euler** rather than failing the job.

### 7. IP-Adapter & Reference Images
- **Lazy Loading**: IP-Adapter weights (`ip-adapter_sdxl.safetensors`, `ip-adapter-plus_sdxl_vit-h.safetensors`, and `image_encoder`) must load lazily on demand to preserve baseline VRAM.
- **Dual References & Strength Clamping**: Support up to 2 reference images with independent modes (`style` or `subject`) and strength clamped to `[0.0, 1.5]`.
- **Cross-Attention Block Decoupling**: In `subject` mode, `down` blocks must be set to `0.0` scale so the text prompt maintains 100% authority over scene framing, camera distance (e.g. full-body vs close-up), and background, while `mid` and `up` blocks inject facial features and identity.
- **Diffusers Scale Matching**: `set_ip_adapter_scale()` must match the exact number of active IP-Adapters in the UNet. When 1 adapter is active, pass a single dict/scalar (blending 2 reference inputs if provided); when 2 adapters are active, pass a list of 2 scale configs.
- **Clean Toggle-Off Lifecycle**: Whenever `has_reference` is False, the adapter MUST invoke `ip_adapter_manager.unload_adapter(pipeline)` and ensure `unet.config.encoder_hid_dim_type` is reset to `None` so standard text-to-image inference does not expect `image_embeds`.
- **Lossless Persistence**: Always store reference configuration in embedded PNG chunk metadata and SQLite records so settings can be fully restored via "Reuse Settings".

---

## 🛠️ Development Commands

Always run commands in the project root (`f:\img-gen`):

### Environment
- Python Virtual Environment: `.venv\Scripts\python.exe`
- Package manager: `.venv\Scripts\pip.exe`
- Node runtime: Node v20+ with npm

### Running the Backend
```bash
# Run FastAPI server with auto-reload
.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 7860 --reload
```

### Running the Frontend
```bash
# Start Vite development server
npm --prefix frontend run dev
```

### Running Tests
```bash
# Run the complete test suite (28/28 tests)
.venv\Scripts\python.exe -m pytest -v

# Run a specific test file
.venv\Scripts\python.exe -m pytest tests/test_unit_config.py -v

# Run with output logging
.venv\Scripts\python.exe -m pytest -v -s
```

### Frontend Build & Typecheck
```bash
# TypeScript typecheck and production build
npm --prefix frontend run build

# ESLint check
npm --prefix frontend run lint
```

---

## 📁 Repository Map

```
f:\img-gen\
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes_generate.py       # Job submission, status, cancellation
│   │   │   ├── routes_models.py         # Model list, loading, and step-aware samplers
│   │   │   ├── routes_reference.py      # Reference uploads, IP-Adapter status & downloads
│   │   │   ├── routes_gallery.py        # Gallery retrieval, filtering, deletion
│   │   │   ├── routes_system.py         # Hardware telemetry, VRAM stats, settings
│   │   │   ├── routes_styles.py         # Style preset CRUD
│   │   │   └── routes_loras.py          # LoRA discovery and activation
│   │   ├── core/
│   │   │   ├── generation_config.py     # Pydantic GenerationConfig & LoRAConfig models
│   │   │   ├── job_queue.py             # Background worker, cancellation, OOM retry
│   │   │   ├── vram_manager.py          # VRAM strategy state machine
│   │   │   ├── exceptions.py            # Custom domain exceptions
│   │   │   └── database.py              # Async SQLite database layer
│   │   ├── models/
│   │   │   ├── registry.py              # Single-resident model registry
│   │   │   ├── base_adapter.py          # Base pipeline interface & simulation mocks
│   │   │   ├── scheduler_factory.py     # Step-aware scheduler instantiator
│   │   │   ├── ip_adapter_manager.py    # IP-Adapter weights, CLIP ViT-H encoder
│   │   │   └── zimage/                  # Z-Image Turbo adapter (SDXL-Lightning)
│   │   ├── gallery/                     # PNG metadata reading and writing
│   │   └── editing/                     # Inpainting, outpainting, 2x/4K upscaling
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── PromptBar.tsx            # Main prompt input, Magic Polish, Generate button
│   │   │   ├── ReferenceImagePanel.tsx  # Dual-mode reference image uploader & sliders
│   │   │   ├── AdvancedSettingsDrawer.tsx # Step-aware sampler selector, steps, CFG, seeds
│   │   │   ├── ImagePreview.tsx         # Real-time preview, generation progress, metadata
│   │   │   └── InpaintCanvas.tsx        # HTML5 mask painting & outpaint expansion
│   │   ├── pages/                       # GeneratePage, GalleryPage, ModelsPage, etc.
│   │   ├── services/api.ts              # Strongly typed REST client
│   │   └── types.ts                     # TypeScript interfaces matching backend models
├── tests/                               # Comprehensive test suite (28 tests)
├── config/                              # Default settings & style preset JSONs
└── scripts/                             # Diagnostics & preflight check utilities
```

---

## 🧪 Testing Guidelines

When adding features or fixing bugs:
1. **Never break existing tests**: Run `.venv\Scripts\python.exe -m pytest -v` before committing any changes.
2. **Add targeted unit tests**:
   - New config fields $\rightarrow$ `tests/test_unit_config.py`
   - Lifecycle / queue / cancellation $\rightarrow$ `tests/test_unit_cancellation_and_lifecycle.py`
   - Gallery metadata $\rightarrow$ `tests/test_unit_gallery_metadata.py`
   - Endpoints $\rightarrow$ `tests/test_api_endpoints.py`
3. **Mocking Rule**: Use `DEV_SIMULATION_MODE=true` in unit tests where actual model weights are not loaded. Ensure tests run fast (< 30 seconds total).

---

## 🎨 UI & Frontend Design Principles

1. **Aesthetics**: Glassmorphism with deep zinc backgrounds (`bg-zinc-900/80`, `backdrop-blur-md`), subtle borders (`border-white/10`), vibrant primary accents (`violet-500`/`indigo-500`), and fluid micro-interactions.
2. **User Feedback**: Provide clear toast notifications on auto-adjustments (e.g. sampler reset when lowering step count) or errors.
3. **Lossless Reuse**: Every image in the gallery must support "Reuse Settings" to restore all prompt, style, dimension, seed, sampler, and reference image parameters into the workspace.
