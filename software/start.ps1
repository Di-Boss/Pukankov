$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
Write-Host 'PUKANKOV - local demo setup' -ForegroundColor Yellow
if (-not (Test-Path -LiteralPath 'node_modules')) {
    npm ci --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) { throw 'npm install failed.' }
}
python -m pip install -r backend/requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
npm run build
if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
Set-Location -LiteralPath (Join-Path $PSScriptRoot 'backend')
python -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw 'Database migration failed.' }
python -m app.seed
if ($LASTEXITCODE -ne 0) { throw 'Demo seed failed.' }
Write-Host 'Open http://127.0.0.1:8000 - stop with Ctrl+C' -ForegroundColor Yellow
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
