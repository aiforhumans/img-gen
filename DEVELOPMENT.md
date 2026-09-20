# Development Log: Antigravity Diffusion Studio (RTX 5080)

## Overview
A modern, modular AI image-generation platform inspired by Fooocus simplicity, engineered specifically for Windows 11 and NVIDIA RTX 5080 (16 GB VRAM). Features automatic model routing, local prompt intelligence with optional LM Studio integration, modular model backends (FLUX.2 Klein, Z-Image Turbo, Qwen Image, SDXL), interactive inpainting/outpainting canvas, SQLite + PNG metadata gallery, and a sleek dark desktop-style interface.

## System Specifications & Hardware
- **Operating System**: Windows 11 (64-bit)
- **GPU**: NVIDIA GeForce RTX 5080 (16,275.4 MiB VRAM, Driver: 616.92, Compute Capability 12.0 sm_120)
- **PyTorch Acceleration**: PyTorch `2.14.0+cu130` with native CUDA 13.0 / sm_120 Blackwell support
- **Host Python**: Python 3.12.10 (64-bit) in `.venv`
- **Node.js**: v24.17.0, npm 11.13.0
- **LM Studio**: Detected active at `http://127.0.0.1:1234/v1` (with Gemma 4 and DeepSeek models)

## Core Architecture & Technical Decisions
1. **NVIDIA RTX 5080 VRAM Manager**:
   - Central memory coordinator managing 4 strategy tiers: `FULL_GPU`, `BALANCED`, `LOW_VRAM`, `CPU_OFFLOAD`.
   - Single-active-model policy: Automatically unloads previous heavy models upon model switching, triggers `gc.collect()` and `torch.cuda.empty_cache()` to prevent VRAM fragmentation.
   - OOM Interceptor: Catches `torch.cuda.OutOfMemoryError`, flushes CUDA cache, steps down memory strategy, and retries safely once with user-friendly diagnostics.
2. **Auto Engine Routing System**:
   - Real-time heuristic semantic classifier that inspects user prompts for subject, photorealism cues, in-image typography/signs, instructions, and LoRA tokens.
   - Outputs a structured decision object (`task`, `category`, `text_rendering`, `editing`, `model`, `width`, `height`, `steps`, `reason`) displayed in the Generation Analysis panel.
3. **Modular Model Adapter Architecture**:
   - `BaseImageModelAdapter` standard interface implemented across:
     - `FluxAdapter`: FLUX.2 Klein 4B & 9B (general-purpose, creative landscapes, high-quality mode).
     - `ZImageAdapter`: Z-Image Turbo (8-step fast photorealism, human portraits, studio photography).
     - `QwenAdapter`: Qwen Image (in-image text rendering, typography, posters, instruction editing).
     - `SDXLAdapter`: SDXL / SDXL Turbo (legacy compatibility, older checkpoints, LoRAs).
4. **Prompt Intelligence Engine**:
   - Local rule-based analyzer detecting subject, style, lighting, depth, and negatives.
   - Optional LM Studio client (`http://127.0.0.1:1234/v1`) using `/v1/chat/completions` for deeper prompt expansion. Falls back seamlessly to the local rule-based engine when LM Studio is offline.
5. **Interactive Inpainting & Outpainting Canvas**:
   - Layered HTML5 Canvas supporting dynamic brush size, erase mask, invert mask, clear, undo/redo history, zoom, and pan.
   - Outpainting directional expansion (L/R/Top/Bottom) and instant aspect-ratio conversion presets (Square -> Portrait, Square -> Landscape, Landscape -> Phone, Portrait -> Cinema).
6. **Local Gallery & Lossless Metadata Engine**:
   - Embedded PNG chunks (`parameters` and `antigravity_metadata` JSON).
   - Local SQLite database (`outputs/gallery.db`) for indexed searching, model filtering, and favorite bookmarking.
7. **Production Windows 11 Launchers**:
   - `install.bat`: Verifies GPU, Python 3.12, installs PyTorch cu130, builds frontend.
   - `start.bat`: Binds to `127.0.0.1:7860` and opens default web browser.
   - `update.bat`: Updates dependencies and rebuilds frontend.
   - `diagnostics.bat`: Generates a technical report without leaking user prompts.

## Completed Work
- [x] Verified RTX 5080 hardware (16GB VRAM) and resolved PyTorch sm_120 compute capability using `torch==2.14.0+cu130`.
- [x] Scaffolding: folder hierarchy, default configurations, and 13 JSON style presets.
- [x] Backend Core: `VRAMManager`, `ModelRegistry`, `JobQueue`, `database.py` (aiosqlite), and `metadata_manager.py` (Pillow PNG chunks).
- [x] Model Adapters: `FluxAdapter` (4B/9B), `ZImageAdapter`, `QwenAdapter`, and `SDXLAdapter`.
- [x] Auto Engine & Prompt Intelligence: `AutoRouter`, `LocalPromptAnalyzer`, and `LMStudioClient`.
- [x] Inpainting & Outpainting engine: `inpainting.py` and `outpainting.py`.
- [x] REST API: `/api/generate`, `/api/models`, `/api/gallery`, `/api/system`, `/api/styles`, `/api/loras`.
- [x] React 19 + TypeScript + Vite frontend with modern dark design system (Inter + Outfit typography, glowing glassmorphic panels, responsive controls).
- [x] Interactive Inpaint Canvas and Outpaint controls.
- [x] Full Gallery page with metadata modal, "Reuse Prompt & Settings", and "Send to Editor".
- [x] Models Manager, LoRA Ecosystem, Settings, and System Hardware Monitor pages.
- [x] Batch Scripts: `install.bat`, `start.bat`, `update.bat`, `diagnostics.bat`, and `download_models.bat`.
- [x] Model Downloader: Added `backend/app/models/downloader.py`, `scripts/download_models.py`, download API endpoints (`/api/models/{id}/download`, `/download-status`, `/validate`), and UI download progress bars in `ModelsPage.tsx`.
- [x] Full automated test suite (7/7 tests passing in `pytest`).
- [x] End-to-end generation verification with the prompt from user instructions.

## Verified Test Runs
- `tests/test_backend_core.py`: All unit tests passed (AutoRouter, VRAM strategy escalation, adapters, metadata roundtrip, SQLite gallery).
- `tests/test_api_endpoints.py`: All REST API integration tests passed.
- End-to-end prompt test (`scripts/test_generation.py`):
  - Prompt: *"A cinematic photograph of an abandoned 1980s arcade at night, wet floor, neon signs saying ARCADE 84."*
  - Automatically routed to: **Qwen Image** (Reason: Detected signs/quotes in prompt).
  - Generated PNG output with embedded metadata saved to `outputs/2026-09-20/`.
  - Registered in SQLite gallery database.

## Launch Instructions
1. Double-click `start.bat` (or run `.venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 7860`).
2. The web interface opens automatically at `http://127.0.0.1:7860`.
