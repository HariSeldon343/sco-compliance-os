---
description: "Chain-of-Verification per deliverable AIMS"
---

# /cove — Chain-of-Verification per deliverable AIMS

## Uso
`/cove [deliverable]`

## Quando
Come quality assurance finale di **ogni output** prodotto dalla skill iso42001-integrato prima della consegna all'utente. Applicato SEMPRE a: `/gap`, `/aiia`, `/fria`, `/soa`, `/roadmap`, `/audit`, `/nc`. Opzionale ma consigliato per output rapidi (`/rischio-regolatorio`, `/ruoli`, `/autorita`).

## Le 5 fasi

### Fase 1 — Baseline
- Riprendere il deliverable prodotto.
- Identificare i claim verificabili: riferimenti normativi, classificazioni, obblighi, scadenze, sanzioni, mapping.
- Riassumere in forma di lista numerata.

### Fase 2 — Verification Planning
Per ogni claim, formulare **una domanda di verifica indipendente**:
- Il riferimento normativo è esatto? (articolo, comma, lettera, allegato)
- La classificazione è coerente con i criteri normativi?
- L'obbligo è effettivamente cogente o volontario?
- La scadenza è corretta?
- Il mapping cross-framework è puntuale?
- Il principio V/U/N è applicato correttamente?

### Fase 3 — Independent Verification
Rispondere a ciascuna domanda **in isolamento**, senza attingere al deliverable originale, solo alle fonti primarie:
- ISO/IEC 42001:2023 (UNI CEI ISO/IEC 42001:2024).
- Reg. (UE) 2024/1689 AI Act.
- Legge 132/2025.
- Normative correlate quando rilevanti.

Per ciascun claim assegnare esito:
- **V** — Verificato (corretto).
- **I** — Inaccurato (errore fattuale da correggere).
- **E** — Errato (errore grave, richiede riscrittura).
- **NV** — Non verificabile (claim troppo generico o fonte mancante, da riformulare o rimuovere).

### Fase 4 — Final Response
- Correggere tutti i claim con esito I, E, NV.
- Riscrivere le sezioni impattate.
- Aggiornare la tabella dei rinvii normativi.
- Verificare la coerenza interna dopo le correzioni.

### Fase 5 — Humanizer Pass
Applicare i principi di `amodeo-voice` e `disaiizzatore-normativo`:
- Rimuovere pattern AI: inflated symbolism, superficial -ing analyses, vague attributions, em dash overuse, regola del tre, parallelismi negativi, filler ("è importante notare che").
- Mantenere precisione tecnica e terminologia normativa.
- Rendere il registro coerente con lo stile professionale del consulente normativo.
- Verificare tono: professionale, preciso, senza formule di cortesia eccessive, senza emoji.
- Verificare coerenza con il destinatario (organizzazione committente, audit team, top management).

## Output

Report CoV in coda al deliverable (o in file separato):

### CoV Report

| Claim | Fonte richiesta | Esito | Azione |
|-------|-----------------|-------|--------|
| Art. X AI Act prevede Y | Reg. 2024/1689 Art. X | V | — |
| Scadenza Z = gg/mm/aaaa | Art. 113 AI Act | I | Corretto a gg/mm/aaaa |
| Obbligo cogente W | Legge 132 Art. ? | NV | Riformulato come requisito volontario 42001 |

### Sintesi
- Claim verificati: X/Y
- Claim corretti: N
- Claim rimossi: N
- Fase humanizer: completata / parziale

## Regole operative

- **Mai consegnare** un deliverable senza CoV quando è prodotto da `/gap`, `/aiia`, `/fria`, `/soa`, `/roadmap`, `/audit`.
- **Mai fidarsi** della memoria: verificare sempre sulle fonti primarie quando il claim coinvolge articoli, scadenze, sanzioni, classificazioni.
- Se un claim è NV perché la fonte primaria non è immediatamente disponibile, **riformularlo** con qualificatore esplicito: "salvo verifica puntuale del riferimento", oppure segnalarlo come `[VERIFICARE]`.
- **Coerenza V/U/N**: verificare che in tutto il deliverable ogni requisito sia correttamente etichettato.
- **Parallelismo ISO+AI Act+Legge 132**: verificare che nessuno dei tre framework sia stato "dimenticato" quando rilevante.
- Il passaggio humanizer non deve **alterare il contenuto tecnico**: solo la forma.
- Segnalare al lettore quando un riferimento normativo è recente (2024/2025/2026) e potrebbe essere oggetto di aggiornamento tramite decreto delegato o linea guida.

## Documenti collegati

- `../references/iso42001-2023.md`
- `../references/ai-act-2024.md`
- `../references/legge-132-2025.md`
- (integrazione con skill `amodeo-voice` e `disaiizzatore-normativo` quando disponibili)
