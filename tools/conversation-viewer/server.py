"""Conversation Viewer — mini server per visualizzare in tempo reale le
conversazioni jarvis <-> codex prodotte dai workflow Conv. 50 (orchestrator
agent-bridge-mcp V2.1).

Avvio:
    python server.py
    -> http://localhost:9000

Endpoint:
    GET /                       pagina HTML viewer
    GET /api/conversations      lista JSON dei conversation-*.md (mtime desc)
    GET /api/conversation?file= contenuto raw di un conversation-*.md

I file conversation-*.md sono cercati nella root del progetto sco-compliance-os
(parent di tools/conversation-viewer/) + sottocartelle fino a 2 livelli.
"""

from __future__ import annotations

import time
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

# server.py -> tools/conversation-viewer/ -> tools/ -> sco-compliance-os/
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
INDEX_HTML = Path(__file__).resolve().parent / "index.html"
CONV_GLOB = "conversation-*.md"
ACTIVE_THRESHOLD_SECONDS = 10  # file modificato di recente = workflow live

app = FastAPI(title="Conversation Viewer jarvis <-> codex")


def _find_conversations() -> list[dict]:
    """Trova i conversation-*.md in root + sottocartelle (fino a 2 livelli),
    dedup per path relativo, ordina per mtime desc."""
    patterns = [CONV_GLOB, f"*/{CONV_GLOB}", f"*/*/{CONV_GLOB}"]
    found: dict[str, Path] = {}
    for pat in patterns:
        for f in PROJECT_ROOT.glob(pat):
            # escludi node_modules / target / .venv per sicurezza performance
            rel = f.relative_to(PROJECT_ROOT)
            parts = set(rel.parts)
            if parts & {"node_modules", "target", ".venv", "dist", "build", ".git"}:
                continue
            found[str(rel)] = f
    now = time.time()
    out: list[dict] = []
    for rel, f in found.items():
        try:
            st = f.stat()
        except OSError:
            continue
        out.append(
            {
                "name": f.name,
                "rel": rel.replace("\\", "/"),
                "size": st.st_size,
                "mtime": st.st_mtime,
                "is_active": (now - st.st_mtime) < ACTIVE_THRESHOLD_SECONDS,
            }
        )
    out.sort(key=lambda x: x["mtime"], reverse=True)
    return out


def _safe_resolve(rel: str) -> Path:
    """Guard path traversal: solo conversation-*.md sotto PROJECT_ROOT."""
    candidate = (PROJECT_ROOT / rel).resolve()
    root_resolved = PROJECT_ROOT.resolve()
    if not str(candidate).startswith(str(root_resolved)):
        raise HTTPException(status_code=403, detail="path fuori dal progetto")
    if not candidate.name.startswith("conversation-") or candidate.suffix != ".md":
        raise HTTPException(status_code=403, detail="solo file conversation-*.md")
    if not candidate.exists():
        raise HTTPException(status_code=404, detail="file non trovato")
    return candidate


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    if not INDEX_HTML.exists():
        raise HTTPException(status_code=500, detail="index.html mancante")
    return INDEX_HTML.read_text(encoding="utf-8")


@app.get("/api/conversations")
def list_conversations() -> JSONResponse:
    return JSONResponse(_find_conversations())


@app.get("/api/conversation", response_class=PlainTextResponse)
def get_conversation(
    file: str = Query(..., description="path relativo del file"),
) -> str:
    path = _safe_resolve(file)
    return path.read_text(encoding="utf-8", errors="replace")


def main() -> None:
    print("Conversation Viewer jarvis <-> codex")
    print(f"  project root: {PROJECT_ROOT}")
    print("  apri: http://localhost:9000")
    print("  Ctrl+C per fermare")
    uvicorn.run(app, host="127.0.0.1", port=9000, log_level="warning")


if __name__ == "__main__":
    main()
