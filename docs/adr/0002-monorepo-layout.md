# ADR 0002 — Layout del monorepo

- **Status**: Accettato
- **Data**: 2026-05-21
- **Decisore**: Antonio Amodeo
- **Relativo a**: ADR 0001 (stack tecnologico)

## Contesto

Lo stack di SCO Compliance OS combina tre toolchain (Rust, Python, TypeScript) e prevede in Wave 3+4 un sistema plug-in di skill di dominio e connettori OAuth/MCP. Servono regole chiare su dove vive ciascun pezzo, come si condividono i tipi di dato e quali confini sono permeabili.

Alternativa estrema A: multi-repo, un repo Git per ogni layer. Pro: build CI isolata. Contro: dependency drift fra layer, friction di sviluppo cross-cutting (un endpoint nuovo tocca 3 repo).

Alternativa estrema B: monolite single-package senza workspace. Pro: massimo accoppiamento. Contro: package.json di 200+ dipendenze miste, impossibile mantenere.

Si sceglie la via di mezzo: monorepo unico con workspace logici disaccoppiati.

## Decisione

Layout adottato:

```
sco-compliance-os/
├── frontend/                       # Workspace pnpm — shell Tauri 2 + UI React
│   ├── src/                        # Componenti, hook, route TypeScript
│   ├── src-tauri/                  # Shell Rust (IPC commands, plugin)
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── backend/                        # Sidecar Python — NON in workspace pnpm
│   ├── sco_compliance_os/          # Package Python principale
│   │   ├── main.py                 # FastAPI app entry
│   │   ├── api/                    # Endpoint HTTP + SSE
│   │   ├── agent/                  # Wiring Anthropic Agent SDK
│   │   ├── mcp/                    # MCP client + server registry
│   │   ├── vault/                  # I/O vault SCO
│   │   └── memory/                 # Memory tree
│   ├── tests/                      # pytest
│   ├── pyproject.toml
│   └── *.spec                      # PyInstaller spec per OS (Conv. 45)
├── packages/                       # Workspace pnpm — pacchetti supporto
│   ├── agent-skills/               # Skill markdown di dominio (compliance, audit, ecc.)
│   │   ├── README.md
│   │   └── skills/
│   │       └── <skill-name>/
│   │           └── SKILL.md
│   └── integrations/               # Adattatori MCP per connettori OAuth
│       ├── README.md
│       └── adapters/
│           └── <provider>/
├── scripts/                        # Helper PowerShell + bash
│   ├── dev.ps1                     # Avvio parallelo dev
│   ├── build-backend.ps1           # PyInstaller bundle
│   └── ci/                         # Script CI matrix
├── docs/
│   ├── adr/                        # Architecture Decision Record
│   ├── ARCHITECTURE.md             # Vista 10000ft
│   └── ROADMAP.md                  # Wave 1-4
├── .github/workflows/              # CI matrix Windows + macOS + Linux
├── package.json                    # Root: orchestrazione script monorepo
├── pnpm-workspace.yaml             # Workspace declaration
├── README.md
├── LICENSE
└── .gitignore
```

### Regole di confine

1. **`frontend/` non importa direttamente da `backend/`**. La comunicazione è solo via IPC Tauri + HTTP REST/SSE verso il sidecar. Niente dipendenze TypeScript su moduli Python.
2. **`backend/` non importa direttamente da `frontend/`**. Niente parsing di componenti React lato Python.
3. **`packages/agent-skills/` è consumato sia dal backend (lettura SKILL.md a runtime) sia dal frontend (catalogo visibile in UI)**. Convenzione: solo file markdown + frontmatter YAML, niente codice eseguibile diretto.
4. **`packages/integrations/` è consumato dal backend (MCP server adapter)**. Convenzione: ogni adapter è un modulo Python o un pacchetto npm separato sotto il workspace.
5. **`scripts/` è agnostico al layer**: contiene solo orchestratori cross-toolchain (PowerShell preferito su Windows, bash su macOS/Linux).

### Lockfile policy

- `pnpm-lock.yaml` alla root (single lockfile monorepo) è committato.
- `package-lock.json` e `yarn.lock` sono esclusi da `.gitignore` per evitare drift di package manager.
- `backend/uv.lock` è committato come lockfile Python deterministico.
- `frontend/src-tauri/Cargo.lock` è committato (best practice Rust per binari).

## Conseguenze

### Positive

- **Confini chiari fra layer**: ogni toolchain ha la sua casa, ogni cross-cutting concern (skill, integrations) ha un pacchetto dedicato.
- **CI matrix mantenibile**: ogni runner OS può eseguire build mirate (`pnpm --filter frontend build` per UI, `cd backend && uv build && pyinstaller` per sidecar).
- **Onboarding nuovi PC veloce**: `git clone` + `pnpm install` + `uv sync` in `backend/` = ambiente dev pronto.
- **Skill e integrations versionabili indipendentemente**: in futuro si possono pubblicare come pacchetti separati senza riorganizzare il repo.

### Negative

- **Doppio package manager** (pnpm + uv): chi contribuisce deve conoscerli entrambi. Mitigazione: documentazione in `README.md` e script `dev.ps1` che astrae l'avvio.
- **Workspace `packages/` ancora vuoti in Wave 1**: rischio "premature abstraction". Mitigazione: si accetta che siano scaffolded vuoti fino a Wave 2-3.

### Neutre

- **Allineamento al pattern `sco-agent-local`**: layout simile al progetto reference, riduce friction cognitiva per Antonio.

## Alternative considerate e scartate

| Alternativa | Motivo dello scarto |
|---|---|
| Nx monorepo | Overkill per 3 layer, complessità config alta, slow onboarding |
| Turborepo | Caching incrementale utile su scala team, qui siamo single-developer |
| Multi-repo Git | Dependency drift, friction cross-cutting troppo alta |
| Python in pnpm workspace via pyproject-bridge | Esperimentale, non production-ready |
| Backend Rust invece di Python sidecar | Vedi ADR 0001 per le ragioni di scarto |

## Riferimenti

- ADR 0001 — Scelta dello stack tecnologico
- pnpm workspaces docs: https://pnpm.io/workspaces
- uv (Python package manager): https://github.com/astral-sh/uv
