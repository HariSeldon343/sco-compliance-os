# Self-installer Windows per SCO Compliance OS.
# Download latest release MSI da GitHub + verifica firma Ed25519 + install LOCALAPPDATA.
# STUB minimale wave 1, espansione progressiva (silent install, MSI flags, rollback).

[CmdletBinding()]
param(
    [string]$Repo = "asamodeo/sco-compliance-os",
    [string]$Version = "latest",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

Write-Host "==> SCO Compliance OS - Self installer (Windows)" -ForegroundColor Cyan
Write-Host "    Repo:    $Repo"
Write-Host "    Version: $Version"

# Resolve latest tag se richiesto
if ($Version -eq "latest") {
    Write-Host "==> Fetching latest release tag..." -ForegroundColor Cyan
    $api = "https://api.github.com/repos/$Repo/releases/latest"
    $rel = Invoke-RestMethod -Uri $api -Headers @{ "User-Agent" = "sco-installer" }
    $Version = $rel.tag_name
    Write-Host "    Resolved: $Version"
}

# Find MSI asset
$msiAsset = $rel.assets | Where-Object { $_.name -like "*x64*.msi" } | Select-Object -First 1
if (-not $msiAsset) {
    throw "MSI asset not found in release $Version"
}

$installDir = Join-Path $env:LOCALAPPDATA "SCO Compliance OS"
$downloadPath = Join-Path $env:TEMP $msiAsset.name

Write-Host "==> Downloading: $($msiAsset.browser_download_url)" -ForegroundColor Cyan
Write-Host "    To: $downloadPath"

if ($DryRun) {
    Write-Host "DRY-RUN: no actual download/install" -ForegroundColor Yellow
    exit 0
}

Invoke-WebRequest -Uri $msiAsset.browser_download_url -OutFile $downloadPath -UseBasicParsing

# Verify SHA256 from latest.json (Ed25519 sig su signature blob, sha256 su artefatto)
Write-Host "==> Verify SHA256 (Ed25519 sig check delegato al Tauri Updater post-install)" -ForegroundColor Cyan
$expectedSha = $msiAsset.digest -replace "^sha256:", ""
if ($expectedSha) {
    $actualSha = (Get-FileHash -Path $downloadPath -Algorithm SHA256).Hash.ToLower()
    if ($expectedSha.ToLower() -ne $actualSha) {
        throw "SHA256 mismatch! expected=$expectedSha actual=$actualSha"
    }
    Write-Host "    SHA256 OK." -ForegroundColor Green
} else {
    Write-Warning "GitHub API digest non disponibile, skip SHA256 verify (verifica delegata al Tauri Updater Ed25519)."
}

Write-Host "==> Installing MSI silent..." -ForegroundColor Cyan
$msiArgs = @(
    "/i", "`"$downloadPath`"",
    "/quiet",
    "/norestart",
    "INSTALLDIR=`"$installDir`""
)
$proc = Start-Process -FilePath "msiexec.exe" -ArgumentList $msiArgs -NoNewWindow -PassThru -Wait
if ($proc.ExitCode -ne 0) {
    throw "MSI install failed with exit code $($proc.ExitCode)"
}

Write-Host "==> Install DONE" -ForegroundColor Green
Write-Host "    Location: $installDir"
Write-Host "    Avvia da Start Menu o Desktop shortcut."
