# PyInstaller orchestrator per Windows (PowerShell).
# Setup venv -> install deps -> run pyinstaller -> copy a frontend sidecar path.
# Conv. 45 lesson 1 enforcement: triple naming x86_64-pc-windows-msvc per Tauri sidecar.

[CmdletBinding()]
param(
    [switch]$Clean,
    [switch]$NoVerify
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendBinDir = Join-Path $ProjectRoot "frontend\src-tauri\binaries"
$Spec = "sco-compliance-os-backend-windows.spec"
$SidecarSrc = Join-Path $BackendDir "dist\sco-compliance-os-backend.exe"
$SidecarDest = Join-Path $FrontendBinDir "sco-compliance-os-backend-x86_64-pc-windows-msvc.exe"

Write-Host "==> sco-compliance-os build-backend (Windows)" -ForegroundColor Cyan
Write-Host "    Project root: $ProjectRoot"
Write-Host "    Spec:         $Spec"

Push-Location $BackendDir
try {
    if ($Clean) {
        Write-Host "==> Clean dist + build dirs" -ForegroundColor Yellow
        Remove-Item -Recurse -Force "dist", "build" -ErrorAction SilentlyContinue
    }

    # Verifica uv installato
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        throw "uv not found. Install: irm https://astral.sh/uv/install.ps1 | iex"
    }

    Write-Host "==> uv sync" -ForegroundColor Cyan
    uv sync
    if ($LASTEXITCODE -ne 0) { throw "uv sync failed" }

    Write-Host "==> pyinstaller $Spec" -ForegroundColor Cyan
    uv run pyinstaller $Spec --noconfirm
    if ($LASTEXITCODE -ne 0) { throw "pyinstaller failed" }

    if (-not (Test-Path $SidecarSrc)) {
        throw "Sidecar binary not produced at: $SidecarSrc"
    }

    Write-Host "==> Copy sidecar to frontend binaries" -ForegroundColor Cyan
    New-Item -ItemType Directory -Path $FrontendBinDir -Force | Out-Null
    Copy-Item $SidecarSrc $SidecarDest -Force
    Write-Host "    Copied to: $SidecarDest"

    if (-not $NoVerify) {
        Write-Host "==> Verify sidecar runs (Conv. 44 lesson 3 smoke)" -ForegroundColor Cyan
        # FIX 28/05 (CO#6): il backend NON ha un handler --help/--version, quindi
        # con `--help` avvia direttamente uvicorn e resta in ascolto per sempre.
        # Il vecchio pattern `Start-Process -Wait` bloccava lo script all'infinito
        # (+ lasciava zombie sidecar dopo kill incompleto, incidenti 27/05 PID
        # 39344 e 6768). Nuovo pattern: avvia senza -Wait, attendi max 8s. Se il
        # processo e' ancora vivo = uvicorn partito correttamente (binario sano)
        # -> killalo + figli e considera OK. Se esce prima con codice != 0/2 =
        # errore reale (hidden import mancante).
        $verifyProc = Start-Process -FilePath $SidecarDest -ArgumentList "--help" -NoNewWindow -PassThru -ErrorAction SilentlyContinue
        $exited = $verifyProc.WaitForExit(8000)
        if (-not $exited) {
            Write-Host "    Sidecar avviato (uvicorn in ascolto, nessun handler --help) -> binario OK." -ForegroundColor Green
            # Kill figli orfani prima del padre (uvicorn worker / reloader)
            Get-CimInstance Win32_Process -Filter "ParentProcessId = $($verifyProc.Id)" -ErrorAction SilentlyContinue |
                ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
            Stop-Process -Id $verifyProc.Id -Force -ErrorAction SilentlyContinue
        } elseif ($verifyProc.ExitCode -ne 0 -and $verifyProc.ExitCode -ne 2) {
            Write-Warning "Sidecar exit code $($verifyProc.ExitCode). Verifica hidden imports in $Spec."
        } else {
            Write-Host "    Sidecar OK (exit $($verifyProc.ExitCode))." -ForegroundColor Green
        }
    }

    Write-Host "==> Build backend DONE" -ForegroundColor Green
} finally {
    Pop-Location
}
