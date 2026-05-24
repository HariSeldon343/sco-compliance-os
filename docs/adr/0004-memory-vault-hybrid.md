# ADR 0004 — Architettura ibrida Memory Tree + Vault SCO

- **Stato**: Accepted
- **Data**: 2026-05-21
- **Autori**: Agent MEMORY-VAULT (sotto orchestrazione main agent), pattern multi-agent Conv. 33+34
- **Decisori**: Antonio Silvestro Amodeo (committente sco-compliance-os)
- **Riferimenti**: vault Antonio `C:\Users\aoedo\Desktop\Second Brain\CLAUDE.md` sezione INGEST, Ondate 2-3-4 del modello tipizzato SCO

## Contesto

`sco-compliance-os` nasce come app desktop AI assistant brandata SCO per il lavoro consulenziale di Antonio Amodeo (cybersecurity, qualità sanitaria, compliance normativa, ingegneria clinica) e dei suoi colleghi. Filosofia simile a OpenHuman ma scritta clean-room da zero. Deve supportare due workload molto diversi:

1. **Ingest auto da connettori OAuth** (email Gmail, eventi calendar Google, file drive, ecc.) + **user uploads** ad-hoc di documenti che l'utente trascina nella chat. Volume previsto: migliaia di chunks/cliente, retention 12-24 mesi, query "rispondi a questa email", "che eventi avevo settimana scorsa", "cerca il PDF del bando ANAC dell'altra settimana".
2. **Compliance ontology curata cliente-per-cliente**: ogni cliente ha un vault SCO con `_index.md` che dichiara `applica_entity[]`, `pertinenza_in_verifica[]`, `fornitore_di[]`; ogni entity wiki ha `entity_type`, `entity_subtype`, `ambito_canonico`, `relationships[]`. Volume per cliente: 50-300 markdown files. Query consulenziali: "chi sono i miei clienti soggetti NIS 2 essenziali?", "quali finding aperti ho su Don Calabria?", "TecnoSys è fornitore critico di chi?", "matrice cross-framework 27001/NIS2/20000-1".

Le due workload hanno requisiti opposti:

- Workload 1: write-heavy, append-only, retention bounded, schema flat, ranking BM25 + recency sufficiente.
- Workload 2: read-heavy, write deliberato e curato da Antonio, schema tipizzato (vocabolari chiusi Ondate 2-3-4), query graph-traversal (relationships, reverse edge cliente→entity), zero tolleranza per hallucination.

## Decisione

Adottiamo un'architettura **ibrida a due layer separati con glue layer**:

### Layer 1 — Memory Tree (services/memory/)

- Token-aware markdown chunker (tiktoken-based, max 3000 token/chunk, overlap 200).
- Hierarchical summary tree via summarizer.py (wave 1 stub, wave 2 LLM).
- BM25 scoring + recency boost + manual boost (no embedding wave 1).
- Storage: SQLite locale `~/.sco-compliance-os/memory_tree.db` via aiosqlite.
- Source types: `connector` | `user_upload` | `vault_ingest` | `manual`.
- Provenance metadata completi (Conv. 43 SMART FILE INJECTION enforcement).

### Layer 2 — Vault SCO (services/vault/)

- Filesystem markdown autoritativo (`vault_root/` cliente-per-cliente).
- Frontmatter YAML tipizzato secondo le 8 dimensioni Ondate 2-3-4 del vault Antonio (fonte autoritativa: `C:\Users\aoedo\Desktop\Second Brain\CLAUDE.md` sezione INGEST):
  - Dim 1: `entity_type` (7 valori chiusi)
  - Dim 2: `entity_subtype` (gerarchico)
  - Dim 3: `ambito_canonico` (17 valori chiusi)
  - Dim 4: `relationships[]` (8 tipi chiusi)
  - Dim 5: `applica_entity[]` (9 ruoli chiusi)
  - Dim 6: `entity_type=scadenza` (sub-tipo dedicato)
  - Dim 7: `pertinenza_in_verifica[]` (qualifiche ambigue strutturate)
  - Dim 8: `fornitore_di[]` (edge cliente↔cliente asimmetrico)
- Index SQLite locale `~/.sco-compliance-os/vault_index.db` (cache query veloce, no source of truth).
- Query layer cross-cliente: `clients_applying_entity`, `pertinenze_in_verifica_open`, `suppliers_of`, `entities_by_ambito`, `entities_with_relationships`.
- Validazione vocabolari chiusi a parse time, warning su violazioni (mai correzione automatica — pattern Conv. 12 "estensione vocabolario non approvato → posporre").

### Layer 3 — Glue (services/glue.py)

- `unified_search(query)` instrada la query al layer corretto:
  - Heuristics regex: `is_compliance_query()` rileva sigle norme (ISO, D.Lgs., Reg. UE, NIS 2, GDPR, ACN, ecc.) → priorità Vault.
  - `detect_ambito_hint()` mappa keyword query → `ambito_canonico` per filtrare entity hits.
  - `_extract_norma_slugs()` estrae slug entity dalla query (`D.Lgs. 138/2024` → `d-lgs-138-2024`) per reverse-edge `clients_applying_entity`.
- Ranking combinato: vault hits ottengono boost x2 se compliance-flavored; memory hits scoring BM25 puro.

## Conseguenze

### Positive

- **Separazione semantica netta**: dati freschi/ephemeri (Memory Tree) vs ontology curata (Vault). L'utente non confonde una nota email con un finding NIS 2.
- **Zero hallucination su compliance**: il vault è curato da Antonio, le query critiche ("quali clienti sono fornitori critici di soggetti essenziali?") leggono solo dati strutturati.
- **Performance bilanciata**: Memory Tree gestisce volume con BM25 + indici source_type; Vault index serve query graph cross-cliente con join in-memory su JSON arrays.
- **Coerenza vault Antonio**: i vocabolari sono allineati 1:1 con `Second Brain/CLAUDE.md` — un cliente sco-compliance-os usa lo stesso modello di Antonio.
- **Estendibilità**: wave 2 può aggiungere embedding semantici al Memory Tree e watch mode al Vault senza toccare l'altro layer.

### Negative

- **Complessità +N**: due DB SQLite invece di uno, due schemi, due pipeline ingest. Costo mitigato dall'isolamento netto (zero foreign key cross-DB).
- **Onere di scrittura Vault**: l'utente (o sistema) deve produrre `_index.md` cliente con frontmatter tipizzato corretto. La frizione è compensata dal valore consulenziale unico — un vault SCO popolato è asset compounding.
- **Glue heuristics regex-based**: in wave 1 può sbagliare classificazione query borderline (es. "TecnoSys ha problemi cyber" è vault o memory?). Mitigato da fallback memory sempre attivo.

### Trade-off rifiutati

- **RAG con vector DB unificato**: rifiutato perché perderebbe la struttura tipizzata SCO (relationships, vocabolari chiusi, edge cliente↔entity). Pattern LLM Wiki di SCO sostituisce RAG fino a ~100 fonti/cliente.
- **Memory Tree-only**: rifiutato perché le query consulenziali cross-cliente ("chi sono i miei soggetti essenziali NIS 2?") richiedono graph traversal su edge tipizzati, non similarity search.
- **Vault SCO-only**: rifiutato perché ingest auto da connettori OAuth produce volume incompatibile con la cura manuale richiesta dal vault. Le email non vengono "promosse a entity wiki" automaticamente.

## Decisioni autonome documentate

- **No embedding in wave 1**: BM25 + recency è sufficiente per query lessicali italiane di alta precisione (terminologia normativa esatta). Embedding rinviato wave 2 con scelta fra Voyage AI cloud vs sentence-transformers on-device.
- **No SQLAlchemy**: uso diretto `aiosqlite` per zero overhead ORM e parità con pattern `sco-agent-local/conversations/store.py`.
- **No watchdog wave 1**: `watch_vault()` solleva NotImplementedError esplicito. Sync manuale via `sync_vault()` a startup app e on-demand.
- **Stub LLM summarizer**: `StubLLMClient` ritorna placeholder esplicito che NON simula intelligenza (pattern SCO "no hallucination"). Wave 2 integrare claude-haiku per cost-effective.

## Riferimenti

- `services/memory/{chunker,scorer,store,summarizer,ingest}.py` — Memory Tree
- `services/vault/{parser,scanner,query,sync}.py` — Vault SCO
- `services/glue.py` — Unified search layer
- `Second Brain/CLAUDE.md` sezione INGEST — vocabolari Ondate 2-3-4 (fonte autoritativa)
- Conv. 33+34 multi-agent pattern, Conv. 35 RESEARCH-BEFORE-ACT, Conv. 43 SMART FILE INJECTION
