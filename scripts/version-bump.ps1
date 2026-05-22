# Version bump coerente in 4 punti (Conv. 47 BUMP VERSION grep enforcement).
# Bumpa:
#   1. frontend/package.json
#   2. frontend/src-tauri/Cargo.toml
#   3. frontend/src-tauri/tauri.conf.json
#   4. backend/sco_compliance_os/__init__.py
# POI esegue grep verifica zero residui versione vecchia.

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$NewVersion,

    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

# Valida formato semver
if ($NewVersion -notmatch "^\d+\.\d+\.\d+$") {
    throw "Versione invalida: $NewVersion. Atteso formato semver X.Y.Z (es. 0.1.1)"
}

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$PackageJson = Join-Path $ProjectRoot "frontend\package.json"
$CargoToml = Join-Path $ProjectRoot "frontend\src-tauri\Cargo.toml"
$TauriConf = Join-Path $ProjectRoot "frontend\src-tauri\tauri.conf.json"
$BackendInit = Join-Path $ProjectRoot "backend\sco_compliance_os\__init__.py"

Write-Host "==> Version bump -> $NewVersion" -ForegroundColor Cyan
Write-Host "    Project root: $ProjectRoot"

# Read current version da package.json
$pkg = Get-Content $PackageJson -Raw | ConvertFrom-Json
$OldVersion = $pkg.version
Write-Host "    Current:      $OldVersion"

if ($OldVersion -eq $NewVersion) {
    Write-Warning "Version invariata, exit."
    exit 0
}

if ($DryRun) {
    Write-Host "DRY-RUN: no actual modifications" -ForegroundColor Yellow
    exit 0
}

# 1. frontend/package.json
Write-Host "==> Bump $PackageJson" -ForegroundColor Cyan
$pkg.version = $NewVersion
$pkg | ConvertTo-Json -Depth 100 | Set-Content $PackageJson -Encoding utf8

# 2. frontend/src-tauri/Cargo.toml
Write-Host "==> Bump $CargoToml" -ForegroundColor Cyan
$cargoContent = Get-Content $CargoToml -Raw
$cargoContent = $cargoContent -replace '(?m)^version\s*=\s*"[^"]+"', "version = `"$NewVersion`""
Set-Content $CargoToml $cargoContent -Encoding utf8 -NoNewline

# 3. frontend/src-tauri/tauri.conf.json
Write-Host "==> Bump $TauriConf" -ForegroundColor Cyan
$tauri = Get-Content $TauriConf -Raw | ConvertFrom-Json
$tauri.version = $NewVersion
$tauri | ConvertTo-Json -Depth 100 | Set-Content $TauriConf -Encoding utf8

# 4. backend/sco_compliance_os/__init__.py
Write-Host "==> Bump $BackendInit" -ForegroundColor Cyan
if (Test-Path $BackendInit) {
    $initContent = Get-Content $BackendInit -Raw
    if ($initContent -match '__version__') {
        $initContent = $initContent -replace '__version__\s*=\s*"[^"]+"', "__version__ = `"$NewVersion`""
    } else {
        $initContent = "$initContent`n__version__ = `"$NewVersion`"`n"
    }
    Set-Content $BackendInit $initContent -Encoding utf8 -NoNewline
}

# Conv. 47 enforcement: grep verifica zero residui versione vecchia
Write-Host "==> Conv. 47 grep verifica zero residui $OldVersion..." -ForegroundColor Cyan
$targets = @($PackageJson, $CargoToml, $TauriConf)
if (Test-Path $BackendInit) { $targets += $BackendInit }

$residui = 0
foreach ($target in $targets) {
    $matches = Select-String -Path $target -Pattern ([regex]::Escape($OldVersion)) -SimpleMatch
    if ($matches) {
        foreach ($m in $matches) {
            Write-Warning "Residuo $OldVersion in ${target}:$($m.LineNumber): $($m.Line.Trim())"
            $residui++
        }
    }
}

if ($residui -gt 0) {
    throw "Conv. 47 FAILED: $residui residui di versione $OldVersion. Fix manualmente prima del commit."
}

Write-Host "==> Bump DONE. Conv. 47 grep PASS (zero residui)." -ForegroundColor Green
Write-Host ""
Write-Host "Prossimi step (Conv. 46 SMOKE PRIMA DEL TAG enforcement):"
Write-Host "  1. Smoke E2E locale fresh install (MSI/DMG/AppImage)"
Write-Host "  2. git diff      (verifica delta atteso)"
Write-Host "  3. git commit -am 'chore: bump version v$NewVersion'"
Write-Host "  4. git tag v$NewVersion"
Write-Host "  5. git push --tags  (trigger release workflow)"
