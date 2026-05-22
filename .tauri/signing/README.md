# Tauri 2 Code Signing (Ed25519) - Setup

Genera e gestisce le chiavi di firma Ed25519 per l'auto-update di SCO Compliance OS.

> NB: Il file privato `private.key` NON va MAI committato. La cartella `.tauri/signing/` e' aggiunta a `.gitignore`.

## Setup iniziale (una volta sola, da macchina dev)

### 1. Installa Tauri CLI

```bash
cargo install tauri-cli --version "^2" --locked
```

### 2. Genera keypair Ed25519

```bash
pnpm tauri signer generate -w .tauri/signing/private.key
```

Il comando produce:

- `private.key` (file privato, NON committare)
- chiave pubblica stampata in console (formato base64)

### 3. Copia la chiave pubblica in `tauri.conf.json`

In `frontend/src-tauri/tauri.conf.json`:

```json
{
  "plugins": {
    "updater": {
      "active": true,
      "endpoints": [
        "https://github.com/asamodeo/sco-compliance-os/releases/latest/download/latest.json"
      ],
      "pubkey": "<chiave pubblica base64 dal comando precedente>"
    }
  }
}
```

### 4. Aggiungi i GitHub Secrets

Settings -> Secrets and variables -> Actions -> New repository secret:

- **`TAURI_SIGNING_PRIVATE_KEY`**: contenuto completo del file `.tauri/signing/private.key`
- **`TAURI_SIGNING_PRIVATE_KEY_PASSWORD`**: password se impostata, altrimenti stringa vuota

## Verifica setup

Localmente:

```bash
pnpm tauri signer sign -k .tauri/signing/private.key <path-artefatto>
```

CI:

```bash
# Triggera workflow Release manualmente da Actions UI
# Output: ogni MSI/DMG/AppImage avra' il proprio .sig file (Ed25519 detached signature)
# + latest.json conterra' il campo `signature` base64 per ogni piattaforma
```

## Rotazione chiavi

Se la chiave privata e' compromessa:

1. Genera nuova keypair (`pnpm tauri signer generate -w .tauri/signing/private-v2.key`)
2. Aggiorna `pubkey` in `tauri.conf.json` con la nuova pubblica
3. Aggiorna `TAURI_SIGNING_PRIVATE_KEY` secret su GitHub
4. Rilascia patch version con la nuova firma
5. Gli utenti su versione precedente NON riceveranno l'auto-update finche' non re-installano manualmente (firma mismatch). Comunica esplicitamente la rotazione.

## Riferimenti

- [Tauri 2 Updater plugin docs](https://v2.tauri.app/plugin/updater/)
- [Ed25519 signature spec](https://datatracker.ietf.org/doc/html/rfc8032)
- Convenzione 45 lesson 2 (CLAUDE.md vault): Tauri Updater supporta MSI/DMG/AppImage, NON DEB/RPM
- Convenzione 46 (CLAUDE.md vault): SMOKE TEST E2E PRIMA DEL TAG GIT
