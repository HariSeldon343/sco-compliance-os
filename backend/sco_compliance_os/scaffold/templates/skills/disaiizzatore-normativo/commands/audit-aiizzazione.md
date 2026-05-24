# Comando `/audit-aiizzazione`

Esegue **solo** le Fasi 1 e 2 del CoVe (BASELINE + VERIFICATION PLANNING) producendo una **diagnosi** dei tell AI nel testo, **senza riscrivere**. Utile per:
- valutare la "AI-quotient" di un documento ricevuto da un collega
- decidere se vale la pena far girare `/disaiizza` o se il testo è già pulito
- imparare a riconoscere i propri tell AI ricorrenti

## Sintassi

```
/audit-aiizzazione
[testo da analizzare]
```

oppure:

```
/audit-aiizzazione file:<nome-file>
```

## Output format

```
═══════════════════════════════════════════════
AUDIT AIIZZAZIONE — Diagnosi
═══════════════════════════════════════════════

Documento analizzato: <descrizione o nome file>
Lunghezza: <N parole, M paragrafi>
Tipologia rilevata: <procedura ISO | DDV | gap analysis | perizia CTU | nota tecnica | altro>

AI-Quotient: <BASSO | MEDIO | ALTO | MOLTO ALTO>
   (calcolato come: numero tell AI / numero paragrafi)

Tell AI rilevati: <N>
   - Confidence ALTA:  <X>
   - Confidence MEDIA: <Y>
   - Confidence BASSA: <Z>

───────────────────────────────────────────────
TABELLA DEI RILIEVI
───────────────────────────────────────────────

| # | Posizione  | Passaggio                          | Categoria        | Conf. |
|---|-----------|------------------------------------|------------------|-------|
| 1 | §1, riga 2 | "rappresenta una pietra miliare"   | #1 enfasi        | ALTA  |
| 2 | §1, riga 4 | "garantendo al contempo"           | #3 gerundio      | ALTA  |
| 3 | §2, riga 1 | "approccio olistico e sinergico"   | #15 promozionale | ALTA  |
| 4 | §2, riga 3 | "in tal senso"                     | #5 connettore    | MEDIA |
| 5 | §3, riga 2 | "—"  (em dash)                     | #10 punteggiatura | ALTA |
| ... |          |                                    |                  |       |

───────────────────────────────────────────────
DISTRIBUZIONE PER CATEGORIA
───────────────────────────────────────────────

Categoria                           | Occorrenze
------------------------------------|------------
#1  Enfasi gonfiata                 | 3
#2  Trittici sinonimici             | 2
#3  Frasi participiali (gerundio)   | 5  ← dominante
#10 Em dash                          | 4
#14 Meta-discorso                    | 6  ← dominante
#15 Aggettivi promozionali           | 3

───────────────────────────────────────────────
RACCOMANDAZIONE
───────────────────────────────────────────────

[Una delle seguenti, in base all'AI-Quotient]

- AI-Quotient BASSO:
  Il testo è sostanzialmente pulito. Qualche rifinitura puntuale è 
  possibile ma non necessaria. /disaiizza non è strettamente richiesto.

- AI-Quotient MEDIO:
  Il testo presenta tell AI riconoscibili ma circoscritti. Si consiglia
  /disaiizza --modalita=conservativo per intervenire solo sui passaggi
  ad alta confidence.

- AI-Quotient ALTO:
  Il testo è chiaramente AI-generato e richiede una riscrittura strutturata.
  Si consiglia /disaiizza --modalita=standard.

- AI-Quotient MOLTO ALTO:
  Il testo è massivamente AI-generato. Anche dopo /disaiizza alcune sezioni 
  potrebbero richiedere una rielaborazione più profonda. Valutare se non sia 
  più rapido riscrivere alcune parti ex novo a partire dai dati di base.

───────────────────────────────────────────────
PASSAGGI NOTEVOLI (whitelist)
───────────────────────────────────────────────

I seguenti passaggi NON vanno toccati anche in caso di /disaiizza:

- §X, riga Y: citazione Art. <riferimento>  → whitelist normativa
- §Z, riga W: definizione ISO <numero>      → whitelist definizioni
```

---

## Calcolo dell'AI-Quotient

Soglie indicative (su 100 parole):

| Tell AI / 100 parole | AI-Quotient |
|---------------------|-------------|
| < 1                 | BASSO       |
| 1 – 3               | MEDIO       |
| 3 – 6               | ALTO        |
| > 6                 | MOLTO ALTO  |

L'AI-Quotient è una metrica orientativa, non un punteggio assoluto. Va sempre letta insieme alla distribuzione per categoria, perché 4 em dash valgono qualitativamente meno di 1 finale "ci si attende che i benefici si materializzino".

---

## Comportamenti speciali

### Se il testo è breve (< 100 parole)

Riportare i tell senza calcolare l'AI-Quotient (la metrica è instabile su campioni piccoli).

### Se il testo contiene formule che potrebbero essere AI ma sono whitelist

Riportarle nella sezione "Passaggi notevoli (whitelist)" con motivazione, in modo che l'utente capisca perché non sono state contate come tell.

### Se il testo è in lingua diversa dall'italiano

Segnalarlo. Il catalogo è tarato sull'italiano: i tell in inglese o altre lingue richiedono un catalogo diverso. Suggerire di usare la skill `humanizer` (in inglese) per testi inglesi.
