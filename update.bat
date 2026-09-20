@echo off
setlocal

echo ======================================================================
echo          UPDATING ANTIGRAVITY DIFFUSION STUDIO
echo ======================================================================

echo [1/3] Updating Backend Dependencies...
if exist .venv\Scripts\uv.exe (
    .venv\Scripts\uv pip install -U -r backend\requirements.txt
) else (
    .venv\Scripts\pip install -U -r backend\requirements.txt
)

echo [2/3] Updating and Rebuilding Frontend...
cd frontend
call npm install
call npm run build
cd ..

echo [3/3] Verifying System Diagnostics...
set PYTHONPATH=.
.venv\Scripts\python scripts\test_system.py

echo ======================================================================
echo Update complete!
echo ======================================================================
pause
