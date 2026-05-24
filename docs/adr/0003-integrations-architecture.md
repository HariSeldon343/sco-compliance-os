# ADR 0003 — Architettura del sistema di integrazioni OAuth

- **Status**: Accepted
- **Date**: 2026-05-21
- **Deciders**: Antonio Amodeo (SCO), Agent INTEGRATIONS (multi-agent Wave 1 scaffolding)
- **Related**: ADR 0001 (Stack choice), Conv. 33+34 (multi-agent + spot check), Conv. 35 (research before act), Conv. 43 (smart file injection), Conv. 47 (single source of truth), Conv. 48 (backend SoT widget chat).

## Contesto

SCO Compliance OS è un'app desktop AI assistant (Tauri 2 + Python sidecar PyInstaller) brandata SCO che deve supportare integrazioni con provider esterni (Gmail, Slack, GitHub, Google Calendar, Google Drive in Wave 1, fino a 50-100 connettori nel medio termine). L'obiettivo è permettere all'utente di portare nel proprio "Memory Tree" locale dati strutturati dai propri account (email, eventi, file, messaggi, PR/issue) per consultazione AI-assisted.

Vincoli:
- **Clean-room**: zero codice copiato da progetti esistenti (in particolare OpenHuman, 24.7k stars GitHub).
- **Privacy zero-data**: i dati utente NON devono mai transitare per server SCO. Solo token cifrati restano lato client.
- **Cross-platform**: Windows + macOS + Linux (Conv. 45 enforcement).
- **Estensibilità**: aggiungere il 51° connettore non deve richiedere refactor di sistema.

## Decisione

Adottiamo un **provider-pattern con classe astratta `BaseConnector` (Python ABC) + registry singleton + token store cifrato OS keyring + scheduler asyncio**. Cinque sotto-decisioni motivate:

### 1. Perché provider-pattern + ABC

Alternative valutate:
- **Function-based handlers** (dict di funzioni per provider): più semplice ma perde type-safety + dispersione logica fetch/refresh/disconnect in moduli scollegati.
- **Plugin esterni dinamici** (entry points setuptools): potenza eccessiva per Wave 1; aggiunge complessità di packaging.
- **ABC + classi concrete** (scelta): contratto stabile garantito dal Python ABC, type hints completi, IDE autocomplete, mockable per test, registry semplice via decorator.

Pattern SCO "schema is the product": le dataclass tipizzate (`OAuthTokens`, `MemoryChunk`, `OAuthError`) sono il contratto stabile; le implementazioni concrete dei connettori sono interscambiabili. Aggiungere un nuovo connettore = 1 file Python + 1 decorator `@connector`.

### 2. Perché token in OS keyring vs DB cifrato

Alternative valutate:
- **DB SQLite cifrato (SQLCipher)**: cifratura forte ma richiede gestione master key (dove vive? in env var? in altro keyring? → ricorsione). Aggiunge dipendenza nativa SQLCipher complessa da PyInstaller-bundle.
- **JSON cifrato con Fernet + password utente**: richiede password addizionale dell'utente solo per integrazioni; UX scadente.
- **OS keyring nativo** (scelta): Windows Credential Manager + macOS Keychain + GNOME Keyring/KWallet già cifrati a livello OS, sbloccati al login utente, nessuna dipendenza extra (Python `keyring` libreria pure-Python con backend nativi). Pattern Conv. 35 RESEARCH-BEFORE-ACT: libreria `keyring` ben documentata e maintained (`https://pypi.org/project/keyring/`).

Trade-off accettato: enumerazione provider richiede probe via lista nota di slug (workaround in `token_store.list_providers`). Costo minimo dato che il registry conosce comunque tutti gli slug.

### 3. Perché 5 connettori in Wave 1

Alternative valutate:
- **1 connettore solo (Gmail)**: troppo poco per validare l'astrazione `BaseConnector`. Rischio di hardcoding logiche Google-specifiche nel base.
- **10+ connettori**: timeboxing scaffolding eccede ragionevole (1 giorno multi-agent).
- **5 connettori** (scelta): coprono **3 provider OAuth distinti** (Google = Gmail + Calendar + Drive; Slack; GitHub) con specificità diverse (Google con PKCE + access_type=offline, Slack con scope CSV + no PKCE + no refresh default, GitHub con token non-expiring default + opt-in expiration). Sufficiente per stress-testare il pattern.

Spot check Conv. 34 enforcement: dopo Wave 1 verifichiamo che `BaseConnector` non abbia avuto bisogno di estensioni provider-specifiche (escape hatch). Se sì, refactor prima di Wave 2.

### 4. Decisione su Composio (NO per Wave 1)

[Composio](https://composio.dev/) è una piattaforma SaaS che offre 250+ connettori già pronti tramite SDK. Valutata e **scartata per Wave 1** per tre ragioni:

1. **Costo**: tier free limitato (200 actions/month), pricing scala con utilizzo. Per app consumer-grade desktop con 1000+ utenti finali → costo significativo.
2. **Dipendenza terza parte**: l'intera roadmap connettori dipenderebbe dalla survival di Composio + dalla loro roadmap di nuovi provider. Lock-in tecnologico forte.
3. **Privacy zero-data conflict**: Composio è SaaS proxy: i dati utente passano per i loro server per ottenere l'astrazione. Conflitto con il vincolo zero-data di SCO Compliance OS.

**Rivalutazione Wave 3+**: se nella Wave 2 il pattern provider-by-provider mostra friction insostenibile (es. 50 connettori = 50 file da scrivere e maintenare), valutiamo Composio o equivalenti (Pipedream, Pizzly) come **opzionale** per provider long-tail, mantenendo i top 10 implementati nativamente per privacy.

### 5. Scheduler asyncio (no APScheduler)

Per Wave 1 lo scheduler è un loop `asyncio` semplice (`while self._running: ... await asyncio.sleep(interval)`). APScheduler valutato e scartato: aggiunge dipendenza con cron-like expressions inutilmente potente per il loop singolo. Refactor a APScheduler accettabile in Wave 2+ se servono trigger sofisticati (es. fetch on-demand triggered da webhook + cron mix).

## Conseguenze

### Positive

- **Single source of truth** lato token: il keyring OS è l'unica fonte autoritativa, niente duplicazione DB/file. Pattern Conv. 47/48 enforcement.
- **Pattern SCO "no edit retroattivo"**: aggiungere nuovi connettori non modifica `BaseConnector`; le 5 dataclass sono stabili.
- **Test isolabili**: `BaseConnector` mockabile via `unittest.mock`; ogni connector testabile in isolamento.
- **Privacy by design**: zero dati utente lato server SCO. Compliance GDPR by architecture.
- **Type safety**: type hints completi Python 3.12 + TypeScript types in `packages/integrations/types.ts`.

### Negative

- **Implementazione manuale per provider**: ogni provider richiede ~150-200 righe di codice (vs ~10 con Composio). Costo mitigato dalla riusabilità del template.
- **Enumerazione keyring**: probe via list per identificare provider connessi (limite cross-platform keyring). Costo trascurabile dato il numero piccolo di connettori.
- **No webhook real-time in Wave 1**: solo polling ogni 20 min. Webhook deferred a Wave 2+ (richiede backend SCO esposto con tunnel — complica privacy zero-data).

## Roadmap espansione

| Wave | Periodo | Connettori | Feature aggiunte |
|---|---|---|---|
| 1 (scaffolding) | 2026-05-21 | Gmail, GoogleCalendar, GoogleDrive, Slack, GitHub (stub) | provider pattern, registry, token store, scheduler stub |
| 2 (Wave 1 fully functional) | 2026-06 | stessi 5, ma con httpx reali + paginazione + parsing | OAuth flow E2E + fetch reale + Memory Tree integration |
| 3 (top 15) | 2026-Q3 | + Outlook, Notion, Linear, Dropbox, HubSpot, Discord, GitLab, Bitbucket, Salesforce, Stripe | webhook opt-in, UI gestione granulare scopes |
| 4 (long tail) | 2026-Q4+ | fino a 50 connettori | rivalutazione Composio per long-tail |

## Riferimenti

- `packages/integrations/README.md` — overview package
- `packages/integrations/CONTRIBUTING.md` — guida aggiunta nuovo connector
- `backend/sco_compliance_os/services/integrations/base.py` — classe astratta
- [OAuth 2.0 RFC 6749](https://datatracker.ietf.org/doc/html/rfc6749)
- [PKCE RFC 7636](https://datatracker.ietf.org/doc/html/rfc7636)
- [Python `keyring`](https://pypi.org/project/keyring/)
- [Composio platform](https://composio.dev/) (rivalutazione Wave 3+)
