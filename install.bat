@echo off
setlocal enabledelayedexpansion

echo ======================================================================
echo          ANTIGRAVITY DIFFUSION STUDIO - INSTALLER (WINDOWS 11)
echo ======================================================================

echo [1/5] Checking NVIDIA GPU and CUDA Driver...
where nvidia-smi >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [WARNING] nvidia-smi not found. Ensure NVIDIA Graphics Drivers are installed.
) else (
    nvidia-smi | findstr /i "5080 5090 RTX GeForce"
    echo [OK] NVIDIA GPU detected.
)

echo [2/5] Checking Python 3.12 / uv environment...
where uv >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [OK] uv package manager detected.
    if not exist .venv (
        echo Creating virtual environment with Python 3.12...
        uv venv .venv --python 3.12
    )
) else (
    if not exist .venv (
        echo Creating virtual environment with Python...
        py -3.12 -m venv .venv
    )
)

if not exist .venv (
    echo [ERROR] Failed to create .venv virtual environment. Please install Python 3.12.
    pause
    exit /b 1
)

echo [3/5] Installing Backend PyTorch (Blackwell / CUDA acceleration)...
if exist .venv\Scripts\uv.exe (
    .venv\Scripts\uv pip install --index-url https://download.pytorch.org/whl/cu130 torch torchvision
    if !ERRORLEVEL! neq 0 (
        echo [INFO] Falling back to PyTorch CUDA 12.6...
        .venv\Scripts\uv pip install --index-url https://download.pytorch.org/whl/cu126 torch torchvision
    )
    .venv\Scripts\uv pip install -r backend\requirements.txt
) else (
    .venv\Scripts\pip install --index-url https://download.pytorch.org/whl/cu130 torch torchvision
    if !ERRORLEVEL! neq 0 (
        echo [INFO] Falling back to PyTorch CUDA 12.6...
        .venv\Scripts\pip install --index-url https://download.pytorch.org/whl/cu126 torch torchvision
    )
    .venv\Scripts\pip install -r backend\requirements.txt
)

echo [4/5] Building Frontend Web Application...
where npm >nul 2>&1
if %ERRORLEVEL% equ 0 (
    cd frontend
    call npm install
    call npm run build
    cd ..
    echo [OK] Frontend built successfully.
) else (
    echo [WARNING] npm not found in PATH. Install Node.js v20+ to compile the frontend.
)

echo [5/5] Running System Preflight & Diagnostics...
set PYTHONPATH=.
.venv\Scripts\python.exe scripts\preflight_check.py

echo ======================================================================
echo Installation complete! Run start.bat to launch the application.
echo ======================================================================
pause
