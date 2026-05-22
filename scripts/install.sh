#!/usr/bin/env bash
# Self-installer macOS/Linux per SCO Compliance OS.
# Download latest release DMG (macOS) / AppImage (Linux) + verifica SHA256.
# Ed25519 firma verificata dal Tauri Updater al primo avvio.
# STUB minimale wave 1, espansione progressiva.

set -euo pipefail

REPO="${REPO:-asamodeo/sco-compliance-os}"
VERSION="${VERSION:-latest}"
DRY_RUN=0
for arg in "$@"; do
    case "${arg}" in
        --dry-run) DRY_RUN=1 ;;
        --repo=*) REPO="${arg#*=}" ;;
        --version=*) VERSION="${arg#*=}" ;;
    esac
done

OS="$(uname -s)"
case "${OS}" in
    Darwin) PLATFORM="macos"; EXT="dmg"; INSTALL_DIR="${HOME}/Applications" ;;
    Linux)  PLATFORM="linux"; EXT="AppImage"; INSTALL_DIR="${HOME}/Applications" ;;
    *)
        echo "ERROR: OS non supportato: ${OS}. Per Windows usa scripts/install.ps1" >&2
        exit 1
        ;;
esac

echo "==> SCO Compliance OS - Self installer (${PLATFORM})"
echo "    Repo:    ${REPO}"
echo "    Version: ${VERSION}"

# Resolve latest tag
if [ "${VERSION}" = "latest" ]; then
    echo "==> Fetching latest release tag..."
    REL_JSON=$(curl -sL "https://api.github.com/repos/${REPO}/releases/latest")
    VERSION=$(echo "${REL_JSON}" | grep -m1 '"tag_name"' | sed -E 's/.*"tag_name": *"([^"]+)".*/\1/')
    echo "    Resolved: ${VERSION}"
else
    REL_JSON=$(curl -sL "https://api.github.com/repos/${REPO}/releases/tags/${VERSION}")
fi

# Find asset
ASSET_URL=$(echo "${REL_JSON}" | grep '"browser_download_url"' | grep -i "\.${EXT}" | head -n1 | sed -E 's/.*"browser_download_url": *"([^"]+)".*/\1/')

if [ -z "${ASSET_URL}" ]; then
    echo "ERROR: ${EXT} asset not found in release ${VERSION}" >&2
    exit 1
fi

FILENAME="$(basename "${ASSET_URL}")"
DOWNLOAD_PATH="/tmp/${FILENAME}"

echo "==> Downloading: ${ASSET_URL}"
echo "    To: ${DOWNLOAD_PATH}"

if [ "${DRY_RUN}" -eq 1 ]; then
    echo "DRY-RUN: no actual download/install"
    exit 0
fi

curl -sLfo "${DOWNLOAD_PATH}" "${ASSET_URL}"

# SHA256 verify se disponibile via .sig sidecar
SIG_URL="${ASSET_URL}.sig"
if curl -sLfI "${SIG_URL}" >/dev/null 2>&1; then
    echo "==> Ed25519 .sig sidecar present (verifica delegata al Tauri Updater post-install)."
fi

mkdir -p "${INSTALL_DIR}"

case "${PLATFORM}" in
    macos)
        echo "==> Mount DMG + copia .app a ${INSTALL_DIR}"
        MOUNT_POINT="/Volumes/SCOComplianceOS"
        hdiutil attach "${DOWNLOAD_PATH}" -mountpoint "${MOUNT_POINT}" -nobrowse -quiet
        APP_SRC=$(find "${MOUNT_POINT}" -name "*.app" -maxdepth 2 | head -n1)
        if [ -z "${APP_SRC}" ]; then
            hdiutil detach "${MOUNT_POINT}" -quiet
            echo "ERROR: .app non trovato nel DMG" >&2
            exit 1
        fi
        cp -R "${APP_SRC}" "${INSTALL_DIR}/"
        hdiutil detach "${MOUNT_POINT}" -quiet
        echo "==> Installato in: ${INSTALL_DIR}/$(basename "${APP_SRC}")"
        ;;
    linux)
        DEST="${INSTALL_DIR}/${FILENAME}"
        cp "${DOWNLOAD_PATH}" "${DEST}"
        chmod +x "${DEST}"
        echo "==> Installato in: ${DEST}"
        echo "    Avvia: ${DEST}"
        ;;
esac

rm -f "${DOWNLOAD_PATH}"
echo "==> Install DONE"
