# Conversation Viewer starter (PowerShell)
# Avvia il mini-server + apre il browser su localhost:9000.
$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
$projectRoot = Resolve-Path (Join-Path $here "..\..")
$venvPy = Join-Path $projectRoot "backend\.venv\Scripts\python.exe"

if (-not (Test-Path $venvPy)) {
    Write-Host "venv backend non trovato: $venvPy" -ForegroundColor Yellow
    Write-Host "Uso 'python' di sistema (richiede fastapi + uvicorn installati)." -ForegroundColor Yellow
    $venvPy = "python"
}

Write-Host "Conversation Viewer jarvis <-> codex" -ForegroundColor Cyan
Write-Host "  Apro http://localhost:9000 nel browser..." -ForegroundColor Cyan
Start-Process "http://localhost:9000"
& $venvPy (Join-Path $here "server.py")
