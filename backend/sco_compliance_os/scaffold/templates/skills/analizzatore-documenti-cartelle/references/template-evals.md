# Template — evals.md

Usa questa struttura come template per generare il report di autovalutazione.

---

```markdown
# Evaluation Report — [Nome cartella master]

Data generazione: YYYY-MM-DD HH:MM
Context-map di riferimento: context-map.md

## Punteggi (scala 1-10)

| # | Criterio | Punteggio | Evidenza |
|---|----------|-----------|----------|
| 1 | **Copertura file** — % di file analizzati su totale presente nella cartella master | _ | [Indicare N/N file, elencare eventuali file non analizzati con motivo] |
| 2 | **Profondità di analisi** — completezza delle schede documento (sintesi, metadati, entità, dipendenze) | _ | [Indicare % schede con tutti i campi compilati, lunghezza media sintesi] |
| 3 | **Accuratezza classificazione** — coerenza e pertinenza dei tag e categorie assegnati | _ | [Indicare eventuali classificazioni ambigue o incerte] |
| 4 | **Rilevamento incoerenze** — capacità di identificare contraddizioni inter-documento | _ | [Indicare N incoerenze rilevate, suddivise per tipo e gravità, eventuali false positive note] |
| 5 | **Struttura e navigabilità** — facilità di consumo del context-map da parte di agenti a valle | _ | [Indicare: indice completo sì/no, riferimenti incrociati sì/no, ID univoci coerenti sì/no] |
| 6 | **Granularità metadati** — quantità e qualità dei metadati estratti per file | _ | [Indicare % file con autore estratto, % con data, % con versione] |
| 7 | **Gestione file non standard** — capacità di trattare file eterogenei (immagini, Excel complessi, binari) | _ | [Indicare come sono stati gestiti file non testuali, eventuali limitazioni] |
| 8 | **Coerenza interna del context-map** — assenza di contraddizioni nel documento generato stesso | _ | [Indicare se self-check ha rilevato problemi, se ID sono coerenti, se riferimenti incrociati sono validi] |
| 9 | **Efficienza del loop** — numero di iterazioni, tasso di keep vs discard, backtrack | _ | [Indicare N iterazioni totali, N revisioni, % keep rate] |
| 10 | **Completezza per agenti a valle** — un agente successivo può operare senza rileggere i documenti originali? | _ | [Indicare % file per cui la scheda è autosufficiente, elencare file che richiedono consultazione diretta] |

**Punteggio composto:** [somma dei 10 punteggi] / 100

---

## Dettaglio per criterio

### 1. Copertura file
[Analisi dettagliata: quanti file totali, quanti analizzati, motivi di eventuali esclusioni]

### 2. Profondità di analisi
[Analisi dettagliata: qualità media delle sintesi, campi più frequentemente mancanti]

### 3. Accuratezza classificazione
[Analisi dettagliata: coerenza delle categorie, eventuali sovrapposizioni o ambiguità]

### 4. Rilevamento incoerenze
[Analisi dettagliata: tipologie di incoerenze trovate, metodo di rilevamento, confidence]

### 5. Struttura e navigabilità
[Analisi dettagliata: valutazione della struttura del context-map per consumo da agenti]

### 6. Granularità metadati
[Analisi dettagliata: quali metadati sono stati estratti più frequentemente, lacune]

### 7. Gestione file non standard
[Analisi dettagliata: approccio per immagini, Excel complessi, file binari]

### 8. Coerenza interna del context-map
[Analisi dettagliata: risultati del self-check, eventuali correzioni applicate]

### 9. Efficienza del loop
[Analisi dettagliata: cronologia delle iterazioni, decisioni keep/discard/revise]

### 10. Completezza per agenti a valle
[Analisi dettagliata: valutazione dell'autosufficienza delle schede]

---

## Note e raccomandazioni

- [Punti di miglioramento identificati]
- [File che meritano rianalisi e motivo]
- [Suggerimenti per iterazioni successive]
- [Aree del corpus che richiedono maggiore attenzione]
- [Proposta di almeno un miglioramento concreto]
```

---

## Guida alla valutazione

### Scala di punteggio

| Punteggio | Significato |
|-----------|-------------|
| 9-10 | Eccellente: criterio soddisfatto pienamente, nessun margine di miglioramento significativo |
| 7-8 | Buono: criterio soddisfatto con margini minori di miglioramento |
| 5-6 | Sufficiente: criterio parzialmente soddisfatto, miglioramenti necessari |
| 3-4 | Insufficiente: criterio poco soddisfatto, intervento necessario |
| 1-2 | Critico: criterio non soddisfatto, rianalisi necessaria |

### Principi di autovalutazione

- Sii onesto e critico: sovrastimare i punteggi riduce il valore dell'eval
- Ogni punteggio DEVE avere un'evidenza concreta nel campo "Evidenza"
- Il punteggio composto target è >= 70/100 per un context-map di qualità accettabile
- Se il punteggio composto è < 60, raccomanda una seconda iterazione completa
