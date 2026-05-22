# Dev launcher Windows: apre 2 terminali (backend uvicorn + frontend tauri dev).
# Conv. 44 lesson 1 enforcement: NO uvicorn --reload (socket zombie su shell ephemeral).
# Backend gira foreground in terminale dedicato, ferma con Ctrl+C.

[CmdletBinding()]
param(
    [int]$BackendPort = 7780,
    [switch]$NoFrontend
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"

Write-Host "==> sco-compliance-os dev launcher (Windows)" -ForegroundColor Cyan
Write-Host "    Backend port: $BackendPort"

# Backend in nuovo terminale PowerShell (no --reload, no run_in_background)
$backendCmd = "Set-Location '$BackendDir'; uv run uvicorn sco_compliance_os.main:app --host 127.0.0.1 --port $BackendPort"
Write-Host "==> Spawn backend in nuovo terminale" -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

if (-not $NoFrontend) {
    Start-Sleep -Seconds 2
    Write-Host "==> Spawn frontend tauri dev nel terminale corrente" -ForegroundColor Cyan
    Set-Location $FrontendDir
    pnpm tauri dev
}
