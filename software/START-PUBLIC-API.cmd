@echo off
setlocal
cd /d "%~dp0"
python scripts\run_public_api.py %*
if errorlevel 1 (
  echo Public API startup failed. Read the error above.
  pause
)
