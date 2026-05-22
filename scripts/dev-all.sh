#!/usr/bin/env bash
# Dev launcher macOS/Linux: backend foreground (terminale nuovo) + frontend tauri dev.
# Conv. 44 lesson 1 enforcement: NO uvicorn --reload (socket zombie su shell ephemeral).

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"
FRONTEND_DIR="${PROJECT_ROOT}/frontend"

BACKEND_PORT="${BACKEND_PORT:-7780}"
NO_FRONTEND=0
for arg in "$@"; do
    case "${arg}" in
        --no-frontend) NO_FRONTEND=1 ;;
    esac
done

echo "==> sco-compliance-os dev launcher ($(uname -s))"
echo "    Backend port: ${BACKEND_PORT}"

OS="$(uname -s)"
case "${OS}" in
    Darwin)
        # macOS: apri Terminal.app con backend, frontend nel terminale corrente
        osascript -e "tell application \"Terminal\" to do script \"cd '${BACKEND_DIR}' && uv run uvicorn sco_compliance_os.main:app --host 127.0.0.1 --port ${BACKEND_PORT}\""
        ;;
    Linux)
        # Linux: gnome-terminal, fallback xterm
        if command -v gnome-terminal >/dev/null 2>&1; then
            gnome-terminal -- bash -c "cd '${BACKEND_DIR}' && uv run uvicorn sco_compliance_os.main:app --host 127.0.0.1 --port ${BACKEND_PORT}; exec bash"
        elif command -v xterm >/dev/null 2>&1; then
            xterm -e "cd '${BACKEND_DIR}' && uv run uvicorn sco_compliance_os.main:app --host 127.0.0.1 --port ${BACKEND_PORT}; bash" &
        else
            echo "WARNING: nessun terminale grafico trovato (gnome-terminal/xterm). Lancia backend manualmente." >&2
            echo "  cd ${BACKEND_DIR} && uv run uvicorn sco_compliance_os.main:app --host 127.0.0.1 --port ${BACKEND_PORT}"
        fi
        ;;
esac

if [ "${NO_FRONTEND}" -eq 0 ]; then
    sleep 2
    echo "==> tauri dev frontend nel terminale corrente"
    cd "${FRONTEND_DIR}"
    pnpm tauri dev
fi
