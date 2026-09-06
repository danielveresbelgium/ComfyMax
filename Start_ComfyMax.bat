@echo off
setlocal
title ComfyMax

cd /d "%~dp0"

echo ==========================================
echo            ComfyMax Startup
echo ==========================================
echo.

REM --- Select Python: prefer local .venv, otherwise use Python on PATH ---
if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] Python was not found.
        echo Install Python or create a .venv in this folder first.
        pause
        exit /b 1
    )
    set "PYTHON=python"
)

REM --- Check whether App.py exists ---
if not exist "App.py" (
    echo [ERROR] App.py was not found in:
    echo %CD%
    echo.
    echo Place this BAT file in the main ComfyMax folder.
    pause
    exit /b 1
)

REM --- Warn if LM Studio is not listening on port 1234 ---
powershell -NoProfile -Command ^
  "if (-not (Test-NetConnection 127.0.0.1 -Port 1234 -InformationLevel Quiet)) { exit 1 }"
if errorlevel 1 (
    echo [WARNING] The LM Studio API does not appear to be running on port 1234.
    echo Start the LM Studio server if you want to use prompt generation.
    echo.
)

REM --- Warn if ComfyUI is not listening on port 8188 ---
powershell -NoProfile -Command ^
  "if (-not (Test-NetConnection 127.0.0.1 -Port 8188 -InformationLevel Quiet)) { exit 1 }"
if errorlevel 1 (
    echo [WARNING] ComfyUI does not appear to be running on port 8188.
    echo Start ComfyUI if you want to render workflows.
    echo.
)

echo [OK] Starting ComfyMax...
echo.
"%PYTHON%" -m streamlit run App.py

echo.
echo ComfyMax has been closed.
pause
endlocal
