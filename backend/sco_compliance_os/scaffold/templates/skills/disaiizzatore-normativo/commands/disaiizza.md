# Comando `/disaiizza`

Esegue il ciclo completo di deaiizzazione a 5 fasi su un testo italiano tecnico-normativo, producendo il documento riscritto pulito + il report sidecar di giustificazione.

## Sintassi

```
/disaiizza
[testo da deaiizzare]
```

oppure, se il testo è in un file allegato:

```
/disaiizza file:<nome-file>
```

oppure con parametri opzionali:

```
/disaiizza --tipo=ddv --modalita=standard
```

## Parametri opzionali

| Parametro | Valori | Default | Effetto |
|-----------|--------|---------|---------|
| `--tipo` | `procedura-iso` \| `ddv` \| `gap-analysis` \| `perizia-ctu` \| `nota-tecnica` \| `email` \| `auto` | `auto` | Calibra il catalogo whitelist sulla tipologia documentale |
| `--modalita` | `conservativo` \| `standard` \| `aggressivo` | `standard` | Soglia di intervento sui casi borderline |
| `--output-file` | `<path>` | nessuno | Salva il documento riscritto su file (solo blocco "Documento riscritto") |
| `--sidecar-file` | `<path>` | nessuno | Salva il report sidecar su file separato |
| `--no-sidecar` | flag | falso | Non produrre il report sidecar (sconsigliato) |
| `--lingua-stile` | `amodeo` \| `neutro` | `amodeo` | Stile-target della riscrittura |

## Flusso di esecuzione

### Fase 1 — BASELINE (interna)

1. Leggi il testo in input.
2. Identifica la tipologia documentale (se `--tipo=auto`).
3. Applica il catalogo `references/tell-ai-italiani.md` per identificare tutti i passaggi candidati alla riscrittura.
4. Costruisci una mappa: `passaggio → categoria tell → confidence (alta/media/bassa)`.
5. **Non riscrivere ancora.**

### Fase 2 — VERIFICATION PLANNING (interna)

Per ogni passaggio candidato:

1. **Test whitelist**: il passaggio contiene elementi di `references/whitelist-normativa.md`?
   - Sì → escludi dalla riscrittura, marca come "whitelist"
   - No → procedi
2. **Test integrità semantica**: la parafrasi rischia di alterare il significato tecnico, attenuare un rilievo, modificare un dato?
   - Sì → escludi dalla riscrittura, marca come "rischio semantico"
   - No → procedi
3. **Test confidence**: il pattern è chiaramente un tell AI o è dubbio?
   - In modalità `conservativo`: solo confidence alta procede
   - In modalità `standard`: confidence alta e media procedono
   - In modalità `aggressivo`: tutte procedono
4. **Test stile-target**: il passaggio è già coerente con `amodeo-voice`?
   - Sì → escludi
   - No → procedi

L'output di Fase 2 è una lista filtrata di passaggi che effettivamente verranno riscritti.

### Fase 3 — REWRITE (interna)

Per ogni passaggio confermato:

1. Applica le sostituzioni del catalogo.
2. Ristruttura il periodo se necessario.
3. Aggiungi (se opportuno) il riferimento normativo puntuale che lo stile Amodeo richiederebbe.
4. Verifica che la riscrittura non introduca em dash, grassetto inline, gerundi finali nuovi.
5. Verifica coerenza con il registro del documento ospitante.

### Fase 4 — INTEGRITY CHECK (interna)

Confronto sistematico tra originale e riscrittura:

| Verifica | Esito atteso |
|----------|--------------|
| Riferimenti normativi (articoli, controlli, norme) | identici |
| Numeri (date, importi, percentuali, RTO/RPO) | identici |
| Identificatori (ID gap, ID controlli, ID rilievi) | identici |
| Classificazione rilievi (NC_I, NC_II, SM, Osservazione) | identica |
| Forza delle conclusioni | identica o più nitida (mai attenuata) |
| Fatti (azioni svolte, evidenze osservate) | identici |
| Lista di tell AI residui nel documento riscritto | nessuno |

Se anche **una sola** verifica fallisce, ritorna a Fase 3 sul passaggio incriminato. Massimo 2 iterazioni; alla terza, marcare il passaggio come "non riscrivibile in sicurezza" e lasciare l'originale.

### Fase 5 — FINAL DELIVERY

Output finale in due blocchi delimitati come specificato in SKILL.md, sezione "Output format".

---

## Esempio di interazione

**Input utente:**

```
/disaiizza --tipo=ddv

In sede di audit è emerso che l'organizzazione, pur avendo implementato 
un approccio strutturato e all'avanguardia alla gestione degli accessi 
privilegiati, presenta alcune aree di miglioramento che meritano di essere 
evidenziate. È importante notare che l'assenza di MFA sugli account 
amministrativi configura una NC_I rispetto a A.5.17 di ISO 27001:2022.
```

**Output skill:**

```
═══════════════════════════════════════════════
DOCUMENTO RISCRITTO (versione pulita)
═══════════════════════════════════════════════

Non risulta evidenza dell'attivazione di meccanismi di autenticazione a più 
fattori (MFA) sugli account amministrativi. La condizione configura NC_I 
rispetto al controllo A.5.17 di ISO/IEC 27001:2022.

═══════════════════════════════════════════════
REPORT SIDECAR — Giustificazione modifiche
═══════════════════════════════════════════════

Sintesi: 4 modifiche su 1 paragrafo. Categorie: meta-discorso (#14), 
aggettivi promozionali (#15), ridondanze (#1).

| # | Originale (estratto)                       | Riscrittura                                | Categoria | Motivazione |
|---|--------------------------------------------|--------------------------------------------|-----------|-------------|
| 1 | "In sede di audit è emerso che"            | (rimosso)                                  | #14       | Meta-discorso ridondante con la formula di rilievo |
| 2 | "approccio strutturato e all'avanguardia"  | (rimosso)                                  | #15       | Aggettivi promozionali senza valore informativo |
| 3 | "presenta alcune aree di miglioramento"    | "Non risulta evidenza di…"                 | #1, formula | Sostituito con formula tipizzata DDV |
| 4 | "È importante notare che"                  | (rimosso)                                  | #14       | Meta-discorso |

Note di integrità (Fase 4):
- Riferimenti normativi: invariati ✅ (A.5.17, ISO/IEC 27001:2022)
- Classificazione rilievo: invariata ✅ (NC_I)
- Forza del rilievo: invariata, lievemente più nitida ✅
- Conclusioni: invariate ✅

Passaggi NON modificati per scelta:
- "NC_I", "A.5.17", "ISO/IEC 27001:2022" → whitelist normativa
```

---

## Comportamenti speciali

### Se il testo non contiene tell AI

Restituire:

```
═══════════════════════════════════════════════
DOCUMENTO RISCRITTO (versione pulita)
═══════════════════════════════════════════════

[testo originale invariato]

═══════════════════════════════════════════════
REPORT SIDECAR — Giustificazione modifiche
═══════════════════════════════════════════════

Nessuna modifica applicata. Il testo non presenta tell AI riconoscibili 
secondo il catalogo. Il registro è coerente con lo stile-target Amodeo.
```

### Se il testo è interamente whitelist

Esempio: una pagina di sole citazioni normative. Restituire invariato con sidecar che spiega.

### Se il testo è troppo lungo per una singola sessione

Suggerire di dividerlo in blocchi (sezione per sezione) e trattarli con `/disaiizza` separatamente, mantenendo lo stesso `--tipo`.

### Se l'utente chiede di salvare su file

Salvare **solo** il blocco "Documento riscritto" sul file indicato. Mai includere il sidecar dentro il file del documento. Se l'utente vuole anche il sidecar su file, usare `--sidecar-file=<path>`.
