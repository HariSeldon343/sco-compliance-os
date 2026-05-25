---
description: "Statement of Applicability (Appendice A ISO/IEC 42001)"
---

# /soa — Statement of Applicability (Appendice A ISO/IEC 42001)

## Uso
`/soa [organizzazione]`

## Quando
Documento obbligatorio ISO/IEC 42001 (cl. 6.1.3 d). Elenca i 39 controlli dell'Appendice A (da A.2.2 ad A.10.4) con stato di applicabilità, giustificazione, riferimenti ai documenti di implementazione.

## Pre-requisiti

- Scoping completato (`/scope`).
- Risk assessment e AIIA almeno in bozza (`/aiia`).
- Politica AI definita.

## Struttura del deliverable

Documento .docx + foglio di calcolo .xlsx (formato esportabile).

### Intestazione
- Organizzazione, scope AIMS, versione, data, owner, firma CEO/responsabile AI.
- Classificazione di rischio AI Act associata.
- Lista dei sistemi IA coperti.

### Tabella SoA (39 righe)

Elenco completo dei 9 obiettivi di controllo e 39 controlli dell'Appendice A ISO/IEC 42001:

**A.2 Politiche relative all'IA**
- A.2.2 Politica AI
- A.2.3 Allineamento con altre politiche organizzative
- A.2.4 Riesame della politica AI

**A.3 Ruoli e responsabilità interne**
- A.3.2 Ruoli e responsabilità AI
- A.3.3 Reporting delle preoccupazioni

**A.4 Risorse per i sistemi IA**
- A.4.2 Documentazione delle risorse
- A.4.3 Risorse dati
- A.4.4 Risorse di strumenti (tooling)
- A.4.5 Risorse di sistema e di calcolo
- A.4.6 Risorse umane

**A.5 Valutazione degli impatti dei sistemi IA**
- A.5.2 Processo di AIIA
- A.5.3 Documentazione dell'AIIA
- A.5.4 Valutazione degli impatti su individui e gruppi
- A.5.5 Valutazione degli impatti sociali

**A.6 Ciclo di vita del sistema IA**
- A.6.1.2 Obiettivi per lo sviluppo responsabile
- A.6.1.3 Processi per lo sviluppo responsabile
- A.6.2.2 Requisiti e specifiche
- A.6.2.3 Documentazione del design e dello sviluppo
- A.6.2.4 Verifica e validazione
- A.6.2.5 Deployment
- A.6.2.6 Esercizio e monitoraggio
- A.6.2.7 Documentazione tecnica
- A.6.2.8 Log di evento
- A.7 Dati per i sistemi IA

**A.7 Dati per i sistemi IA**
- A.7.2 Dati per lo sviluppo e miglioramento
- A.7.3 Acquisizione dei dati
- A.7.4 Qualità dei dati
- A.7.5 Provenienza dei dati
- A.7.6 Preparazione dei dati

**A.8 Informazioni per le parti interessate**
- A.8.2 Documentazione di sistema
- A.8.3 Informazioni agli utenti
- A.8.4 Segnalazione di incidenti esterni
- A.8.5 Comunicazione agli interessati

**A.9 Uso dei sistemi IA**
- A.9.2 Processi per l'uso responsabile
- A.9.3 Obiettivi per l'uso responsabile
- A.9.4 Uso previsto

**A.10 Terze parti e relazioni con i clienti**
- A.10.2 Allocazione delle responsabilità
- A.10.3 Fornitori
- A.10.4 Clienti

### Colonne della tabella

| Colonna | Contenuto |
|---------|-----------|
| ID | A.x.y |
| Titolo | Testo normativo sintetico |
| Applicabile | SI / NO |
| Giustificazione | Motivazione fondata sul risk assessment, scope, AIIA |
| Implementazione | Descrizione misure attuate |
| Documenti | Riferimento a policy, procedure, registri |
| Owner | Ruolo responsabile |
| Riferimento AI Act | Art. correlati (es. A.6.2.4 ↔ Art. 15 AI Act) |
| Riferimento Legge 132 | Art. correlato quando applicabile |
| Stato maturità | Assente/Iniziale/Definito/Gestito/Ottimizzato |

### Note di chiusura
- Elenco esclusioni con giustificazione.
- Versionamento e piano di revisione.

## Regole operative

- Nessuna esclusione è ammessa per i controlli ritenuti fondamentali dallo scope. Le esclusioni vanno giustificate su base di rischio, non per convenienza.
- Per ogni controllo applicabile, mappa almeno un articolo di AI Act e, se pertinente, di Legge 132.
- I controlli non prescrittivi di Appendice C e D ISO 42001 sono informativi e non entrano nella SoA.
- Quando un controllo è "Definito" o meno, genera automaticamente un gap record riconducibile al piano di trattamento (`/gap`).

## Documenti collegati

- `../references/iso42001-2023.md` (Appendice A completa, Appendice B linee guida attuative)
- `../references/matrice-cross-framework.md`
- `../templates/soa-42001.md`
