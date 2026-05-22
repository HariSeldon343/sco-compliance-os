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
        $verifyProc = Start-Process -FilePath $SidecarDest -ArgumentList "--help" -NoNewWindow -PassThru -Wait -ErrorAction SilentlyContinue
        if ($verifyProc.ExitCode -ne 0 -and $verifyProc.ExitCode -ne 2) {
            Write-Warning "Sidecar exit code $($verifyProc.ExitCode). Verifica hidden imports in $Spec."
        } else {
            Write-Host "    Sidecar OK." -ForegroundColor Green
        }
    }

    Write-Host "==> Build backend DONE" -ForegroundColor Green
} finally {
    Pop-Location
}
