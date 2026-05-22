# @sco/integrations — Sistema connettori OAuth

Pacchetto del monorepo SCO Compliance OS che ospita il sistema di integrazioni con provider esterni (Gmail, Google Calendar, Google Drive, Slack, GitHub, e oltre 50 connettori roadmap). Brandato SCO, scritto clean-room da zero, ispirato dalla filosofia industry-standard del provider-pattern OAuth 2.0.

## Filosofia

Il sistema adotta il **provider-pattern** con:

- **Classe astratta `BaseConnector`** (Python ABC) che definisce il contratto comune (slug, name, category, oauth_provider, scopes_required, hooks per OAuth flow + data fetch).
- **Implementazioni concrete** per ciascun provider (`GmailConnector`, `SlackConnector`, etc.) che ereditano dal base e implementano i dettagli provider-specifici.
- **Flow OAuth 2.0 standardizzato** (Authorization Code Grant + PKCE dove supportato), con scambio code → token, refresh token automatico, revoke su disconnessione.
- **Registry singleton** (`ConnectorRegistry`) che mappa slug → classe connector e abilita discovery dinamica lato API/UI.

## Architettura

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (Tauri WebView)                                    │
│  - UI lista connettori (icone + status)                      │
│  - "Connect" button → apre browser su authorization URL      │
│  - Polling status connessione                                │
└────────────────────┬────────────────────────────────────────┘
                     │ REST/IPC
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Backend (FastAPI sidecar PyInstaller)                       │
│  - /api/integrations/start (genera auth_url + state)         │
│  - /api/integrations/callback (riceve code, scambia token)   │
│  - /api/integrations/list (status per user_id)               │
│  - /api/integrations/disconnect                              │
│  - Scheduler fetch_data ogni N min (default 20)              │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴───────────────┐
        ▼                            ▼
┌──────────────────┐         ┌────────────────────────┐
│  OS Keyring      │         │  Provider API esterno  │
│  (token cifrati) │         │  (Google, Slack, GH)   │
└──────────────────┘         └────────────────────────┘
```

## Sicurezza

- **Token cifrati in OS keyring**: Windows Credential Manager / macOS Keychain / GNOME Keyring (Linux). Libreria Python [`keyring`](https://pypi.org/project/keyring/) come abstraction layer cross-platform.
- **MAI plaintext su disk**: nessun `tokens.json`, nessun database SQLite con token in chiaro. Il keyring è l'unico storage autorizzato.
- **OAuth state parameter**: ogni flow genera state casuale crittografico (`secrets.token_urlsafe(32)`) per anti-CSRF.
- **PKCE quando supportato**: code_verifier + code_challenge per provider che lo supportano (Google supporta, Slack no, GitHub sì).
- **Backend è proxy SOLO per token**: il data fetch (email, file, eventi) arriva dal provider al client, viene processato localmente nel Memory Tree, **MAI** transita per server SCO (zero-data architecture).

## Roadmap connettori (50 target)

Wave 1 (questo scaffolding — 5 connettori stub):

| Slug | Provider | Categoria | Wave |
|---|---|---|---|
| `gmail` | Google | Email | 1 |
| `google_calendar` | Google | Calendar | 1 |
| `google_drive` | Google | Storage | 1 |
| `slack` | Slack | Communication | 1 |
| `github` | GitHub | Code | 1 |

Wave 2+ (roadmap espansione):

| Categoria | Connettori target |
|---|---|
| Email | Outlook, ProtonMail, Fastmail |
| Calendar | Outlook Calendar, Apple Calendar, Cal.com |
| Storage | Dropbox, OneDrive, Box, iCloud Drive |
| Code | GitLab, Bitbucket, Codeberg |
| Project Mgmt | Linear, Jira, Asana, Trello, Notion, ClickUp |
| CRM | HubSpot, Salesforce, Pipedrive |
| Communication | Discord, Microsoft Teams, Telegram, WhatsApp Business |
| Social | LinkedIn, X/Twitter, Mastodon, Bluesky |
| Commerce | Shopify, Stripe, PayPal |
| Productivity | Todoist, Things, Obsidian Sync, Apple Notes |

Target finale: **50 connettori entro fine 2027**, con possibile espansione a 100 in base alla traction utente.

## Privacy

Architettura **zero-data**: il backend SCO è un proxy stateless per i token OAuth, non vede mai il contenuto dei dati utente. Il `fetch_data()` di ciascun connector:

1. Recupera tokens dal keyring locale del client.
2. Chiama l'API del provider (Gmail API, Slack API, etc.) direttamente dal client/sidecar locale.
3. Processa i dati e li scrive nel **Memory Tree locale** (filesystem markdown + JSON, pattern Karpathy three-layer + Conv. 43 Smart File Injection).

Nessun dato utente attraversa server SCO. I token cifrati restano sul dispositivo. Il fetch è on-device.

## Wave 1 — Scaffolding corrente

Vedi `CONTRIBUTING.md` per il template di aggiunta di un nuovo connettore. Vedi `docs/adr/0003-integrations-architecture.md` per il razionale architetturale completo.

Stato Wave 1: 5 stub `BaseConnector` concreti con OAuth flow scheletro + `fetch_data()` mock che ritorna `MemoryChunk` di esempio. Implementazione completa (chiamate reali API provider, gestione paginazione, parsing payload, error handling production-grade) è work-in-progress.

## Riferimenti

- [OAuth 2.0 Authorization Framework RFC 6749](https://datatracker.ietf.org/doc/html/rfc6749)
- [OAuth 2.0 PKCE RFC 7636](https://datatracker.ietf.org/doc/html/rfc7636)
- [Google OAuth 2.0 docs](https://developers.google.com/identity/protocols/oauth2)
- [Slack OAuth v2 docs](https://api.slack.com/authentication/oauth-v2)
- [GitHub OAuth docs](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps)
- [Python `keyring` library](https://pypi.org/project/keyring/)
