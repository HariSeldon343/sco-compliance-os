#!/usr/bin/env bash
# ============================================================================
# dev.sh — launcher development backend SCO Compliance OS (Mac/Linux)
# ----------------------------------------------------------------------------
# Uso:
#     cd /path/to/sco-compliance-os/backend
#     ./scripts/dev.sh
#
# NOTA Conv. 44 lesson 1: ESEGUI SOLO da terminale persistente (bash/zsh
# interattivo). NON da shell ephemeral di tool LLM in background — produce
# socket zombie e ConnectionRefused successivi.
# ============================================================================

set -euo pipefail

# Posizionati nella root backend (parent di scripts/)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_ROOT="$( dirname "$SCRIPT_DIR" )"
cd "$BACKEND_ROOT"

echo "[dev.sh] Backend root: $BACKEND_ROOT"
echo "[dev.sh] Avvio uvicorn con --reload (dev mode)"

# Verifica .env (warning, non blocca)
if [ ! -f ".env" ]; then
    echo "[dev.sh] WARN: file .env mancante. Copialo da .env.example."
fi

# Avvia uvicorn auto-reload. PERSISTENTE in foreground.
exec uv run uvicorn sco_compliance_os.main:app \
    --host 127.0.0.1 \
    --port 7800 \
    --reload \
    --reload-dir sco_compliance_os \
    --log-level info
