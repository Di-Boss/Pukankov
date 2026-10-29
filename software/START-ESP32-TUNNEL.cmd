@echo off
setlocal
cd /d "%~dp0"
python -u scripts\run_esp32_tunnel.py %*
if errorlevel 1 pause
