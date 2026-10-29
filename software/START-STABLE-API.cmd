@echo off
setlocal
title PUKANKOV - Stable ESP32 API
set "PATH=%LOCALAPPDATA%\Microsoft\WindowsApps;%PATH%"
cd /d "%~dp0"
python -u scripts\run_stable_api.py %*
if errorlevel 1 pause
