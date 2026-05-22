# SCO Compliance OS

> "Compliance OS for AI" — la postazione di lavoro AI di SCO Solution Consulting srls.

Applicazione desktop locale-first per il lavoro consulenziale di Antonio Amodeo. Agente AI con vault Karpathy editabile, memory tree gerarchica, connettori OAuth verso servizi cloud, multi-LLM router. Tutto on-device per default, niente upload silenziosi al cloud.

Brand: SCO Solution Consulting srls. Palette navy `#302e5c` + blue `#0074b4` + amber `#ffa727`. Tipografia Inter (UI) + Source Code Pro (mono).

---

## Cos'è

SCO Compliance OS è un sistema operativo AI desktop per consulenti normativi. Tre piani di lavoro:

1. **Chat con agente**, multi-LLM (reasoning/fast/vision), tool use end-to-end, voice STT/TTS opzionale, mascot opzionale.
2. **Vault Karpathy**, repository markdown locale (filesystem nativo) editabile a mano e dall'agente. Wiki di compliance, raw, sources, entities, concepts, synthesis, glossari.
3. **Memory Tree**, knowledge base gerarchica tokenizzata, sintesi progressiva, ricerca semantica locale senza vector DB esterno.

Connettività verso il cloud solo su richiesta, via 100+ connettori OAuth plug-in (Gmail, Calendar, Slack, GitHub, Notion, Drive, ecc.). Default privacy: niente telemetria, niente egress automatico.

## Perché esiste

Il lavoro consulenziale di Antonio Amodeo produce decine di deliverable a settimana (procedure SGSI, RVE audit, perizie CTU, gap analysis, atti di gara, contenuti LinkedIn). I tool generalisti (ChatGPT web, Claude.ai web, IDE plugin) sono nati per altri use case e impongono compromessi sul controllo dei dati e sulla persistenza della conoscenza maturata sessione dopo sessione.

SCO Compliance OS nasce per:

- Conservare in locale il "secondo cervello" del consulente, in formato markdown leggibile, versionato git, sincronizzabile fra PC.
- Standardizzare il workflow Amodeo (regole permanenti, convenzioni operative, skill di dominio) come asset compounding.
- Disaccoppiare il valore consulenziale dall'AI provider del momento, grazie al routing multi-LLM e al protocollo MCP per i connettori esterni.

## Stack

| Layer | Tecnologia | Versione | Note |
|---|---|---|---|
| Shell desktop | Tauri | 2.x | Cross-platform Windows + macOS + Linux |
| Linguaggio shell | Rust | stable | IPC commands, plugin nativi |
| UI | React | 19.x | Componenti, hook, suspense |
| Linguaggio UI | TypeScript | 5.8.x | Strict mode |
| Bundler UI | Vite | 6.x | Dev server HMR |
| Styling | Tailwind CSS | 4.x | Plugin `@tailwindcss/vite` |
| Backend agente | Python | 3.11+ | FastAPI sidecar PyInstaller-bundled |
| Framework HTTP | FastAPI | 0.115+ | Endpoint chat + SSE streaming |
| SDK AI | Anthropic Agent SDK | latest | Reasoning, tool use, computer use |
| Connettori | MCP (Model Context Protocol) | spec 2024-11 | OAuth-backed via MCP servers |
| Package manager | pnpm | 10.x | Workspace monorepo |
| Build cross-OS | GitHub Actions matrix | n/a | Windows + macOS + Linux runners |

Ipotesi tecnica da validare: il routing multi-LLM richiederà un layer adapter unificato. Soluzioni candidate `LiteLLM` (Python) oppure adapter custom. Decisione rimandata a Wave 3 (vedi `docs/ROADMAP.md`).

## Quick start dev

Requisiti host: Node.js 22.x LTS, pnpm 10.x, Rust toolchain stabile, Python 3.11+, uv (Python package manager). Su Windows serve anche Visual Studio Build Tools (per la compilazione Rust).

```powershell
# Clone (path canonico Antonio)
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

Build produzione locale (MSI Windows):

```powershell
pnpm build
```

Per il flusso CI matrix cross-OS vedere `.github/workflows/` (carry-over Wave 1, riferimento `sco-agent-local` Conv. 45).

## Architettura monorepo

```
sco-compliance-os/
├── frontend/                 # Tauri 2 + React 19 + Vite 6 + Tailwind 4
│   ├── src/                  # Componenti UI, hook, route
│   └── src-tauri/            # Shell Rust, IPC commands
├── backend/                  # FastAPI sidecar Python
│   └── sco_compliance_os/    # Logica agente, MCP wiring, vault I/O
├── packages/
│   ├── agent-skills/         # Skill di dominio markdown (versionabili)
│   └── integrations/         # Adattatori MCP per connettori OAuth
├── scripts/                  # PowerShell + bash helper di build/dev
├── docs/                     # ADR, architettura, roadmap
└── .github/workflows/        # CI matrix Windows + macOS + Linux
```

Dettaglio razionale in `docs/adr/0002-monorepo-layout.md`.

Vista architetturale completa con diagramma layer in `docs/ARCHITECTURE.md`.

## Roadmap

Lavorazione in 4 wave incrementali (totale ~5-7 mesi calendario, calibrato sul ritmo sostenibile per consulente full-time).

| Wave | Obiettivo | Durata stimata |
|---|---|---|
| 1 | MVP locale single-LLM Anthropic + vault + chat | 4-6 settimane |
| 2 | Memory Tree + 5-10 connettori OAuth core | 4-6 settimane |
| 3 | Multi-LLM router + voice STT/TTS + plugin system | 4-6 settimane |
| 4 | 100+ integrazioni + mascot opzionale + auto-update | 8-12 settimane |

Dettaglio in `docs/ROADMAP.md`.

## Licenza

Software proprietario chiuso, copyright SCO Solution Consulting srls. Vedere `LICENSE` per i termini completi. Nessuna parte di questo software è rilasciata sotto licenza open source. Riproduzione, modifica e distribuzione non autorizzate sono vietate.

## Riferimenti interni

- `docs/adr/0001-stack-choice.md` — Architecture Decision Record sullo stack
- `docs/adr/0002-monorepo-layout.md` — ADR sul layout del monorepo
- `docs/ARCHITECTURE.md` — Vista architetturale 10000ft
- `docs/ROADMAP.md` — Roadmap di sviluppo a 4 wave
- `scripts/dev.ps1` — Avvio sviluppo parallelo Windows
