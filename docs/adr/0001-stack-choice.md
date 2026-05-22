# ADR 0001 — Scelta dello stack tecnologico

- **Status**: Accettato
- **Data**: 2026-05-21
- **Decisore**: Antonio Amodeo (titolare SCO Solution Consulting srls)
- **Supersedes**: nessuno

## Contesto

SCO Compliance OS è un'applicazione desktop AI per il lavoro consulenziale di Antonio Amodeo (cybersecurity, qualità sanitaria, compliance normativa italiana). Vincoli operativi rilevati durante la prima incarnazione interna `sco-agent-local` (v0.1.0 → v0.6.20, ~150 commit in 6 mesi):

1. **Cross-platform obbligatorio**, distribuzione Windows + macOS + Linux su 3 PC personali Antonio + clienti.
2. **Locale-first, privacy by default**, niente egress automatico verso il cloud, niente telemetria silenziosa.
3. **Bundle desktop autocontenuto**, l'utente cliente non installa Python / Node / Rust separatamente.
4. **UI ricca con streaming chat real-time**, markdown rendering, code highlight, force graph 2D/3D per vault.
5. **Backend AI estendibile**, supporto attuale Anthropic Agent SDK con previsione di multi-LLM router in Wave 3.
6. **Integrazioni esterne plug-in**, target 100+ connettori OAuth verso servizi cloud in Wave 4.

L'esperienza pregressa su `sco-agent-local` ha validato in produzione una specifica combinazione tecnologica. Riusarla riduce il rischio di "second-system effect" e permette di concentrare l'energia di sviluppo sulle feature nuove.

## Decisione

Lo stack adottato per SCO Compliance OS è il seguente.

### Layer shell desktop: Tauri 2 + Rust

Tauri 2.x come framework di shell desktop, con backend Rust per gli IPC commands e i plugin nativi. Vantaggi rispetto a Electron: footprint MSI ridotto (~10 MB vs ~120 MB), uso della WebView di sistema invece di Chromium bundlato, plugin updater nativo con firma Ed25519, supporto matrix cross-OS via tauri-action GitHub Action.

Vincoli noti (riferimenti Conv. 44 e Conv. 45 del workflow Amodeo):
- PyInstaller non cross-compila: serve CI matrix con runner separati per Windows + macOS + Linux.
- Tauri 2 WebView2 su Windows usa origin `http://tauri.localhost`: il backend FastAPI deve includerlo nel CORS `allow_origins`.
- Tauri Updater supporta MSI/DMG/AppImage ma non DEB/RPM: su Linux si distribuisce solo AppImage.

### Layer UI: React 19 + TypeScript 5.8 + Vite 6 + Tailwind 4

React 19 con server components disattivati (siamo client-only in Tauri), TypeScript in modalità strict, Vite 6 come dev server e bundler di produzione, Tailwind CSS 4 con plugin nativo `@tailwindcss/vite` (no PostCSS legacy). Stack validato in `sco-agent-local`, ottima HMR experience in dev.

### Layer backend agente: Python 3.11+ + FastAPI + Anthropic Agent SDK

Backend sidecar in Python perché:
- L'SDK Anthropic ufficiale più ricco è in Python (Agent SDK con tool use, computer use, prompt caching, batch).
- L'ecosistema MCP Python è maturo e ben documentato.
- L'ecosistema librerie compliance normativa italiana (parser PDF, OCR, generazione docx, manipolazione xlsx) è prevalentemente Python.

FastAPI per gli endpoint HTTP + SSE streaming. Sidecar bundle via PyInstaller. Anthropic Agent SDK come motore agente con tool calling completo. uv come package manager (più veloce di pip, lockfile deterministico).

### Layer connettori: MCP (Model Context Protocol)

MCP come protocollo unificato per i connettori OAuth verso servizi cloud (Gmail, Calendar, Slack, GitHub, Notion, Drive, ecc.). Vantaggi:
- Spec aperta gestita da Anthropic, in adozione anche da altri provider AI.
- Disaccoppia l'agente dal singolo connettore: si aggiungono MCP server senza modificare il core.
- Ecosistema MCP server in crescita rapida (registry pubblici, server community-maintained).

### Package management: pnpm 10 (frontend monorepo) + uv (backend Python)

pnpm per il monorepo frontend con workspace `frontend/` + `packages/*`. uv per il backend Python. Distinzione netta: pnpm non gestisce Python, uv non gestisce JavaScript. Niente Lerna, niente Nx (overkill per la dimensione attuale).

### CI/CD: GitHub Actions matrix cross-OS

Pipeline su 3 runner paralleli (`windows-latest`, `macos-latest`, `ubuntu-22.04`) per build Tauri + PyInstaller sidecar. Tauri Updater endpoint unificato `latest.json` su GitHub Releases con firma Ed25519 per MSI + DMG + AppImage.

## Conseguenze

### Positive

- **Time-to-market accelerato** rispetto a uno stack greenfield: i pattern Tauri 2 + Python sidecar + PyInstaller + CORS WebView2 sono già stati validati in produzione su `sco-agent-local`.
- **Footprint installer contenuto**: MSI Windows ~30 MB completo di sidecar Python, accettabile per distribuzione consulenziale.
- **Privacy nativa**: tutto il flusso agente passa per il backend locale, niente proxy cloud Anthropic se non per la singola chiamata API. Telemetria opt-in di default disattivata.
- **Estendibilità garantita**: il protocollo MCP scollega l'aggiunta di nuovi connettori dalla modifica del core agente.
- **Cross-OS reale**: la matrix CI replica la pipeline di `sco-agent-local` v0.4.0+ già in produzione.

### Negative

- **Tre toolchain da mantenere**: Rust + Python + Node/TypeScript. Setup iniziale per nuovi PC richiede ~30 minuti.
- **PyInstaller non cross-compila**: la build Mac va fatta su runner Mac, la build Linux su runner Linux, costo CI minuto runner Mac > Linux > Windows.
- **Tauri 2 ancora giovane**: API in evoluzione, alcuni plugin (es. dialog, opener) hanno breaking change minori fra minor version. Mitigazione: lock di versione esplicito in package.json, upgrade controllati.
- **Anthropic Agent SDK in lock-in temporaneo**: per Wave 1+2 lo stack è single-LLM Anthropic. Il multi-LLM router (Wave 3) richiede uno strato di adattamento aggiuntivo (ipotesi tecnica: LiteLLM o adapter custom).

### Neutre

- **Familiarità preesistente**: Antonio ha già esperienza operativa con tutti i layer di questo stack. Curva di onboarding nulla.
- **Documentazione e community**: tutti i layer scelti hanno documentazione ufficiale ricca, ecosistema attivo, supporto LLM-assistito affidabile per troubleshooting.

## Alternative considerate e scartate

| Alternativa | Motivo dello scarto |
|---|---|
| Electron + Node.js full-stack | Footprint installer eccessivo (~120 MB), ecosistema AI Python più ricco del Node, già scartato in sco-agent-local |
| Flutter desktop | Linguaggio Dart fuori dallo stack di Antonio, ecosistema librerie compliance italiana inesistente |
| Native Win32 + .NET MAUI | Cross-platform debole, lock-in ecosistema Microsoft, no privacy by default |
| Wails (Go + WebView) | Ecosistema AI Go meno maturo, niente SDK Anthropic ufficiale Go |
| Backend in Go o Rust | Ecosistema librerie compliance italiana assente, ecosistema MCP in Python più maturo |
| OpenAI SDK invece di Anthropic | Antonio è cliente Anthropic da 2 anni, Agent SDK Anthropic è più maturo su tool use end-to-end |

## Riferimenti

- Esperienza pregressa: `C:\Users\aoedo\Progetti\sco-agent-local` (v0.1.0 → v0.6.20)
- Workflow Amodeo, convenzioni operative: `CLAUDE.md` del Second Brain, Conv. 44 e Conv. 45
- Tauri 2 docs: https://v2.tauri.app
- Anthropic Agent SDK: https://docs.anthropic.com/agents
- Model Context Protocol: https://modelcontextprotocol.io
