# Template — context-map.md

Usa questa struttura come template per generare il context-map. Ogni sezione è obbligatoria.

---

```markdown
# Context Map — [Nome cartella master]

Data generazione: YYYY-MM-DD HH:MM
Cartella master: /percorso/completo/
Totale file analizzati: N
Totale sottocartelle: N

## Indice di classificazione

| # | Percorso relativo | Tipo file | Categoria | Tag | Criticità |
|---|-------------------|-----------|-----------|-----|-----------|
| 1 | /subdir/doc.pdf   | PDF       | Procedura operativa | ISO9001, qualità | media |
| 2 | /subdir2/risk.xlsx | XLSX     | Risk assessment | sicurezza, rischio | alta |

> Nota: l'indice deve contenere TUTTI i file analizzati, ordinati per DOC-ID.
> La colonna "Criticità" indica l'importanza del documento nel contesto del corpus (alta/media/bassa).

---

## Schede documento

### DOC-001 — /subdir/doc.pdf
- **Tipo:** PDF, 12 pagine
- **Categoria:** Procedura operativa
- **Tag:** ISO 9001, gestione qualità, processo X
- **Sintesi:** [Sintesi dettagliata del contenuto: scopo, ambito, prescrizioni principali, riferimenti normativi, destinatari. MINIMO 80 parole, MASSIMO 300 parole. La sintesi deve essere sufficientemente dettagliata da rendere superflua la rilettura del documento originale per un agente a valle.]
- **Metadati chiave:** autore, data creazione/modifica, versione, stato (bozza/approvato/obsoleto), numero protocollo se presente
- **Entità rilevanti:** nomi di persone, organizzazioni, date significative, numeri di protocollo, riferimenti normativi, riferimenti incrociati ad altri documenti del corpus
- **Dipendenze:** riferisce a DOC-003 (procedura padre), è referenziato da DOC-007 (audit report)
- **Lingua originale:** italiano (indicare se diversa da italiano)
- **Note:** [eventuali anomalie, sezioni mancanti, formattazione problematica, dubbi interpretativi]

### DOC-002 — /subdir/report.docx
[...stessa struttura...]

> Ripetere per OGNI file presente nella cartella master.
> Ogni file deve avere un DOC-ID univoco progressivo (DOC-001, DOC-002, ...).
> Se un file Excel ha fogli strutturalmente diversi, documentare ogni foglio come sotto-sezione.

---

## Mappa delle incoerenze

| # | Tipo incoerenza | File coinvolti | Descrizione | Gravità |
|---|----------------|----------------|-------------|---------|
| 1 | Dato contraddittorio | DOC-001, DOC-005 | La data di approvazione della procedura X differisce: 01/03/2025 vs 15/04/2025 | alta |
| 2 | Riferimento rotto | DOC-003 | Cita "Procedura ABC rev.2" ma nella cartella esiste solo rev.1 | media |
| 3 | Versione multipla | DOC-010, DOC-011 | Due versioni dello stesso documento "Policy Sicurezza" (v1.0 e v2.0) senza indicazione di quale sia vigente | media |
| 4 | Metadato incoerente | DOC-007 | Autore indicato come "Mario Rossi" ma il documento è firmato da "Luigi Bianchi" | bassa |

### Tipi di incoerenza da rilevare:
- **Dato contraddittorio**: stessa informazione con valori diversi in documenti diversi
- **Riferimento rotto**: documento che cita un altro documento non presente nel corpus
- **Versione multipla**: più versioni dello stesso documento senza chiara indicazione di quale sia vigente
- **Metadato incoerente**: discrepanza tra metadati (autore, data, versione) all'interno dello stesso documento o tra documenti correlati
- **Dipendenza circolare**: catena di riferimenti che crea un ciclo
- **Obsolescenza**: documento che riferisce a normative/standard/procedure superate
- **Lacuna documentale**: processo o area menzionata ma priva di documentazione di supporto

---

## Statistiche di copertura

- **File analizzati:** N/N (100%)
- **File non leggibili:** [elenco con percorso e motivo di non leggibilità]
- **Categorie rilevate:** [elenco di tutte le categorie assegnate con conteggio]
- **Tag più frequenti:** [top 10 tag con conteggio]
- **Incoerenze totali:** N (alta: X, media: Y, bassa: Z)
- **Distribuzione per tipo file:** PDF: N, DOCX: N, XLSX: N, PPTX: N, altri: N
- **Sottocartelle analizzate:** [elenco con conteggio file per sottocartella]
```

---

## Note per l'agente

- L'indice di classificazione è il punto di ingresso per agenti a valle: deve essere completo e navigabile.
- Le schede documento sono il cuore del context-map: la sintesi deve essere autosufficiente.
- La mappa delle incoerenze è il valore aggiunto principale: sii aggressivo nel rilevamento.
- Le statistiche di copertura sono la prova di completezza: N/N deve essere 100% o giustificato.
