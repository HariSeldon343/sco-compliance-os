#!/bin/bash
# Run integration tests for SCO Compliance OS backend.
# Conv. 46 enforcement: smoke E2E pre-tag gate.
#
# Usage:
#   ./scripts/run-integration-tests.sh           # all tests
#   ./scripts/run-integration-tests.sh -k health # filter
#
# Output: HTML report in build/test-report.html + console.

set -euo pipefail

# Move to backend root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}/.."

# Ensure deps installed
echo "[+] Sync dev deps via uv..."
uv sync --extra dev

# Force test env (Conv. 44 lesson 1: no zombie processes)
export SCO_SEAL_SCHEDULER_ENABLED=0
export SCO_AUTO_FETCH_ENABLED=0
export ANTHROPIC_API_KEY=""
export LICENSE_KEY=""

# Output dir
mkdir -p build

# Run pytest
echo "[+] Run pytest integration..."
uv run pytest tests/integration/ \
    -v \
    --tb=short \
    --asyncio-mode=auto \
    --html=build/test-report.html \
    --self-contained-html \
    "$@"

echo "[+] Done. Report: build/test-report.html"
