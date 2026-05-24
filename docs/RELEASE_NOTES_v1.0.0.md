# SCO Compliance OS v1.0.0

| Versione | Data | Tipo | Piattaforme |
|---|---|---|---|
| **v1.0.0** | 24/05/2026 | General Availability | Windows MSI · macOS DMG universal · Linux AppImage |

---

## Cos'è SCO Compliance OS

Sistema operativo AI desktop pensato per il consulente normativo italiano. Una postazione di lavoro privata, locale di default, che integra agente multi-LLM, vault editabile, memoria a lungo termine, voce on-device e oltre 100 connettori OAuth. I dati restano sul computer del consulente, salvo decisione esplicita.

## Cosa contiene v1.0.0

### Knowledge Layer

Wiki SCO a cinque categorie (`raw`, `sources`, `entities`, `concepts`, `synthesis`, `glossari`) come knowledge base di compliance navigabile. Memory Tree con sintesi progressiva a quattro fasi (L0 raw, L1 compressed, L2 synthesis, L3 canonical) tramite estrattore Claude Haiku, senza vector database esterno. Vault auto-ingest su sette estensioni (`.md`, `.pdf`, `.docx`, `.xlsx`, `.pptx`, `.txt`, `.json`) con file watcher live. Skill loader runtime con skill `os-setup` che profila l'utente al primo avvio.

### Multi-LLM router

Routing trasparente fra quattro provider: Anthropic (Claude Sonnet 4.6 default), OpenAI, Google Gemini, Ollama in locale per il fallback offline. Tre profili: reasoning, fast, vision. Chiavi API per tenant gestite dal pannello SaaS admin.

### Voce on-device

STT con Whisper.cpp (`tiny`, `base`, `small`, `medium`). TTS con Piper, voci italiane selezionabili. Nessun audio inviato a servizi terzi senza consenso.

### Interfaccia utente

Command Palette `⌘K`, BottomTabBar per chat, vault, memoria e impostazioni. MeshGradient WebGL e mascotte SVG 2D opzionale. Palette brand SCO navy `#302e5c`, blu `#0074b4`, ambra `#ffa727`, tipografia Inter + Source Code Pro.

### Integrazioni OAuth

Cinque connettori cablati in v1.0.0: Gmail, Google Calendar, Google Drive, Slack, GitHub. Tutti opt-in, scope minimo, revocabili dal pannello impostazioni. Il protocollo MCP rende l'aggiunta di nuovi connettori una questione di adapter.

### SaaS admin

Console completa: tenant, licenze, audit log, pricing plan, usage telemetry, membri del team, chiavi API multi-provider. Deploy serverless su Vercel. Separazione netta fra dati operativi del cliente (locali) e metadati di licenza (cloud).

### Privacy by design

Default non negoziabile. Niente telemetria attiva, niente egress automatico, niente upload silenziosi. I documenti del cliente restano sul disco del consulente, le credenziali OAuth vivono in keyring di sistema.

## Per chi è

Consulenti compliance italiani, RSPP, lead auditor ISO 27001 e 9001, DPO, avvocati che gestiscono adempimenti normativi sostenuti (NIS 2 D.Lgs. 138/2024, ISO/IEC 27001:2022, AI Act Reg. UE 2024/1689, GDPR, sicurezza sul lavoro D.Lgs. 81/2008, accreditamento sanitario).

## Come installare

| OS | Artefatto firmato Ed25519 | Auto-update |
|---|---|---|
| Windows 10 64-bit o superiore | `sco-compliance-os_1.0.0_x64_en-US.msi` | Sì |
| macOS 11 o superiore (Intel + Apple Silicon) | `sco-compliance-os_1.0.0_universal.dmg` | Sì |
| Linux x86_64 | `sco-compliance-os_1.0.0_amd64.AppImage` | Sì |

L'aggiornamento automatico Tauri Updater verifica la firma Ed25519 prima dell'installazione del delta, senza richiedere il package manager di sistema.

## Stack tecnologico

Tauri 2 + Rust per la shell desktop. React 19 + TypeScript 5.8 + Vite 6 + Tailwind 4 per la UI. Python 3.12 + FastAPI sidecar bundled PyInstaller per il backend agente. Anthropic Claude Sonnet 4.6 come provider primario. Whisper.cpp e Piper per la voce on-device. Model Context Protocol per i connettori. Next.js su Vercel + Supabase per il SaaS admin.

## Licensing

Software proprietario chiuso, copyright SCO Solution Consulting srls. Distribuzione tramite license-key per tenant generata dal pannello SaaS admin. Tre piani: Starter (single seat), Professional (team fino a 5 seat), Enterprise (team illimitati, SLA dedicato, supporto prioritario). Richiesta licenze a `commerciale@scosolution.it`.

## Carry-over v1.1 e successive

Cinque filoni di lavoro pianificati per le prossime release.

1. **GitHub Copilot connector** per integrare suggerimenti di codice direttamente nell'agente.
2. **LinkedIn connector** per la pubblicazione automatizzata dei contenuti editoriali del consulente.
3. **Notion sync bidirezionale** per chi tiene knowledge base su Notion e vuole portarla nel vault locale (e viceversa).
4. **Voice clone TTS personalizzato** per registrare voce e timbro del consulente, da usare nella sintesi audio dei documenti.
5. **Plugin marketplace** per distribuire skill di dominio sviluppate da terze parti, con revisione editoriale SCO.

Le scadenze indicative saranno pubblicate nella `docs/ROADMAP.md` e nelle release notes successive.
