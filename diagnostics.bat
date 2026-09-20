@echo off
setlocal
cd /d "%~dp0"

echo ======================================================================
echo          ANTIGRAVITY DIFFUSION STUDIO - SYSTEM DIAGNOSTICS
echo ======================================================================

set PYTHONPATH=.
if exist .venv\Scripts\python.exe (
    .venv\Scripts\python scripts\test_system.py
) else (
    python scripts\test_system.py
)

pause
