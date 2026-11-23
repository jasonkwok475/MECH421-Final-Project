# Starts the backend (FastAPI) and the frontend (Vite) for local development on Windows.
# Usage (from the repo root):  .\scripts\dev.ps1
# If PowerShell blocks scripts:  powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "software\backend"
$frontend = Join-Path $root "software\frontend"

# --- backend -----------------------------------------------------------------
$venvPy = Join-Path $backend ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Host "Creating Python virtual environment..."
    python -m venv (Join-Path $backend ".venv")
    & $venvPy -m pip install --upgrade pip
    & $venvPy -m pip install -r (Join-Path $backend "requirements-dev.txt")
}
Start-Process powershell -ArgumentList "-NoExit", "-Command",
    "Set-Location '$backend'; & '$venvPy' -m uvicorn app.main:app --reload --port 8000"

# --- frontend ----------------------------------------------------------------
if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    Write-Host "Installing frontend dependencies..."
    Push-Location $frontend; npm install; Pop-Location
}
Start-Process powershell -ArgumentList "-NoExit", "-Command",
    "Set-Location '$frontend'; npm run dev"

Start-Sleep -Seconds 4
Start-Process "http://localhost:5173"
Write-Host "Backend: http://127.0.0.1:8000/docs   GUI: http://localhost:5173"
