# Changelog SCO Compliance OS

Tutte le modifiche notevoli sono documentate in questo file. Il progetto segue il versionamento semantico (MAJOR.MINOR.PATCH).

---

## v1.0.0 — 24/05/2026

Prima release generale. Per la descrizione narrativa completa vedere `RELEASE_NOTES_v1.0.0.md`. Cumulativa delle otto release di sviluppo che la precedono (v0.4.0 → v0.7.3).

---

## v0.7.3 — 24/05/2026

Patch finale pre-GA.

- Fix bug rendering pannello impostazioni multi-LLM su macOS Apple Silicon.
- Hardening firma Ed25519 degli artefatti, allineamento `latest.json` su tre OS.
- Allineamento versione costanti `LEGAL_VERSION`, `PRIVACY_VERSION`, `DEMO_VERSION` fra backend e frontend (single source of truth lato backend).

## v0.7.2 — 23/05/2026

Stabilizzazione SaaS admin.

- Pannello membri del team con ruoli granulari (admin, editor, viewer).
- Pricing plan a tre livelli (Starter, Professional, Enterprise) cablati su Stripe.
- Audit log con filtro multi-tenant e export CSV.

## v0.7.1 — 23/05/2026

Connettori OAuth completati.

- Gmail, Google Calendar, Google Drive, Slack, GitHub: cinque connettori cablati end-to-end via MCP.
- Scope minimo per ciascun connettore, revoca dalla console impostazioni.
- Token store su keyring di sistema (Windows Credential Manager, macOS Keychain, Linux Secret Service).

## v0.7.0 — 22/05/2026

Multi-LLM router e voce on-device.

- Router multi-LLM con quattro provider: Anthropic, OpenAI, Gemini, Ollama.
- Tre profili modello: reasoning (Claude Sonnet 4.6), fast (Claude Haiku), vision (Claude Sonnet 4.6 multimodale).
- STT con Whisper.cpp, quattro modelli selezionabili (`tiny`, `base`, `small`, `medium`).
- TTS con Piper, voci italiane on-device.

## v0.6.0 — 21/05/2026

Memory Tree bucket-seal.

- Implementazione della memoria gerarchica a quattro fasi (L0 raw, L1 compressed, L2 synthesis, L3 canonical).
- Estrattore basato su Claude Haiku per la sintesi progressiva.
- Ricerca semantica locale senza vector database esterno, fondata su tokenizzazione e gerarchia.

## v0.5.1 — 20/05/2026

Vault auto-ingest e skill loader.

- Auto-ingest su sette estensioni (`.md`, `.pdf`, `.docx`, `.xlsx`, `.pptx`, `.txt`, `.json`).
- File watcher live, propagazione automatica delle modifiche in vault.
- Skill loader runtime con hot-reload, skill `os-setup` per profilazione utente al primo avvio.
- Schema scheda standard per ogni nuovo deposito in `raw/`.

## v0.5.0 — 19/05/2026

Wiki SCO e knowledge layer.

- Strutturazione del vault in cinque categorie (`raw`, `sources`, `entities`, `concepts`, `synthesis`, `glossari`).
- Indicizzatore in-process per la navigazione del wiki di compliance.
- Editor markdown integrato con preview live, sintassi YAML frontmatter, link bidirezionali fra entità e fonti.

## v0.4.0 — 18/05/2026

Foundation release.

- Shell Tauri 2 cross-platform Windows + macOS + Linux.
- UI React 19 + TypeScript 5.8 + Vite 6 + Tailwind 4 con palette brand SCO.
- Backend FastAPI Python 3.12 sidecar PyInstaller-bundled.
- Integrazione Anthropic Claude Sonnet 4.6 come provider primario di chat.
- Auto-update Tauri Updater con firma Ed25519 e `latest.json` unificato sui tre OS.
- Comand Palette `⌘K`, BottomTabBar, MeshGradient WebGL.
- Mascotte SVG 2D opzionale.

---

## Note sul versionamento

Le release dalla v0.4.0 alla v0.7.3 sono pre-rilascio cumulative, integrate nella v1.0.0 General Availability del 24/05/2026. La numerazione MAJOR.MINOR.PATCH dalla v1.0.0 in poi segue lo standard SemVer: cambio MAJOR per modifiche incompatibili, MINOR per nuove funzionalità retro-compatibili, PATCH per fix.

Per la roadmap delle release successive vedere `docs/ROADMAP.md`.
