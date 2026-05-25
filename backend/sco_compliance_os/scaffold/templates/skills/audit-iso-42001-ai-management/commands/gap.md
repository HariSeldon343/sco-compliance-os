---
description: "Gap analysis integrata 42001 + AI Act + Legge 132"
---

# /gap — Gap analysis integrata 42001 + AI Act + Legge 132

## Uso
`/gap [organizzazione]`

## Quando
Task complesso. Attiva CoV completo + pianificazione + allineamento. È il deliverable principe della skill: valuta lo stato attuale dell'organizzazione rispetto ai tre livelli normativi e produce piano di trattamento prioritizzato.

## Pre-requisiti

- Scoping regolatorio completato (usa prima `/scope`).
- Classificazione rischio AI Act determinata (usa `/rischio-regolatorio`).
- Ruoli regolatori mappati (usa `/ruoli`).

## Struttura del deliverable

Documento .docx articolato in 7 sezioni:

### 1. Executive summary
- Ambito dell'analisi.
- Scoping regolatorio: classificazione rischio AI Act, ruoli, settori italiani attivati.
- Sintesi dei gap per severity (Critico / Alto / Medio / Basso).
- Esposizione sanzionatoria (Art. 99 AI Act) e reputazionale.
- Raccomandazioni top-3.

### 2. Metodologia
- Framework di riferimento: ISO/IEC 42001:2023, Reg. (UE) 2024/1689, Legge 132/2025.
- Fonti consultate.
- Scala di maturità (Assente / Iniziale / Definito / Gestito / Ottimizzato).
- Scala di severity gap (Critico / Alto / Medio / Basso).
- Criteri di priorità (probabilità × impatto entro il livello di rischio regolatorio).

### 3. Gap rispetto a ISO/IEC 42001 (livello V — volontario)
- Per ciascuna clausola 4-10: requisito, stato attuale, gap, maturità, raccomandazione.
- Per ciascun controllo Appendice A applicabile (A.2.2 ÷ A.10.4): stato, applicabilità, giustificazione esclusione.
- Output tabellare + breve narrativa per clausola.

### 4. Gap rispetto ad AI Act (livello U — cogente UE)
- Solo se il sistema è classificato alto rischio, GPAI o soggetto a obblighi trasparenza.
- Per ciascun articolo rilevante (Art. 9 RMS, Art. 10 data governance, Art. 11 + All. IV documentazione tecnica, Art. 12 log, Art. 13 trasparenza, Art. 14 sorveglianza umana, Art. 15 accuratezza/robustezza/cybersecurity, Art. 16-17 QMS fornitore, Art. 26-27 deployer, Art. 50 trasparenza, Art. 72 post-market monitoring, Art. 73 reporting incidenti): stato, gap, scadenza applicativa, sanzione.
- Flag di **obbligatorietà** sempre presente.

### 5. Gap rispetto a Legge 132/2025 (livello N — cogente nazionale)
- Verifica dei sette principi Art. 3.
- Verifica dei settori rafforzati attivati (Art. 7-15) con obblighi informativi specifici.
- Verifica governance (Art. 19-20: notifica ad AgID/ACN, collegamento con Comitato PCM).
- Monitoraggio decreti delegati (Art. 16-18, attesi entro 10/10/2026).

### 6. Matrice integrata dei gap
Tabella consolidata con le colonne:

| ID | Area | Requisito | Livello (V/U/N) | Fonte puntuale | Stato | Severity | Azione | Owner | Deadline | Priorità | Sanzione potenziale |
|----|------|-----------|-----------------|----------------|-------|----------|--------|-------|----------|-----------|---------------------|

### 7. Piano di trattamento
- Quick wins (0-3 mesi).
- Azioni a medio termine (3-9 mesi).
- Azioni strutturali (9-18 mesi).
- Milestone allineate alle scadenze AI Act (02/08/2026 per alto rischio).
- Stima risorse (con placeholder `[DA INSERIRE]`).
- Dipendenze tra azioni.
- KPI di monitoraggio.

## Regole operative

- Ogni requisito elencato riporta sempre il livello V/U/N e la fonte puntuale.
- Obblighi AI Act e Legge 132 **mai** classificati come opzionali.
- I controlli Appendice A C e D ISO 42001 etichettati come "informativi" (non prescrittivi).
- Se la classificazione di rischio AI Act è "minimo" → sezione 4 è ridotta a una nota di non applicabilità, con eventuali requisiti di trasparenza Art. 50.
- Se il sistema è vietato (Art. 5) → il deliverable è una raccomandazione di dismissione/riprogettazione, non un gap plan.
- Per settori Legge 132 attivati, integra i rinvii alle discipline verticali (D.Lgs. 152/1997 lavoro, L. 24/2017 Gelli-Bianco, Codice privacy).

## Pianificazione e allineamento

Prima di produrre il deliverable:

1. Presenta piano di esecuzione in 5 step.
2. Chiedi conferma su: scope finale, profondità sulle singole aree, preferenze formato.
3. Segnala eventuali input mancanti con `[DA INSERIRE — fonte/dato necessario: ...]`.

## Documenti collegati

- `../references/iso42001-2023.md`
- `../references/ai-act-2024.md`
- `../references/legge-132-2025.md`
- `../references/matrice-cross-framework.md`
- `../templates/risk-register-ai.md`
