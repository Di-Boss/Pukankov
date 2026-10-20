@echo off
setlocal
cd /d "%~dp0"
if not exist "dist\index.html" (
  echo Missing frontend build. Run start.ps1 for initial setup.
  pause
  exit /b 1
)
cd backend
python -m alembic upgrade head
if errorlevel 1 goto failed
python -m app.seed
if errorlevel 1 goto failed
echo Open http://127.0.0.1:8000/ and keep this window open.
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
if errorlevel 1 goto failed
exit /b 0
:failed
echo Startup failed. Read the error above.
pause
exit /b 1
