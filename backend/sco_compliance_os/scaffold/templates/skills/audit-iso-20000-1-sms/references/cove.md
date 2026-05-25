# Chain-of-Verification (CoVe) — Metodologia di Quality Assurance

Il CoVe è il meccanismo interno di quality assurance — un audit interno su ogni output prodotto dall'agente. Garantisce che ogni risposta sia accurata, coerente e verificata prima di essere consegnata all'utente.

## Le 4 fasi (eseguite internamente — l'utente riceve solo l'output finale)

### FASE 1 — BASELINE RESPONSE
Genera bozza completa dell'output richiesto. Applica tutte le regole della skill (formato, riferimenti normativi, mapping triplice). Non consegnare questa bozza.

### FASE 2 — VERIFICATION PLANNING
Genera internamente una lista di domande di verifica per ogni affermazione critica della bozza. Le domande devono essere:

**Per ISO 20000-1**:
- Il riferimento alla clausola/processo è corretto? (es. "Incident Management è davvero §8.6.1?")
- I termini tecnici (CMDB, CAB, RFC, KEDB, SLA/OLA/UC, SCAT) sono usati correttamente?
- I KPI/SLA indicati sono realistici e coerenti con la norma?
- Il mapping con ISO 27001 e NIS2 è esatto?

**Per ISO 27001**:
- I numeri di controllo Annex A sono corretti? (es. "A.8.9 è davvero Configuration Management?")
- Le clausole citate esistono e dicono quello che affermiamo?
- Il SoA è coerente con le estensioni 27017/27018?
- La classificazione NC (Maggiore/Minore/SM) è proporzionata?

**Per NIS2/Legge 90**:
- Gli articoli D.Lgs. 138/2024 citati sono corretti?
- Le timeline di notifica Art. 23 sono esatte (24h/72h/1month)?
- La classificazione del soggetto (essenziale/importante) è applicata correttamente?
- I mapping NIS2↔27001↔NIST↔20000-1 sono accurati?

**Per tutti gli output**:
- Ci sono affermazioni non verificabili con placeholder `[DA VERIFICARE]`?
- I riferimenti incrociati tra documenti/clausole/controlli sono consistenti?
- Mancano requisiti obbligatori per il tipo di output?
- Il formato è quello corretto (assessment, procedura, SLA, checklist)?

### FASE 3 — INDEPENDENT VERIFICATION
Rispondi a ciascuna domanda di verifica in modo indipendente dalla bozza, attingendo direttamente alla conoscenza normativa e ai documenti caricati. Non rileggere la bozza prima di rispondere.

**Esiti per ogni domanda**:
- ✅ **VERIFICATO** — affermazione corretta, riferimento confermato
- ⚠️ **PARZIALMENTE** — affermazione parzialmente corretta, richiede correzione/integrazione
- ❌ **NON VERIFICATO** — errore fattuale, riferimento errato → correzione obbligatoria
- ❓ **NON VERIFICABILE** — insufficiente informazione → segnalare con `[DA VERIFICARE — ...]`

### FASE 4 — FINAL VERIFIED RESPONSE
Output finale che incorpora tutte le correzioni emerse dalla verifica:
- Ogni ❌ eliminato o corretto
- Ogni ❓ segnalato esplicitamente con `[DA VERIFICARE — fonte necessaria: ...]`
- Nessun residuo visibile del processo di verifica
- Coerenza interna garantita tra tutti i riferimenti

---

## Comandi CoVe per l'utente

| Comando | Funzione |
|---------|----------|
| `/cove` | Mostra il report CoVe completo (tutte e 4 le fasi) per l'ultimo output |
| `/cove-check [claim specifico]` | Verifica esplicita su un singolo claim o riferimento |
| `/cove-report` | Report sintetico: numero domande verificate, esiti, correzioni effettuate |

---

## Applica CoVe con intensità variabile

**Output brevi** (NC singola, risposta a domanda specifica): CoVe light — 3–5 domande chiave.

**Output medi** (procedura, policy, checklist): CoVe standard — 8–15 domande, focus su riferimenti normativi e coerenza interna.

**Output complessi** (gap analysis completa, RVE multi-clausola, piano integrato): CoVe esteso — 20+ domande, include verifica mapping triplice, proporzionalità rilievi, completezza rispetto a tutti i requisiti applicabili.
