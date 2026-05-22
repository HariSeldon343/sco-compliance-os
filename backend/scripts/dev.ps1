# ============================================================================
# dev.ps1 — launcher development backend SCO Compliance OS (Windows PowerShell)
# ----------------------------------------------------------------------------
# Uso:
#     cd C:\Users\aoedo\Progetti\sco-compliance-os\backend
#     .\scripts\dev.ps1
#
# NOTA Conv. 44 lesson 1: ESEGUI SOLO da terminale PowerShell PERSISTENTE
# (apri PowerShell manualmente). NON eseguire questo script da shell ephemeral
# (es. shell di Claude Code in background) — produce socket zombie su porta.
# ============================================================================

$ErrorActionPreference = "Stop"

# Posizionati nella root backend (parent di scripts/)
$BackendRoot = Split-Path -Parent $PSScriptRoot
Set-Location $BackendRoot

Write-Host "[dev.ps1] Backend root: $BackendRoot" -ForegroundColor Cyan
Write-Host "[dev.ps1] Avvio uvicorn con --reload (dev mode)" -ForegroundColor Cyan

# Verifica esistenza .env (warning, non blocca)
if (-not (Test-Path ".\.env")) {
    Write-Host "[dev.ps1] WARN: file .env mancante. Copialo da .env.example." -ForegroundColor Yellow
}

# Avvia uvicorn con auto-reload. PERSISTENTE in foreground.
uv run uvicorn sco_compliance_os.main:app `
    --host 127.0.0.1 `
    --port 7800 `
    --reload `
    --reload-dir sco_compliance_os `
    --log-level info
