#!/usr/bin/env bash
# PyInstaller orchestrator per macOS + Linux.
# Setup venv -> install deps -> run pyinstaller -> copy a frontend sidecar path.
# Conv. 45 lesson 1 enforcement: triple naming per OS.
# Conv. 45 cristallizzato sco-agent-local: su macOS copia con 3 nomi alternativi
# (aarch64, x86_64, universal) per Tauri sidecar resolution opaca.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"
FRONTEND_BIN_DIR="${PROJECT_ROOT}/frontend/src-tauri/binaries"

OS="$(uname -s)"
case "${OS}" in
    Darwin)
        SPEC="sco-compliance-os-backend-macos.spec"
        SIDECAR_SRC="${BACKEND_DIR}/dist/sco-compliance-os-backend"
        DEST_PRIMARY="${FRONTEND_BIN_DIR}/sco-compliance-os-backend-aarch64-apple-darwin"
        DEST_X86="${FRONTEND_BIN_DIR}/sco-compliance-os-backend-x86_64-apple-darwin"
        DEST_UNIV="${FRONTEND_BIN_DIR}/sco-compliance-os-backend-universal-apple-darwin"
        ;;
    Linux)
        SPEC="sco-compliance-os-backend-linux.spec"
        SIDECAR_SRC="${BACKEND_DIR}/dist/sco-compliance-os-backend"
        DEST_PRIMARY="${FRONTEND_BIN_DIR}/sco-compliance-os-backend-x86_64-unknown-linux-gnu"
        ;;
    *)
        echo "ERROR: OS non supportato dallo script .sh: ${OS}" >&2
        echo "       Per Windows usa scripts/build-backend.ps1" >&2
        exit 1
        ;;
esac

CLEAN=0
NO_VERIFY=0
for arg in "$@"; do
    case "${arg}" in
        --clean) CLEAN=1 ;;
        --no-verify) NO_VERIFY=1 ;;
    esac
done

echo "==> sco-compliance-os build-backend (${OS})"
echo "    Project root: ${PROJECT_ROOT}"
echo "    Spec:         ${SPEC}"

cd "${BACKEND_DIR}"

if [ "${CLEAN}" -eq 1 ]; then
    echo "==> Clean dist + build dirs"
    rm -rf dist build
fi

command -v uv >/dev/null 2>&1 || {
    echo "ERROR: uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    exit 1
}

echo "==> uv sync"
uv sync

echo "==> pyinstaller ${SPEC}"
uv run pyinstaller "${SPEC}" --noconfirm

if [ ! -f "${SIDECAR_SRC}" ]; then
    echo "ERROR: Sidecar binary not produced at: ${SIDECAR_SRC}" >&2
    exit 1
fi

echo "==> Copy sidecar to frontend binaries"
mkdir -p "${FRONTEND_BIN_DIR}"
cp "${SIDECAR_SRC}" "${DEST_PRIMARY}"
chmod +x "${DEST_PRIMARY}"
echo "    Copied to: ${DEST_PRIMARY}"

# macOS: triplo alias per Tauri sidecar resolution (Conv. 45 cristallizzato)
if [ "${OS}" = "Darwin" ]; then
    cp "${SIDECAR_SRC}" "${DEST_X86}"
    cp "${SIDECAR_SRC}" "${DEST_UNIV}"
    chmod +x "${DEST_X86}" "${DEST_UNIV}"
    echo "    Copied to: ${DEST_X86}"
    echo "    Copied to: ${DEST_UNIV}"
fi

if [ "${NO_VERIFY}" -eq 0 ]; then
    echo "==> Verify sidecar runs (Conv. 44 lesson 3 smoke)"
    if "${DEST_PRIMARY}" --help >/dev/null 2>&1 || [ $? -eq 2 ]; then
        echo "    Sidecar OK."
    else
        echo "    WARNING: sidecar verify exit code != 0. Verifica hidden imports in ${SPEC}." >&2
    fi
fi

echo "==> Build backend DONE"
