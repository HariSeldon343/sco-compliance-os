# Run integration tests for SCO Compliance OS backend (Windows PowerShell).
# Conv. 46 enforcement: smoke E2E pre-tag gate.
#
# Usage:
#   ./scripts/run-integration-tests.ps1           # all tests
#   ./scripts/run-integration-tests.ps1 -k health # filter via $args
#
# Output: HTML report in build\test-report.html + console.

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $ScriptDir "..")

Write-Host "[+] Sync dev deps via uv..." -ForegroundColor Cyan
uv sync --extra dev
if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] uv sync failed" -ForegroundColor Red
    exit 1
}

# Force test env (Conv. 44 lesson 1: no zombie processes)
$env:SCO_SEAL_SCHEDULER_ENABLED = "0"
$env:SCO_AUTO_FETCH_ENABLED = "0"
$env:ANTHROPIC_API_KEY = ""
$env:LICENSE_KEY = ""

# Output dir
New-Item -ItemType Directory -Force -Path "build" | Out-Null

Write-Host "[+] Run pytest integration..." -ForegroundColor Cyan
uv run pytest tests/integration/ `
    -v `
    --tb=short `
    --asyncio-mode=auto `
    --html=build/test-report.html `
    --self-contained-html `
    $args

$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    Write-Host "[+] PASS - Report: build/test-report.html" -ForegroundColor Green
} else {
    Write-Host "[!] FAIL exit=$exitCode - Report: build/test-report.html" -ForegroundColor Red
}

exit $exitCode
