---
description: "Identificazione autorità competente"
---

# /autorita — Identificazione autorità competente

## Uso
`/autorita [fattispecie]`

## Quando
Per individuare quale autorità nazionale o UE è competente per una determinata fattispecie: notifica, autorizzazione, accreditamento, segnalazione, sanzione, reclamo. Strumento chiave in caso di incidente, richiesta, verifica.

## Pre-requisiti

- Ruolo regolatorio chiaro (`/ruoli`).
- Classificazione rischio AI Act (`/rischio-regolatorio`).
- Settori Legge 132 attivati (`/settori`).

## Autorità di riferimento

### Livello UE

| Autorità | Ambito |
|----------|--------|
| Commissione UE — AI Office | GPAI, modelli a rischio sistemico, standard armonizzati, linee guida AI Act |
| European AI Board | Coordinamento autorità nazionali |
| Corte di Giustizia UE | Interpretazione AI Act |

### Livello nazionale italiano (Legge 132 Art. 19-20)

| Autorità | Competenza |
|----------|-----------|
| **AgID** | Accreditamento sistemi IA PA, standard tecnici, linee guida applicative, sostegno attuativo |
| **ACN** (Agenzia Cybersicurezza Nazionale) | Cybersecurity sistemi IA; intersezione con NIS2 e Legge 90/2024 |
| **Comitato PCM IA** | Coordinamento politico settori strategici |
| **Garante Privacy** | GDPR + trattamenti dati personali anche automatizzati (Art. 22 GDPR) |
| **AGCOM** | Contenuti sintetici, trasparenza Art. 50, deepfake, piattaforme online |
| **Banca d'Italia / IVASS / CONSOB** | IA nel settore bancario, assicurativo, finanziario |
| **AGENAS** | IA nel settore sanitario (accreditamento, qualità) |
| **Ispettorato Nazionale Lavoro + INPS** | IA nel settore lavoro |
| **MITE / MIMIT** | Infrastrutture critiche, settori strategici |
| **Autorità di vigilanza settoriale** | Enti regolatori settoriali preesistenti |

### Decision tree

```
1) Il sistema è vietato ex AI Act Art. 5?
   SÌ → Autorità di sorveglianza nazionale (AgID/ACN) + sanzioni Art. 99 (35M€ / 7%)
   NO → prosegui

2) Il sistema è ad alto rischio ex Art. 6 + Allegato III?
   SÌ → Autorità di sorveglianza nazionale + eventuale autorità settoriale
        + obbligo registrazione EUDB gestita da Commissione
   NO → prosegui

3) È un GPAI?
   SÌ → AI Office UE (competenza primaria) + autorità nazionale come coordinamento
   NO → prosegui

4) È coperto da obblighi trasparenza Art. 50?
   SÌ → Autorità nazionale (AGCOM prevalente per deepfake e contenuti)
   NO → prosegui

5) Tratta dati personali?
   SÌ → Garante Privacy (anche cumulativamente con altre autorità)

6) Rientra in settore Legge 132 specifico?
   SÌ → autorità settoriale + AgID/ACN:
        • sanità: AGENAS + Regioni
        • lavoro: INL + INPS
        • PA: AgID
        • giustizia: Ministero Giustizia
        • professioni: ordini professionali

7) C'è incidente significativo?
   SÌ → notifica a tutte le autorità competenti ratione materiae:
        • AI Act Art. 73 (incidente grave) → autorità sorveglianza nazionale
        • GDPR Art. 33 (data breach) → Garante Privacy (72h)
        • NIS2 Art. 23 → CSIRT Italia + ACN (early warning 24h, notifica 72h)
        • Legge 90/2024 → CSIRT PA
```

## Output

Scheda:

1. **Fattispecie**: breve descrizione (es. "incidente grave su sistema di credit scoring").
2. **Autorità UE competenti**: elenco.
3. **Autorità italiane competenti**: elenco con ordine di priorità.
4. **Notifiche / adempimenti**: cosa va comunicato, a chi, entro quando.
5. **Termini**: timeline precisa (es. 15 giorni standard Art. 73 AI Act, 72 ore Art. 33 GDPR, 24 ore early warning NIS2).
6. **Documentazione a supporto**: cosa allegare o preparare.
7. **Rischio di overlap**: dove notifiche multiple sono dovute, coordinare per evitare incoerenze.

## Regole operative

- In caso di overlap (tipico), fare un unico "event report" interno e estrapolare le singole notifiche per ciascun destinatario.
- Per aziende con DPO, il DPO è punto di contatto per Garante Privacy ma non assorbe gli altri canali: è necessario un coordinamento multi-autorità.
- AgID e ACN hanno ruoli complementari: AgID governo e accreditamento; ACN dimensione cyber e sicurezza nazionale. Non sono alternative.
- Le notifiche ex Legge 90/2024 (PA) coesistono con NIS2 e AI Act: verifica matrice obblighi.
- Il Comitato PCM è organo politico: intervento per dossier strategici, non per adempimenti operativi.

## Documenti collegati

- `../references/decision-tree-autorita.md`
- `../references/legge-132-2025.md` (Art. 19-20)
- `../references/ai-act-2024.md` (Art. 70, 73, 99)
