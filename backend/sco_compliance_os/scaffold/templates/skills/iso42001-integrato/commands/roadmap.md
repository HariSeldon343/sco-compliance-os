---
description: "Roadmap di adeguamento AIMS + AI Act + Legge 132"
---

# /roadmap — Roadmap di adeguamento AIMS + AI Act + Legge 132

## Uso
`/roadmap [organizzazione|sistema]`

## Quando
Quando l'organizzazione ha completato gap analysis (`/gap`) e ha bisogno di un piano di adeguamento temporale, prioritizzato, con assegnazione di owner e risorse. La roadmap è lo strumento operativo per passare dalla diagnosi all'azione.

## Pre-requisiti

- Gap analysis completata (`/gap`).
- Risk assessment aggiornato.
- Classificazione AI Act confermata (`/rischio-regolatorio`).
- Mappa delle scadenze regolatorie (`references/scadenze-regolatorie.md`).

## Scadenze regolatorie di riferimento

| Data | Obbligo |
|------|---------|
| 02/02/2025 | Divieti Art. 5 AI Act + AI literacy Art. 4 (già in vigore) |
| 02/08/2025 | Obblighi GPAI Art. 51-55; autorità nazionali |
| 02/08/2026 | Obblighi sistemi alto rischio (Art. 6 + Allegato III); obblighi fornitori e deployer; sanzioni piene |
| 10/10/2026 | Scadenza deleghe Legge 132 (decreti attuativi Art. 16-18) |
| 02/08/2027 | Obblighi sistemi alto rischio integrati in prodotti regolamentati (Allegato I) |

## Struttura della roadmap

Documento .docx + cronoprogramma .xlsx + diagramma Gantt.

### 1. Visione
- Obiettivo al 02/08/2026 (o data target aziendale).
- Livello di maturità AIMS atteso.
- Certificazione ISO 42001 come target opzionale (8-12 mesi).
- Stato di conformità target a AI Act e Legge 132.

### 2. Fase 0 — Quick wins (0-3 mesi)
Azioni a basso sforzo e alto impatto:
- Nomina AI governance lead e istituzione comitato AI.
- Pubblicazione politica AI.
- Formazione AI literacy (Art. 4 AI Act — già obbligatoria).
- Censimento sistemi IA (inventario iniziale).
- Verifica presenza pratiche vietate Art. 5.

### 3. Fase 1 — Fondazione AIMS (3-6 mesi)
- Scoping formale.
- Risk assessment e AIIA sui sistemi critici.
- Prima versione SoA.
- Procedure di ciclo di vita (design, sviluppo, deployment, monitoring).
- Procedure di data governance.
- Formazione specialistica.

### 4. Fase 2 — Implementazione cogenti AI Act (6-12 mesi)
Per ogni sistema ad alto rischio:
- Documentazione tecnica Allegato IV completa.
- Sistema di gestione rischi Art. 9.
- Misure data governance Art. 10.
- Log system Art. 12.
- Istruzioni d'uso trasparenti Art. 13.
- Sorveglianza umana Art. 14.
- Misure accuratezza/robustezza/cybersecurity Art. 15.
- QMS fornitore Art. 17.
Per deployer (quando applicabile):
- FRIA Art. 27.
- Procedure sorveglianza Art. 26.
Per GPAI (quando applicabile):
- Documentazione Art. 53 + codice di condotta Art. 56.

### 5. Fase 3 — Settori Legge 132 e autorità italiane (6-12 mesi, in parallelo)
- Verifica applicabilità Art. 7-15 per settore.
- Implementazione obblighi informativi specifici (lavoratori, pazienti, clienti).
- Accreditamento/notifica verso AgID/ACN secondo Art. 19-20.
- Coordinamento con Comitato PCM (settori strategici).
- Monitoraggio decreti delegati Art. 16-18.

### 6. Fase 4 — Audit, riesame, miglioramento continuo (9-15 mesi)
- Audit interno completo AIMS.
- Riesame di direzione con dati di monitoraggio.
- Piano di miglioramento.
- Eventuale preparazione audit di certificazione ISO 42001.

### 7. Fase 5 — Operatività e compliance continua (15+ mesi)
- Post-market monitoring Art. 72.
- Gestione incidenti gravi Art. 73.
- Aggiornamento continuo documentazione.
- Verifica periodica su nuove pratiche vietate, nuovi standard armonizzati, linee guida Commissione.

### 8. Governance del piano
- Sponsorship: CEO / CdA.
- Steering committee mensile.
- KPI di monitoraggio.
- Indicatori di ritardo e escalation.
- Budget e risorse (placeholder da popolare).

## Regole operative

- Le azioni legate a obblighi cogenti AI Act **hanno priorità assoluta** sulle azioni volontarie 42001: data di scadenza fissa per legge.
- Non promettere certificazione ISO 42001 come deliverable in meno di 8 mesi dalla fase 0.
- Integra dipendenze: audit interno ≠ audit esterno di certificazione; tra i due servono almeno 3 mesi di consolidamento.
- Prevedi buffer su ogni scadenza regolatoria (30-60 giorni).
- Se l'organizzazione ha già ISO 27001 e GDPR maturi, accelera Fase 1-2 riutilizzando controlli esistenti.
- Segnala esplicitamente i rischi di mancato rispetto delle scadenze cogenti con stima sanzionatoria (`/sanzioni`).

## Documenti collegati

- `../references/scadenze-regolatorie.md`
- `../references/matrice-cross-framework.md`
- `../references/ai-act-2024.md`
- `../references/legge-132-2025.md`
