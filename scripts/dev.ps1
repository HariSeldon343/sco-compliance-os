# =========================================================================
# SCO Compliance OS — Script di avvio dev parallelo
# Lancia backend FastAPI (uvicorn) + frontend Tauri/Vite in due terminali.
# =========================================================================
# Uso:
#   powershell -ExecutionPolicy Bypass -File scripts\dev.ps1
# oppure:
#   pnpm dev:all
# =========================================================================

$ErrorActionPreference = "Stop"

# Risolvi root del repo (parent di scripts/)
$RepoRoot = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $RepoRoot "backend"
$FrontendDir = Join-Path $RepoRoot "frontend"

Write-Host "[sco-compliance-os] dev launcher" -ForegroundColor Cyan
Write-Host "  repo root  = $RepoRoot"
Write-Host "  backend    = $BackendDir"
Write-Host "  frontend   = $FrontendDir"
Write-Host ""

# Verifica prerequisiti minimi
if (-not (Test-Path $BackendDir)) {
    Write-Error "Directory backend non trovata: $BackendDir"
    exit 1
}
if (-not (Test-Path $FrontendDir)) {
    Write-Error "Directory frontend non trovata: $FrontendDir"
    exit 1
}

# Comando backend (sidecar Python FastAPI tramite uv)
$BackendCmd = "Set-Location '$BackendDir'; uv run uvicorn sco_compliance_os.main:app --host 127.0.0.1 --port 7800 --reload"

# Comando frontend (Tauri dev tramite pnpm filter)
$FrontendCmd = "Set-Location '$RepoRoot'; pnpm --filter frontend tauri dev"

Write-Host "Apro 2 finestre PowerShell:" -ForegroundColor Yellow
Write-Host "  1) backend uvicorn su 127.0.0.1:7800"
Write-Host "  2) frontend tauri dev"
Write-Host ""

Start-Process powershell -ArgumentList "-NoExit", "-Command", $BackendCmd
Start-Sleep -Seconds 2
Start-Process powershell -ArgumentList "-NoExit", "-Command", $FrontendCmd

Write-Host "Lanciati. Chiudi le finestre per terminare i processi." -ForegroundColor Green
