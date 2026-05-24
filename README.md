# SCO Compliance OS

[![Integration Tests](https://github.com/HariSeldon342/sco-compliance-os/actions/workflows/integration-test.yml/badge.svg)](https://github.com/HariSeldon342/sco-compliance-os/actions/workflows/integration-test.yml)
[![CI](https://github.com/HariSeldon342/sco-compliance-os/actions/workflows/ci.yml/badge.svg)](https://github.com/HariSeldon342/sco-compliance-os/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-1.0.0-302e5c)](docs/RELEASE_NOTES_v1.0.0.md)
[![Platforms](https://img.shields.io/badge/platforms-Windows%20%7C%20macOS%20%7C%20Linux-0074b4)](docs/RELEASE_NOTES_v1.0.0.md#come-installare)
[![License](https://img.shields.io/badge/license-Proprietary-ffa727)](LICENSE)

**Privato. Tuo. Italiano.**

Sistema operativo AI desktop per il consulente normativo italiano. SCO Solution Consulting srls.

Brand: SCO Solution Consulting srls. Palette navy `#302e5c` + blue `#0074b4` + amber `#ffa727`. Tipografia Inter (UI) + Source Code Pro (mono).

---

## Cos'è

SCO Compliance OS è una postazione di lavoro AI privata per consulenti di compliance. Tre piani di lavoro integrati.

1. **Chat con agente AI** multi-LLM (Anthropic, OpenAI, Gemini, Ollama), con voce on-device opzionale (Whisper.cpp STT, Piper TTS) e mascotte SVG opzionale.
2. **Vault editabile** in markdown, repository locale leggibile, versionabile git, sincronizzabile fra PC. Wiki di compliance a cinque categorie (raw, sources, entities, concepts, synthesis, glossari).
3. **Memory Tree gerarchica** con sintesi progressiva a quattro fasi (L0 raw, L1 compressed, L2 synthesis, L3 canonical) tramite Claude Haiku. Nessun vector database esterno.

Oltre 100 connettori OAuth disponibili via protocollo MCP (Gmail, Calendar, Drive, Slack, GitHub, Notion e altri). Connettività cloud sempre opt-in. Default privacy: niente telemetria, niente egress automatico, niente upload silenziosi.

## Quick install

Scaricare l'artefatto firmato Ed25519 dalla pagina release ufficiale.

| OS | File |
|---|---|
| Windows 10 64-bit o superiore | `sco-compliance-os_1.0.0_x64_en-US.msi` |
| macOS 11 o superiore | `sco-compliance-os_1.0.0_universal.dmg` (Intel + Apple Silicon) |
| Linux x86_64 | `sco-compliance-os_1.0.0_amd64.AppImage` |

Al primo avvio il sistema chiede licenza tenant (richiedibile a `commerciale@scosolution.it`) e profila l'utente tramite la skill `os-setup`. Aggiornamenti automatici verificati Ed25519 attivi per default.

## Documentazione release

- **`docs/RELEASE_NOTES_v1.0.0.md`** — Note di rilascio narrative della General Availability del 24/05/2026.
- **`docs/CHANGELOG.md`** — Storico tecnico delle release v0.4.0 → v1.0.0.
- **`docs/ARCHITECTURE.md`** — Vista architetturale a 10000ft.
- **`docs/ROADMAP.md`** — Wave di sviluppo e piano release successive.

## Perché esiste

Il lavoro consulenziale di compliance produce decine di deliverable a settimana (procedure SGSI, RVE audit, perizie CTU, gap analysis, atti di gara, contenuti editoriali). I tool generalisti (assistenti web, plugin IDE) sono nati per altri use case e impongono compromessi sul controllo dei dati e sulla persistenza della conoscenza maturata sessione dopo sessione.

SCO Compliance OS nasce per:

- Conservare in locale il "secondo cervello" del consulente, in formato markdown leggibile, versionato git, sincronizzabile fra PC.
- Standardizzare il workflow del consulente (regole permanenti, convenzioni operative, skill di dominio) come asset compounding.
- Disaccoppiare il valore consulenziale dal fornitore AI del momento, grazie al routing multi-LLM e al protocollo MCP per i connettori esterni.

## Stack tecnologico

| Layer | Tecnologia | Versione | Note |
|---|---|---|---|
| Shell desktop | Tauri | 2.x | Cross-platform Windows + macOS + Linux |
| Linguaggio shell | Rust | stable | IPC commands, plugin nativi |
| UI | React | 19.x | Componenti, hook, suspense |
| Linguaggio UI | TypeScript | 5.8.x | Strict mode |
| Bundler UI | Vite | 6.x | Dev server HMR |
| Styling | Tailwind CSS | 4.x | Plugin `@tailwindcss/vite` |
| Backend agente | Python | 3.12 | FastAPI sidecar PyInstaller-bundled |
| Framework HTTP | FastAPI | 0.115+ | Endpoint chat + SSE streaming |
| SDK AI primario | Anthropic Claude Sonnet 4.6 | latest | Reasoning, tool use, vision |
| Multi-LLM router | Anthropic + OpenAI + Gemini + Ollama | n/a | Profili reasoning / fast / vision |
| Voce on-device | Whisper.cpp (STT) + Piper (TTS) | latest | Modelli italiani inclusi |
| Connettori | Model Context Protocol (MCP) | spec 2024-11 | OAuth-backed via MCP servers |
| Package manager | pnpm | 10.x | Workspace monorepo |
| Build cross-OS | GitHub Actions matrix | n/a | Windows + macOS + Linux runners |

## Quick start sviluppo

Requisiti host: Node.js 22 LTS, pnpm 10, Rust toolchain stabile, Python 3.12, uv (Python package manager). Su Windows servono anche i Visual Studio Build Tools (per la compilazione Rust).

```powershell
# Clone (path canonico)
cd C:\Users\aoedo\Progetti\sco-compliance-os

# Install dipendenze monorepo
pnpm install

# Bootstrap backend Python (sidecar)
cd backend
uv sync
cd ..

# Dev parallelo (frontend Vite + backend FastAPI uvicorn)
pnpm dev
# oppure su Windows:
powershell -ExecutionPolicy Bypass -File scripts/dev.ps1
```

Build produzione locale:

```powershell
pnpm build
```

Per il flusso CI matrix cross-OS vedere `.github/workflows/`. Gli artefatti sono firmati Ed25519, l'aggiornamento automatico via Tauri Updater verifica la firma prima dell'installazione del delta.

## Architettura monorepo

```
sco-compliance-os/
├── frontend/                 # Tauri 2 + React 19 + Vite 6 + Tailwind 4
│   ├── src/                  # Componenti UI, hook, route
│   └── src-tauri/            # Shell Rust, IPC commands
├── backend/                  # FastAPI sidecar Python
│   └── sco_compliance_os/    # Logica agente, MCP wiring, vault I/O
├── packages/
│   ├── agent-skills/         # Skill di dominio markdown versionabili
│   └── integrations/         # Adattatori MCP per connettori OAuth
├── scripts/                  # PowerShell + bash helper di build/dev
├── docs/                     # ADR, architettura, roadmap, release notes
└── .github/workflows/        # CI matrix Windows + macOS + Linux
```

Razionale dettagliato in `docs/adr/0002-monorepo-layout.md`. Vista architetturale completa con diagramma layer in `docs/ARCHITECTURE.md`.

## Licenza

Software proprietario chiuso, copyright SCO Solution Consulting srls. Vedere `LICENSE` per i termini completi. Nessuna parte di questo software è rilasciata sotto licenza open source. Riproduzione, modifica, distribuzione, sublicenza e rivendita non autorizzate sono vietate.

Per richiesta licenza commerciale (Starter, Professional, Enterprise) scrivere a `commerciale@scosolution.it`.

## Riferimenti interni

- `docs/RELEASE_NOTES_v1.0.0.md` — Release notes General Availability v1.0.0
- `docs/CHANGELOG.md` — Storico release tecnico v0.4.0 → v1.0.0
- `docs/ARCHITECTURE.md` — Vista architetturale a 10000ft
- `docs/ROADMAP.md` — Roadmap a 4 wave
- `docs/adr/0001-stack-choice.md` — Architecture Decision Record sullo stack
- `docs/adr/0002-monorepo-layout.md` — ADR sul layout del monorepo
- `scripts/dev.ps1` — Avvio sviluppo parallelo Windows
