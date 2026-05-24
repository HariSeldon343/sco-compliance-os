# Loop Operativo — Analisi Documentale Iterativa

Dettaglio del loop autonomo iterativo per l'analisi documentale, ispirato al pattern autoresearch di Karpathy applicato all'analisi di corpus documentali.

## Architettura del loop

```
┌─────────────────────────────────────────────────┐
│                 FASE 3 — LOOP                    │
│                                                   │
│  ┌──────┐   ┌─────────┐   ┌────────┐            │
│  │ SCAN │──▶│ ANALYZE │──▶│ VERIFY │            │
│  └──────┘   └─────────┘   └────────┘            │
│                                  │                │
│                                  ▼                │
│  ┌────────┐   ┌────────────┐   ┌────────┐       │
│  │ REPEAT │◀──│ KEEP/REVISE│◀──│ APPEND │       │
│  └────────┘   └────────────┘   └────────┘       │
│      │              ▲                             │
│      │              │                             │
│      │        ┌────────────┐                      │
│      │        │ SELF-CHECK │                      │
│      │        └────────────┘                      │
│      │                                            │
│      ▼ (quando tutti i file sono analizzati)      │
│  ┌──────────────────────┐                         │
│  │ CROSS-REF GLOBALE    │                         │
│  └──────────────────────┘                         │
│      │                                            │
│      ▼                                            │
│  ┌──────────────────────┐                         │
│  │ GENERA evals.md      │                         │
│  └──────────────────────┘                         │
└─────────────────────────────────────────────────┘
```

## Dettaglio degli step

### Step 1 — SCAN

Seleziona il prossimo batch di file non ancora analizzati.

**Batch size consigliati:**
- File testuali brevi (TXT, MD, CSV, JSON): 8-10 file per batch
- Documenti strutturati (PDF, DOCX): 3-5 file per batch
- File complessi (XLSX multi-foglio, PPTX): 2-3 file per batch
- File non standard (immagini, binari): 5-8 file per batch (analisi più superficiale)

**Come tracciare il progresso:**
Mantieni una lista interna dei file già analizzati. Dopo ogni iterazione, aggiorna il contatore.

```
Iterazione 1: DOC-001 → DOC-005 (5 file, 5/48 totali)
Iterazione 2: DOC-006 → DOC-010 (5 file, 10/48 totali)
...
```

### Step 2 — ANALYZE

Per ogni file nel batch, esegui:

1. **Lettura**: Usa `read` per leggere il contenuto del file
2. **Identificazione tipo**: Determina tipo file, numero pagine/fogli/slide
3. **Classificazione**: Assegna categoria primaria e tag (1-5)
4. **Estrazione metadati**: Autore, data, versione, stato, protocollo
5. **Sintesi**: Scrivi una sintesi di 80-300 parole che copra: scopo, ambito, contenuti principali, prescrizioni, riferimenti normativi, destinatari
6. **Entità**: Estrai nomi, date, numeri di protocollo, riferimenti ad altri documenti
7. **Dipendenze**: Identifica riferimenti incrociati ad altri documenti del corpus

**Per file Excel:**
- Elenca tutti i fogli presenti
- Se i fogli contengono dati strutturalmente diversi, documenta ogni foglio come sotto-sezione
- Indica dimensioni (righe × colonne) e tipo di dati per ogni foglio

**Per immagini:**
- Usa `read` che supporta analisi visiva delle immagini
- Descrivi il contenuto visivo: tipo di immagine (diagramma, screenshot, foto, scansione)
- Se contiene testo leggibile, trascrivilo
- Se è un diagramma/schema, descrivi la struttura

**Per file non leggibili:**
- Registra percorso e motivo della non leggibilità
- Aggiungi alla sezione "File non leggibili" delle statistiche

### Step 3 — VERIFY

Confronta le informazioni appena estratte con il context-map esistente:

- **Contraddizioni**: Stessa informazione con valori diversi?
- **Riferimenti**: I documenti appena analizzati citano documenti già catalogati? I riferimenti sono corretti?
- **Versioni**: Esistono versioni multiple dello stesso documento?
- **Metadati**: Date, autori, numeri di revisione sono coerenti con documenti correlati?

### Step 4 — APPEND

Aggiungi le nuove schede al context-map.md:

1. Aggiorna l'indice di classificazione (tabella in testa)
2. Aggiungi le schede documento nella sezione appropriata
3. Se sono state rilevate incoerenze, aggiungile alla mappa delle incoerenze
4. Aggiorna le statistiche di copertura

Usa il tool `edit` per aggiornamento incrementale — non riscrivere l'intero file.

### Step 5 — SELF-CHECK

Rileggi il context-map aggiornato e verifica:

- [ ] Tutti i DOC-ID sono univoci e progressivi
- [ ] L'indice di classificazione corrisponde alle schede presenti
- [ ] I riferimenti incrociati (DOC-XXX) puntano a schede esistenti
- [ ] Le categorie e i tag sono coerenti (stessa terminologia)
- [ ] Le sintesi rispettano il vincolo 80-300 parole
- [ ] La mappa delle incoerenze usa i DOC-ID corretti
- [ ] Le statistiche di copertura sono aggiornate

### Step 6 — KEEP/REVISE

- Se il self-check non rileva problemi → **KEEP** e prosegui
- Se il self-check rileva problemi → **REVISE**: correggi gli errori prima di proseguire al batch successivo
- Registra internamente: iterazione N, esito (keep/revise), eventuali correzioni applicate

### Step 7 — REPEAT

Torna allo Step 1 con il prossimo batch di file non analizzati.

**Condizione di uscita**: tutti i file della cartella master sono stati analizzati (o registrati come non leggibili).

## Passaggio finale — Cross-reference globale

Dopo il completamento del loop, esegui un passaggio dedicato di cross-reference:

1. Rileggi l'intero context-map dall'inizio
2. Cerca pattern di incoerenza che emergono solo vedendo l'intero corpus:
   - Processi documentati in modo frammentario
   - Aree con documentazione ridondante
   - Lacune documentali (aree menzionate ma non documentate)
   - Catene di dipendenze problematiche
3. Aggiorna la mappa delle incoerenze con i nuovi findings
4. Aggiorna le statistiche finali

## Metriche del loop

Alla fine del loop, registra per l'evals.md:

- **Iterazioni totali**: N
- **Tasso keep**: N keep / N iterazioni totali (%)
- **Revisioni**: N (con dettaglio di cosa è stato corretto)
- **Tempo stimato per iterazione**: (se tracciabile)
- **File per iterazione media**: N
