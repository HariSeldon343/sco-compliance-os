# Conversation Viewer — jarvis &lt;&gt; codex

Mini interfaccia grafica che mostra **in tempo reale** lo streaming delle conversazioni fra jarvis (Claude) e codex (Codex CLI) prodotte dai workflow Conv. 50 (orchestrator `agent-bridge-mcp` V2.1).

## A cosa serve

Quando lanci un workflow a 4 mani jarvis+codex, l'orchestratore scrive un file `conversation-<timestamp>.md` nella root del progetto. Questo viewer:

- **Lista** tutte le conversazioni (live + storico) nella colonna di sinistra
- **Mostra in tempo reale** la conversazione selezionata, con i messaggi che appaiono mentre il workflow gira (polling 1.5s + auto-scroll)
- **Colora** i turni: blu = jarvis, verde = codex, giallo = orchestratore
- Badge **LIVE** verde pulsante sulle chat con un workflow attivo (file modificato negli ultimi 10 secondi)

## Avvio

Doppio click su `start.bat`, oppure:

```powershell
.\start.ps1
```

Oppure manualmente:

```powershell
cd tools\conversation-viewer
..\..\backend\.venv\Scripts\python.exe server.py
```

Poi apri **http://localhost:9000** nel browser.

## Come funziona

- `server.py` — mini-server FastAPI (porta 9000):
  - `GET /` pagina HTML
  - `GET /api/conversations` lista JSON dei `conversation-*.md` (mtime desc)
  - `GET /api/conversation?file=<rel>` contenuto raw di un file (guard path traversal)
- `index.html` — pagina vanilla JS (zero dipendenze CDN): polling lista 3s + polling contenuto 1.5s + render colorato custom + auto-scroll intelligente (segue il fondo solo se eri gia in fondo).

I file `conversation-*.md` sono cercati nella root di `sco-compliance-os/` + sottocartelle fino a 2 livelli (escluse node_modules, target, .venv, dist, build, .git).

## Pre-requisiti

- Python 3.12 con `fastapi` + `uvicorn` (gia presenti nel `backend/.venv` del progetto).
- Nessuna dipendenza frontend (render markdown custom inline).
