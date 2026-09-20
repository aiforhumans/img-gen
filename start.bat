@echo off
setlocal
cd /d "%~dp0"
title Antigravity Diffusion Studio (RTX 5080)

if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Virtual environment not found. Running installer first...
    call install.bat
)

set PYTHONPATH=.
set PYTHONUNBUFFERED=1
set HOST=127.0.0.1
set PORT=7860

:: Check and free port if already occupied
for /f "tokens=5" %%a in ('netstat -aon ^| findstr /r /c:":%PORT% *LISTENING"') do (
    echo [INFO] Port %PORT% is in use by PID %%a. Terminating previous instance...
    taskkill /F /PID %%a >nul 2>&1
    timeout /t 1 /nobreak >nul
)

:: Run preflight diagnostics displaying all hardware, models, and runtime status
.venv\Scripts\python.exe scripts\preflight_check.py

:: Launch browser in background once server has initialized
start /b cmd /c "ping 127.0.0.1 -n 3 >nul & start http://%HOST%:%PORT%"

:: Launch FastAPI application with vivid colorized output and clean real-time streaming (no access spam)
.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host %HOST% --port %PORT% --log-level info --no-access-log --use-colors

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Application exited with error code %ERRORLEVEL%.
)

pause
