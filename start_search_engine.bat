@echo off
title VASTUDA Search Engine & Discovery Platform
echo ========================================================
echo   Starting VASTUDA Independent AI Discovery Engine...
echo ========================================================
echo.

cd /d "%~dp0"

:: Start browser after 2 seconds
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:5000"

:: Launch the Flask server
python -m search_engine.server

pause
