@echo off
title Staunt Browser Ultra Launcher
cd /d "%~dp0"
echo Launching Staunt Browser Ultra...
start "" "%~dp0node_modules\electron\dist\electron.exe" .
exit
