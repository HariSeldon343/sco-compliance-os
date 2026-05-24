---
type: readme
title: "wiki_seed - template seed per nuovi vault scaffolded"
status: active
last_reviewed: 2026-05-24
tags: [scaffold, template, wiki, seed]
---

## 1. Cosa e wiki_seed/

La cartella `wiki_seed/` contiene il **seed iniziale** della LLM Wiki di compliance per i vault Karpathy generati dall'app Compliance Copilot (SCO Compliance OS). Quando un nuovo vault viene scaffolded (vuoto o incompleto), il modulo `auto_scaffold.py` copia integralmente il contenuto di `wiki_seed/` dentro la cartella `wiki/` del vault destinazione, fornendo all'utente una base operativa popolata con le entity, i concept, le synthesis, il glossario e le sources piu comuni nel lavoro consulenziale italiano in materia di compliance normativa.

## 2. Composizione del seed (30+ file)

| Sotto-cartella | File seed | Funzione |
|---|---|---|
| `wiki_seed/entities/` | 10 file .md | Atti normativi, standard tecnici, autorita di vigilanza (NIS 2, GDPR, ISO 27001, ISO 9001, AI Act, TUSL, ISO 42001, ACN, AGENAS, Garante Privacy) |
| `wiki_seed/concepts/` | 8 file .md | Concetti normativi e tecnici trasversali (analisi dei rischi, audit interno, riesame della direzione, NC/AC, gestione incidenti, valutazione conformita, BIA, DPIA) |
| `wiki_seed/synthesis/` | 4 file .md | Mapping cross-framework comuni (NIS 2 / ISO 27001, AI Act / ISO 42001, GDPR / ISO 27701, ISO 9001 / ISO 27001) |
| `wiki_seed/glossari/_index.md` | 1 file con 50+ sigle | Glossario aziendale tabellare per dominio (cybersicurezza, sanita, privacy, lavoro, qualita) |
| `wiki_seed/sources/_index.md` | 1 file di indice | Schema standard B Ondata 4 + esempio di scheda di sintesi delle fonti raw |

Totale: 24 file markdown + struttura cartelle. Espandibile dall'utente con entity, concept, synthesis e fonti proprie del vault destinazione.

## 3. Convenzioni di scaffolding rispettate

Il seed rispetta integralmente le convenzioni del DNA del vault (CLAUDE.md sezione INGEST):

- **Frontmatter YAML strict** con vocabolario chiuso (entity_type, entity_subtype, ambito_canonico, status)
- **Status `stub`** su tutti i file (sono template, da popolare in ingest concreti dall'utente)
- **Relationships tipizzate** (Ondata 3) popolate con vocabolario chiuso 8 valori
- **Wikilink relativi** che funzionano dopo la copia in qualsiasi vault destinazione
- **Body markdown italiano professionale** con tono consulenziale Amodeo (no emoji, virgolette dritte, "al punto" mai segno paragrafo)
- **Cross-reference** popolate fra entity, concept e synthesis

## 4. Flusso di scaffolding (per DEV-AUTO-SCAFFOLD)

```python
# Pseudocode del modulo auto_scaffold.py
def scaffold_vault(target_vault_root: Path) -> None:
    seed_root = Path(__file__).parent / "templates" / "wiki_seed"
    target_wiki = target_vault_root / "wiki"
    
    # Crea struttura wiki/ vuota se non esiste
    for subdir in ["entities", "concepts", "synthesis", "glossari", "sources"]:
        (target_wiki / subdir).mkdir(parents=True, exist_ok=True)
    
    # Copia seed entities (se cartella vuota o non contiene file con stesso slug)
    for seed_file in (seed_root / "entities").glob("*.md"):
        target_file = target_wiki / "entities" / seed_file.name
        if not target_file.exists():
            shutil.copy2(seed_file, target_file)
    
    # Idem per concepts, synthesis, sources, glossari
    # ... 
```

## 5. Estensione del seed

L'utente puo:

- **Aggiungere entity custom** del proprio settore (es. entity di standard verticali sanitari, ambientali, finanziari) dopo lo scaffolding iniziale
- **Personalizzare il glossario** con sigle aziendali interne al proprio business
- **Aggiungere synthesis** specifiche ai clienti del proprio portafoglio (mapping cross-framework non coperti dal seed)
- **Promuovere a `status: active`** le pagine del seed che vengono effettivamente popolate con dettagli del proprio operato

## 6. Note tecniche

- Il seed e versionato con il codebase di SCO Compliance OS in `backend/sco_compliance_os/scaffold/templates/wiki_seed/`
- L'aggiornamento del seed (nuove entity comuni, nuove synthesis, nuove sigle nel glossario) si propaga ai nuovi vault scaffolded ma NON ai vault gia esistenti (no auto-update retroattivo, principio Karpathy "no edit retroattivo")
- Versione corrente del seed: 1.0.2 (24/05/2026)

Part of [[scaffold/_index]]
