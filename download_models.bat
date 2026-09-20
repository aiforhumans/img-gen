@echo off
setlocal
cd /d "%~dp0"

echo ======================================================================
echo          ANTIGRAVITY DIFFUSION STUDIO - MODEL DOWNLOADER
echo ======================================================================

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found. Please run install.bat first.
    pause
    exit /b 1
)

set PYTHONPATH=.
.venv\Scripts\python scripts\download_models.py %*

pause
