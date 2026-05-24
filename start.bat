@echo off
title AMT AI Assistant
cd /d "%~dp0"
color 0A

echo.
echo  ===================================================
echo   AMT AI Assistant
echo  ===================================================
echo.

REM ── Check venv exists ───────────────────────────────
if not exist "venv\Scripts\python.exe" (
    echo  [SETUP] No Python environment found. Creating...
    python -m venv venv
    if errorlevel 1 (
        echo  [ERROR] Python not found. Please install Python 3.10+ and retry.
        pause & exit /b 1
    )
    goto :install_deps
)

REM ── Validate venv works on THIS machine ─────────────
venv\Scripts\python.exe -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo  [SETUP] Environment needs rebuilding for this machine...
    rmdir /s /q venv >nul 2>&1
    python -m venv venv
    if errorlevel 1 (
        echo  [ERROR] Python not found. Please install Python 3.10+ and retry.
        pause & exit /b 1
    )
    goto :install_deps
)
goto :start

:install_deps
echo  [SETUP] Installing packages ^(first run takes a few minutes^)...
venv\Scripts\pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo  [ERROR] Package install failed. Check your internet connection.
    pause & exit /b 1
)
echo  [OK] Packages installed.

:start
echo  [OK] Environment ready.
echo  [OK] Server starting at http://localhost:5000
echo  [OK] Open your browser and go to localhost:5000
echo.
venv\Scripts\python.exe app.py
pause
