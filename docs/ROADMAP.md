# Roadmap SCO Compliance OS

Roadmap incrementale a 4 wave. Ogni wave si chiude con una release pubblica firmata (`vN.0.0`) e uno smoke test E2E su 3 OS (riferimento Conv. 46 workflow Amodeo). Durata totale stimata: 5-7 mesi calendario, calibrata sul ritmo sostenibile di un consulente full-time che sviluppa in parallelo al lavoro core.

## Sintesi

| Wave | Obiettivo principale | Durata | Release target |
|---|---|---|---|
| 1 | MVP locale single-LLM Anthropic + vault + chat | 4-6 settimane | v0.1.0 |
| 2 | Memory Tree + 5-10 connettori OAuth core | 4-6 settimane | v0.2.0 |
| 3 | Multi-LLM router + voice STT/TTS + plugin system | 4-6 settimane | v0.3.0 |
| 4 | 100+ integrazioni + mascot opzionale + auto-update produzione | 8-12 settimane | v1.0.0 |

## Wave 1 — MVP locale single-LLM (4-6 settimane)

Obiettivo: avere in mano un'app desktop installabile su Windows che esegua una chat completa con vault SCO editabile, single-LLM Anthropic, senza connettori esterni.

Deliverable:
- Shell Tauri 2 funzionante con WebView2 Windows, navigation base.
- Sidecar FastAPI con endpoint `/api/v1/chat/stream` SSE, conversation history SQLite.
- Wiring Anthropic Agent SDK base (no tool use ancora).
- VaultExplorer UI con editor markdown e preview live.
- Bootstrap vault da template SCO (struttura `raw/`, `wiki/`, `CLAUDE.md` seed).
- Build MSI Windows firmato, distribuzione manuale.
- Smoke test E2E manuale: install MSI + onboarding + apertura vault + chat reale + persistenza conversation.

Fuori scope Wave 1: tool use, MCP, multi-LLM, voice, mascot, macOS/Linux build, auto-update.

Exit criteria: tag `v0.1.0` pushed dopo smoke test PASS (Conv. 46 enforcement).

## Wave 2 — Memory Tree + connettori OAuth core (4-6 settimane)

Obiettivo: aggiungere conoscenza persistente strutturata (memory tree) e i primi 5-10 connettori OAuth verso servizi cloud essenziali al workflow Amodeo.

Deliverable:
- Memory Tree backend: nodi/edge in SQLite, sintesi gerarchica progressiva (algoritmo SCO-style, no vector DB).
- Memory Tree UI: force graph 2D/3D React, navigazione concetti.
- MCP server registry nel sidecar, gestione lifecycle (start/stop/health).
- 5-10 connettori OAuth target priorità Antonio:
  - Gmail (lettura/scrittura email)
  - Google Calendar (eventi)
  - Google Drive (file)
  - GitHub (issue, PR, commit)
  - Notion (database, page) — opzionale Wave 2
  - Slack — opzionale Wave 2
  - Linear — opzionale Wave 2
  - LinkedIn — opzionale (no MCP ufficiale, valutare)
- Anthropic Agent SDK con tool use abilitato per i connettori.
- Persistenza stato widget chat (Conv. 48 enforcement).
- Build macOS DMG universal2 (aarch64 + x86_64).
- Build Linux AppImage (Conv. 45).

Exit criteria: tag `v0.2.0` pushed dopo smoke test PASS su Windows + macOS + Linux. Almeno 5 connettori OAuth funzionanti end-to-end.

## Wave 3 — Multi-LLM router + voice + plugin system (4-6 settimane)

Obiettivo: disaccoppiare il valore consulenziale dal singolo AI provider, aggiungere voice come modalità di input/output, introdurre un sistema plug-in formale per skill di dominio.

Deliverable:
- Multi-LLM router nel sidecar:
  - Adapter Anthropic (già presente)
  - Adapter OpenAI
  - Adapter Google Gemini
  - Adapter locale via Ollama (opzionale)
  - Routing rules per task (reasoning vs fast vs vision)
  - Ipotesi tecnica: LiteLLM come libreria unificata. Decisione finale in fase di design Wave 3.
- Voice input STT:
  - Integrazione Whisper locale (preferito per privacy) o API
  - UI microfono in chat
- Voice output TTS:
  - Integrazione locale (es. Piper, Coqui) o API
  - Setting utente attiva/disattiva
- Plugin system formale:
  - `packages/agent-skills/` come catalogo skill markdown
  - Loader skill runtime nel sidecar
  - UI catalogo skill in app, attivazione/disattivazione runtime
- Auto-update Tauri Updater abilitato per MSI + DMG + AppImage (Conv. 45 lesson 2).
- Endpoint `latest.json` firmato Ed25519 su GitHub Releases.

Exit criteria: tag `v0.3.0` pushed dopo smoke test PASS. Almeno 2 provider LLM attivi e switchabili. Voice STT funzionante. Auto-update verificato su Windows.

## Wave 4 — 100+ integrazioni + mascot + auto-update produzione (8-12 settimane)

Obiettivo: scalare il numero di connettori OAuth a 100+ (parità con tool concorrenti di riferimento), aggiungere mascot opzionale per affinità con l'estetica desktop AI assistant, stabilizzare auto-update in produzione su tutti gli OS.

Deliverable:
- 100+ connettori MCP integrati, gestiti via registry pubblico MCP + adapter custom su `packages/integrations/`.
- Categorie connettori target:
  - Email/Messaging: Gmail, Outlook, Slack, Teams, Discord, Telegram, Signal
  - Calendar: Google Calendar, Outlook Calendar, Calendly, Fantastical
  - Storage: Drive, Dropbox, OneDrive, Box, iCloud, S3, Backblaze
  - Dev: GitHub, GitLab, Bitbucket, Linear, Jira, Trello, Asana
  - Productivity: Notion, Obsidian, Roam, Logseq, Apple Notes, OneNote
  - CRM: HubSpot, Salesforce, Pipedrive, Airtable
  - Finance: Stripe, Plaid, banche italiane (PSD2 via Saltedge)
  - Custom: connettori specifici workflow Amodeo (kDrive Infomaniak, normattiva.it scraper, EUR-Lex)
- Mascot opzionale (carry-over filosofico):
  - Asset 3D leggero (glTF) o sprite 2D animato
  - Stati: idle, listening, thinking, speaking, error
  - Setting utente per disattivazione totale (privacy)
- Auto-update produzione su tutti gli OS:
  - Pipeline CI matrix completa (Windows + macOS + Linux)
  - Signing Apple Developer ID (mac) — costo annuale da budgetare
  - Signing Windows certificate (msi) — costo annuale da budgetare
- Documentazione utente finale (carry-over Wave 4):
  - Manuale uso in italiano
  - Video onboarding 5-10 minuti
  - Quick reference connettori

Exit criteria: tag `v1.0.0` pushed dopo smoke test PASS su 3 OS. Auto-update verificato in produzione. Almeno 50 connettori OAuth funzionanti end-to-end (i 100+ è obiettivo a tendere post-v1.0.0).

## Note di pianificazione

1. **Le durate sono stime, non commitment**. Antonio sviluppa in parallelo al lavoro consulenziale full-time, le settimane non sono tutte uguali. Slittamenti +20% sono fisiologici.
2. **Ogni release wave passa per smoke test E2E manuale** (Conv. 46 enforcement). Niente tag se lo smoke non passa.
3. **Le wave non sono strettamente sequenziali**: in caso di blocchi su una wave, parti di wave successive possono essere anticipate (es. macOS build può essere anticipato a Wave 1 se serve per testing).
4. **Carry-over post-Wave 4**: localizzazione UI multi-lingua, mobile companion app (iOS/Android via Tauri mobile), modello SaaS opzionale per team (rinviato a v2.x).

## Backlog idee post-v1.0.0

- Plugin marketplace community (skill markdown condivisibili)
- Modalità "team" con vault sincronizzato fra più operatori (riferimento profilo Pietro nel workflow Amodeo)
- Companion mobile iOS/Android per ingestione veloce note e foto
- Integrazione computer use Anthropic SDK per automation desktop
- Cifratura at-rest del vault opzionale (BitLocker/FileVault wrapper)

## Riferimenti

- ADR 0001 — Scelta dello stack tecnologico
- ADR 0002 — Layout del monorepo
- `docs/ARCHITECTURE.md` — Vista architetturale 10000ft
- Workflow Amodeo: `CLAUDE.md` Second Brain, in particolare Conv. 46 (smoke test prima del tag), Conv. 45 (cross-platform matrix), Conv. 44 (debug Tauri 2/Python)
