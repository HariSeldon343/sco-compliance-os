# Architettura di SCO Compliance OS

Vista architetturale 10000ft. Per le decisioni puntuali sullo stack e sul layout vedere `adr/0001-stack-choice.md` e `adr/0002-monorepo-layout.md`.

## Diagramma a layer

```
+------------------------------------------------------------------+
|                       USER (Antonio / cliente)                   |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|             [1] UI LAYER — Tauri 2 + React 19 + TS 5.8           |
|             Vite 6 dev/build, Tailwind 4 styling                 |
|                                                                  |
|  +-------------+ +-------------+ +-------------+ +-------------+ |
|  | ChatView    | | VaultExpl.  | | MemoryTree  | | Connettori  | |
|  | (streaming) | | (markdown)  | | (graph)     | | (OAuth)     | |
|  +-------------+ +-------------+ +-------------+ +-------------+ |
+------------------------------------------------------------------+
                              |
                              v  (IPC Tauri commands + fetch HTTP)
+------------------------------------------------------------------+
|             [2] SHELL LAYER — Rust (src-tauri/)                  |
|             Comandi nativi, lifecycle, plugin updater Ed25519    |
|                                                                  |
|  - spawn sidecar Python  - leggi/scrivi filesystem vault         |
|  - OAuth callback        - aggiornamento auto MSI/DMG/AppImage   |
+------------------------------------------------------------------+
                              |
                              v  (HTTP REST + SSE su 127.0.0.1:7800)
+------------------------------------------------------------------+
|         [3] SIDECAR LAYER — Python 3.11 + FastAPI                |
|         Bundle PyInstaller, avvio automatico da Tauri            |
|                                                                  |
|  +-----------+  +-----------+  +-----------+  +-----------+      |
|  | /chat     |  | /vault    |  | /memory   |  | /mcp      |      |
|  | (SSE)     |  | CRUD      |  | tree API  |  | servers   |      |
|  +-----------+  +-----------+  +-----------+  +-----------+      |
|                                                                  |
|              v                                                   |
|  +-----------------------------------------------------+         |
|  | AGENT CORE — Anthropic Agent SDK                    |         |
|  | tool use, prompt caching, computer use, streaming   |         |
|  +-----------------------------------------------------+         |
+------------------------------------------------------------------+
        |                  |                |               |
        v                  v                v               v
+----------------+ +---------------+ +-------------+ +-----------+
| Anthropic API  | | MCP Servers   | | Vault       | | Memory    |
| (cloud)        | | (OAuth conn.) | | SCO         | | Tree      |
| solo chiamate  | | Gmail, Slack, | | local FS    | | local FS  |
| esplicite      | | Calendar, ... | | markdown    | | tokenized |
+----------------+ +---------------+ +-------------+ +-----------+
```

## Layer dettaglio

### [1] UI Layer — Tauri 2 + React 19

Responsabilità: rendering interfaccia utente, gestione stato locale, comunicazione con il backend.

Componenti principali:
- **ChatView**: chat con agente AI, streaming SSE token-by-token, markdown + code highlight, tool use widget cliccabili.
- **VaultExplorer**: navigazione filesystem del vault SCO, editor markdown inline, preview live.
- **MemoryTree**: visualizzazione force graph 2D/3D della knowledge base, navigazione per concetti e backlink.
- **Connettori**: gestione OAuth verso servizi esterni (Gmail, Slack, ecc.) con flow di consenso utente.

Stato: locale per default, persistenza filesystem via IPC verso shell Rust. Niente storage remoto.

### [2] Shell Layer — Rust (Tauri 2)

Responsabilità: ciclo di vita app desktop, comandi nativi, sicurezza filesystem, auto-update.

Funzioni chiave:
- Spawn del sidecar Python all'avvio (`sco-compliance-os-backend.exe` o equivalente per OS).
- IPC commands per operazioni filesystem privilegiate (creazione vault, lettura file ACL).
- Plugin updater Tauri 2 con verifica firma Ed25519 contro `latest.json` su GitHub Releases.
- OAuth callback handler (deep link sco-compliance-os://oauth/...).
- Permission system Tauri 2 per restringere accessi del WebView.

### [3] Sidecar Layer — Python FastAPI

Responsabilità: motore agente AI, integrazioni MCP, I/O vault e memory tree.

Endpoint principali:

| Endpoint | Metodo | Funzione |
|---|---|---|
| `/api/v1/chat/stream` | POST + SSE | Chat streaming token-by-token, tool use, ask_user_question |
| `/api/v1/vault/files` | GET | Lista file del vault corrente |
| `/api/v1/vault/file` | GET/PUT | Leggi/scrivi file markdown |
| `/api/v1/vault/ingest` | POST | Ingestione file in `raw/` + scheda `wiki/sources/` |
| `/api/v1/memory/tree` | GET | Knowledge graph nodes + edges |
| `/api/v1/memory/search` | POST | Ricerca semantica locale |
| `/api/v1/mcp/servers` | GET | Lista MCP server attivi |
| `/api/v1/mcp/oauth/start` | POST | Avvio flow OAuth per connettore |
| `/api/v1/health` | GET | Probe liveness/readiness sidecar |

Avvio: il sidecar bindato a `127.0.0.1:7800` (porta hardcoded), CORS configurato per accettare `http://tauri.localhost`, `http://localhost:1420`, `tauri://localhost`.

## Sequenza tipica — chat con tool use

Scenario: utente invia "Riassumi le email non lette di oggi e crea evento Calendar per domani 10:00".

```
1. UI (ChatView) -> POST /api/v1/chat/stream
   { messages: [...], conversation_id: "abc123" }
2. Sidecar riceve, monta contesto:
   - Carica conversation history da SQLite locale
   - Risolve skill attive dal catalogo (packages/agent-skills/)
   - Risolve MCP server registrati per "gmail" e "calendar"
3. Sidecar chiama Anthropic Agent SDK:
   anthropic.messages.stream(
     model="claude-opus-4-7",
     tools=[mcp_gmail_tools, mcp_calendar_tools],
     messages=[...]
   )
4. Anthropic risponde con tool_use:
   { type: "tool_use", name: "gmail_list_unread", input: {date: "2026-05-21"} }
5. Sidecar inoltra al MCP server Gmail:
   POST http://localhost:8001/mcp/tools/gmail_list_unread
6. MCP server Gmail:
   - Recupera OAuth token da keyring sistema
   - Chiama Gmail API
   - Risponde con lista 5 email
7. Sidecar inietta tool_result e riprende stream Anthropic
8. Anthropic risponde con nuovo tool_use:
   { type: "tool_use", name: "calendar_create_event", input: {...} }
9. Sidecar -> MCP Calendar -> Calendar API -> tool_result
10. Anthropic produce risposta finale text streaming
11. UI riceve SSE token-by-token, render markdown live
12. Sidecar persiste messaggio in SQLite per conversation
```

Punto chiave: la persistenza di stato widget (es. `ask_user_question`) avviene in DB lato sidecar (riferimento Conv. 48 del workflow Amodeo, single source of truth backend anche per stato widget chat post-streaming).

## Persistenza

| Cosa | Dove | Formato |
|---|---|---|
| Conversation history | SQLite locale (sidecar) | DB file `~/.sco-compliance-os/conversations.db` |
| Vault SCO | Filesystem utente | Markdown + YAML frontmatter + asset binari |
| Memory tree nodi/edge | SQLite locale (sidecar) | DB file `~/.sco-compliance-os/memory.db` |
| OAuth token connettori | Keyring sistema operativo | Credential manager Win / Keychain Mac / libsecret Linux |
| Configurazione utente | JSON file utente | `~/.sco-compliance-os/config.json` |
| Skill markdown | `packages/agent-skills/skills/` | Markdown + YAML |

Nessun database server, nessun servizio cloud per persistenza. Lo stato vive sul filesystem dell'utente.

## Modello di sicurezza

1. **CORS restrittivo**: il sidecar accetta solo origin di Tauri WebView e `localhost:1420` per dev. Niente wildcard `*` in produzione.
2. **Porta sidecar locale only**: `127.0.0.1:7800`, niente bind su `0.0.0.0`.
3. **OAuth token in keyring OS**: niente plain text su filesystem, niente env var.
4. **Firma updater Ed25519**: ogni MSI/DMG/AppImage firmato, public key embedded nel binario shell.
5. **Permission system Tauri 2**: il WebView ha capabilities esplicite, niente accesso filesystem arbitrario.
6. **Vault sandboxing**: il sidecar accede solo al vault corrente selezionato dall'utente, niente path traversal.

## Riferimenti incrociati

- ADR 0001 — Scelta dello stack tecnologico
- ADR 0002 — Layout del monorepo
- `docs/ROADMAP.md` — Piano di sviluppo a 4 wave
- Convenzioni operative workflow Amodeo: `CLAUDE.md` Second Brain, Conv. 44 (debug Tauri 2/Python), Conv. 45 (cross-platform CI matrix), Conv. 46 (smoke test E2E prima del tag), Conv. 47 (single source of truth costanti), Conv. 48 (single source of truth stato widget)
