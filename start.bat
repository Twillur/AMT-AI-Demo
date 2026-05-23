@echo off
title AMT AI Server
cd /d "%~dp0"
echo Starting AMT AI Assistant...
echo Open: http://localhost:5000
echo.
.\venv\Scripts\python.exe app.py
pause
