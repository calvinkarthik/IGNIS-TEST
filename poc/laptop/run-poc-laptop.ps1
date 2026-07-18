$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$backendRoot = Join-Path $repoRoot "backend"
$frontendRoot = Join-Path $repoRoot "frontend"
$runtimeRoot = Join-Path $repoRoot "poc\.runtime"
$venvPython = Join-Path $backendRoot ".venv\Scripts\python.exe"

New-Item -ItemType Directory -Force -Path $runtimeRoot | Out-Null
if (-not (Test-Path (Join-Path $backendRoot ".env"))) {
    Copy-Item (Join-Path $backendRoot ".env.example") (Join-Path $backendRoot ".env")
    Write-Host "Created backend\.env. Change IGNIS_DEVICE_TOKEN before the Pi run."
}

if (-not (Test-Path $venvPython)) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 -m venv (Join-Path $backendRoot ".venv")
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python -m venv (Join-Path $backendRoot ".venv")
    } else {
        throw "Python 3.11 or newer is required."
    }
    & $venvPython -m pip install -r (Join-Path $backendRoot "requirements.txt")
}

$packageManager = Get-Command pnpm.cmd -ErrorAction SilentlyContinue
if (-not $packageManager) { $packageManager = Get-Command pnpm -ErrorAction SilentlyContinue }
$usePnpm = [bool]$packageManager
if (-not $packageManager) { $packageManager = Get-Command npm.cmd -ErrorAction SilentlyContinue }
if (-not $packageManager) { $packageManager = Get-Command npm -ErrorAction SilentlyContinue }
if (-not $packageManager) { throw "Node.js 20 or newer with pnpm or npm is required." }
if (-not (Test-Path (Join-Path $frontendRoot "node_modules"))) {
    Push-Location $frontendRoot
    try {
        if ($usePnpm) {
            & $packageManager.Source install --frozen-lockfile
        } else {
            & $packageManager.Source install --no-package-lock
        }
    } finally { Pop-Location }
}

$backend = Start-Process -FilePath $venvPython `
    -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000") `
    -WorkingDirectory $backendRoot -WindowStyle Hidden -PassThru
$frontend = Start-Process -FilePath $packageManager.Source `
    -ArgumentList @("run", "dev", "--", "--host", "0.0.0.0") `
    -WorkingDirectory $frontendRoot -WindowStyle Hidden -PassThru

@{ backend = $backend.Id; frontend = $frontend.Id } |
    ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $runtimeRoot "processes.json")

Start-Sleep -Seconds 2
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -TimeoutSec 5
    Write-Host "Laptop backend: $($health.backend)"
} catch {
    Write-Host "Backend is still starting. Run it manually from backend\ if it does not come up."
}
Write-Host "Open http://localhost:5173"
Write-Host "Pi sends authenticated camera traffic to this laptop on TCP port 9001."
Write-Host "Stop both with: powershell -ExecutionPolicy Bypass -File poc\laptop\stop-poc-laptop.ps1"
