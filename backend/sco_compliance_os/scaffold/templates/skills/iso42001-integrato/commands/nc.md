---
description: "Non conformità e azione correttiva"
---

# /nc — Non conformità e azione correttiva

## Uso
`/nc [descrizione non conformità]`

## Quando
Per emettere, gestire, documentare una non conformità rilevata in ambito AIMS (ISO 42001 cl. 10.2) integrandola, quando pertinente, con gli obblighi normativi (AI Act: Art. 16 lett. j, Art. 20; Legge 132/2025: obblighi notifica autorità).

## Tipologia di NC gestite

- **NC di sistema AIMS** — deviazione da un requisito ISO/IEC 42001 rilevata in audit o in esercizio.
- **NC regolatoria AI Act** — violazione di un obbligo cogente (alto rischio, GPAI, trasparenza).
- **NC regolatoria Legge 132** — violazione di un principio o obbligo settoriale.
- **Incidente grave (Art. 73 AI Act)** — se qualifica come "serious incident", attiva anche `/sanzioni` e procedura di reporting specifica.
- **NC rilevata da terze parti** (deployer, utenti, autorità, segnalazioni interne).

## Struttura del deliverable

Documento .docx + registro .xlsx aggiornato.

### Scheda NC

| Campo | Contenuto |
|-------|-----------|
| ID NC | Progressivo univoco |
| Data rilevamento | |
| Fonte | audit interno / esterno / segnalazione / monitoraggio / cliente |
| Descrizione oggettiva | Fatto rilevato, evidenze, contesto |
| Requisito violato | Rinvio puntuale a: clausola ISO 42001 / articolo AI Act / articolo Legge 132 / altro |
| Classificazione | Maggiore / Minore / Osservazione |
| Severity regolatoria | Critica / Alta / Media / Bassa (basata su esposizione sanzionatoria) |
| Rischio associato | Rimando al registro rischi IA |
| Correzione immediata | Azione di contenimento |
| Analisi causa profonda | RCA (5 perché, Ishikawa, altro) |
| Azione correttiva | Intervento per eliminare causa |
| Owner | |
| Scadenza | |
| Efficacia | Criterio di verifica + esito |
| Chiusura | Data, verificatore, stato |

### Flusso decisionale

1. **Rilevamento** → apertura scheda in registro.
2. **Qualificazione** → distinguere se la NC attiva obblighi normativi aggiuntivi.
3. **Notifiche** (se pertinenti):
   - Autorità nazionale (AgID/ACN) ex Legge 132 Art. 19-20 per determinate NC.
   - Autorità di sorveglianza ex AI Act Art. 20 (fornitore) o Art. 73 (incidenti gravi: 15 giorni standard, 2 giorni violazione diritti fondamentali).
   - Garante Privacy ex GDPR Art. 33 se data breach.
   - ACN ex NIS2 Art. 23 se soggetto essenziale/importante con incidente significativo.
4. **Contenimento** immediato.
5. **RCA**: analisi causa profonda.
6. **Piano di azione correttiva**: misure strutturali per evitare ricorrenza.
7. **Implementazione**.
8. **Verifica di efficacia** a distanza congrua.
9. **Chiusura** con lesson learned e aggiornamento AIMS.

## Regole operative

- Non chiudere una NC senza verifica di efficacia documentata.
- Se la NC tocca un controllo Appendice A valutato "Ottimizzato" nella SoA, riesaminare la maturità.
- Le NC regolatorie AI Act e Legge 132 **non ammettono classificazione "Osservazione"**: minimo "Minore".
- Un "incidente grave" ex Art. 3 n. 49 AI Act → obbligo di reporting entro termini stretti, la NC interna è un secondo registro paralelo alla notifica.
- Le NC collegate a sistemi ad alto rischio richiedono aggiornamento della documentazione tecnica Allegato IV.
- Collega sempre la NC al registro rischi (la NC può innescare revisione del rating di rischio).

## Documenti collegati

- `../references/iso42001-2023.md` (cl. 10.2)
- `../references/ai-act-2024.md` (Art. 20, 73)
- `../references/legge-132-2025.md` (Art. 19-20)
- `../templates/serious-incident-report.md`
