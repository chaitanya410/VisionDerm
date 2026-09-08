# Starts the FastAPI backend and the Vite frontend together (Windows / PowerShell).
# Usage:  ./run.ps1
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$venvPy = Join-Path $backend ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPy)) {
  Write-Host "Creating backend virtualenv..." -ForegroundColor Cyan
  python -m venv (Join-Path $backend ".venv")
  & $venvPy -m pip install --upgrade pip
  & $venvPy -m pip install -r (Join-Path $backend "requirements.txt")
}

$samples = Join-Path $backend "data\samples"
if (-not (Get-ChildItem -Path $samples -Filter *.jpg -ErrorAction SilentlyContinue)) {
  Write-Host "Fetching sample images..." -ForegroundColor Cyan
  Push-Location $backend; & $venvPy "data\fetch_samples.py"; Pop-Location
}

if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
  Write-Host "Installing frontend dependencies..." -ForegroundColor Cyan
  Push-Location $frontend; npm install; Pop-Location
}

Write-Host "Starting backend on http://localhost:8000 ..." -ForegroundColor Green
$be = Start-Process -PassThru -WorkingDirectory $backend $venvPy `
  -ArgumentList "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"

Write-Host "Starting frontend on http://localhost:5173 ..." -ForegroundColor Green
# Must be npm.cmd, not "npm": PowerShell resolves bare "npm" to the extensionless
# Unix shell script in nodejs/, which ShellExecute opens in an editor instead of running.
$fe = Start-Process -PassThru -WorkingDirectory $frontend "npm.cmd" -ArgumentList "run", "dev"

Write-Host "`nBoth running. Press Ctrl+C to stop." -ForegroundColor Yellow
try {
  Wait-Process -Id $be.Id, $fe.Id
} finally {
  $be, $fe | ForEach-Object { if (-not $_.HasExited) { Stop-Process -Id $_.Id -Force } }
}
