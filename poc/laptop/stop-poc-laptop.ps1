$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$stateFile = Join-Path $repoRoot "poc\.runtime\processes.json"
if (-not (Test-Path $stateFile)) {
    Write-Host "No POC process file was found."
    exit 0
}
$state = Get-Content -Raw $stateFile | ConvertFrom-Json
foreach ($processId in @($state.backend, $state.frontend)) {
    if ($processId -and (Get-Process -Id $processId -ErrorAction SilentlyContinue)) {
        Stop-Process -Id $processId
    }
}
Remove-Item -LiteralPath $stateFile
Write-Host "IGNIS laptop POC stopped."
