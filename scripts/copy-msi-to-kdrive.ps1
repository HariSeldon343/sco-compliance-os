# SCO Compliance OS — copia MSI bundle al doppio percorso kDrive Copilot Installer.
#
# Eseguito automaticamente dopo `pnpm build:msi` per propagare il MSI ai
# percorsi shared kDrive (sync multi-PC). Pattern Conv. 46 (dual artifact path)
# + Conv. 45 (PyInstaller cross-platform).
#
# Path target hardcoded per richiesta utente esplicita 24/05/2026:
#   C:\Users\aoedo\kDrive\Copilot Installer\
#
# Manteniamo anche il path originale Tauri:
#   frontend\src-tauri\target\release\bundle\msi\

$ErrorActionPreference = "Stop"

$BundleDir = Join-Path $PSScriptRoot "..\frontend\src-tauri\target\release\bundle\msi"
$TargetDir = "C:\Users\aoedo\kDrive\Copilot Installer"

if (-not (Test-Path $BundleDir)) {
    Write-Host "==> ERRORE: bundle dir non trovata: $BundleDir" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $TargetDir)) {
    Write-Host "==> Creo target dir: $TargetDir"
    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
}

# Trova l'MSI piu' recente (filename pattern: "SCO Compliance OS_X.Y.Z_x64_it-IT.msi")
$LatestMsi = Get-ChildItem -Path $BundleDir -Filter "SCO Compliance OS_*_x64_it-IT.msi" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $LatestMsi) {
    Write-Host "==> ERRORE: nessun MSI trovato in $BundleDir" -ForegroundColor Red
    exit 1
}

$DestFile = Join-Path $TargetDir $LatestMsi.Name

Write-Host "==> Copio: $($LatestMsi.Name)"
Write-Host "    da: $($LatestMsi.FullName)"
Write-Host "    a:  $DestFile"

Copy-Item -Path $LatestMsi.FullName -Destination $DestFile -Force

$DestSize = (Get-Item $DestFile).Length
$DestSizeMb = [math]::Round($DestSize / 1MB, 1)

Write-Host "==> Copia OK ($DestSizeMb MB)" -ForegroundColor Green
Write-Host "==> Doppio percorso MSI disponibile:"
Write-Host "    1. $($LatestMsi.FullName)"
Write-Host "    2. $DestFile"
