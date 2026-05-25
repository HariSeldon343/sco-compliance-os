---
description: "Settori italiani rafforzati (Legge 132/2025 Capo II)"
---

# /settori — Settori italiani rafforzati (Legge 132/2025 Capo II)

## Uso
`/settori [settore]`

## Quando
Per mappare gli obblighi aggiuntivi che la Legge 132/2025 pone sui settori strategici italiani, in aggiunta agli obblighi AI Act. La Legge 132 non sostituisce l'AI Act (principio di complementarità Art. 1 c. 5), ma impone requisiti informativi, di governance, di documentazione ulteriori.

## Pre-requisiti

- Scoping completato (`/scope`).
- Ruolo regolatorio mappato (`/ruoli`).

## Settori coperti

### 1. Sanità (Art. 7-10)

Campo: uso di IA in prevenzione, diagnosi, cura, riabilitazione, scelta terapeutica, organizzazione sanitaria.

Obblighi:
- Garantire che la decisione finale resti del professionista sanitario.
- Informare il paziente in forma comprensibile su uso dell'IA, logica di base, benefici, rischi, alternative.
- Consenso informato esteso agli aspetti IA.
- Tracciabilità delle decisioni assistite dall'IA.
- Integrazione con obblighi Gelli-Bianco (L. 24/2017): risk management clinico include IA.
- Integrazione con accreditamento istituzionale regionale.
- Registro nazionale IA in sanità (Art. 8) — attuazione via decreto delegato.

Riferimenti incrociati: AI Act Art. 6 + Allegato III punto 5 lett. c (servizi sanitari privati classificati alto rischio); AI Act Art. 14 sorveglianza umana.

### 2. Lavoro (Art. 11-12)

Campo: uso di IA in reclutamento, selezione, organizzazione del lavoro, gestione, valutazione, monitoraggio, terminazione, sicurezza.

Obblighi:
- Informativa scritta al lavoratore ex Art. 1-bis D.Lgs. 152/1997 (come modificato dal Decreto Trasparenza): contenuto, modalità d'uso, logica del sistema, impatti.
- Procedura di contestazione delle decisioni automatizzate (art. 11 Legge 132).
- Coinvolgimento RSA/RSU per decisioni riguardanti gestione del personale.
- Divieto di sistemi che categorizzano emozioni sul luogo di lavoro (AI Act Art. 5 lett. f).
- Rispetto dignità e salute del lavoratore.

Riferimenti incrociati: AI Act Allegato III punto 4 (occupazione, gestione lavoratori) → alto rischio; D.Lgs. 152/1997 modificato; Statuto dei Lavoratori art. 4 controlli a distanza.

### 3. Professioni intellettuali (Art. 13)

Campo: uso di IA da parte di avvocati, commercialisti, medici, ingegneri, architetti, consulenti.

Obblighi:
- L'uso dell'IA deve essere "strumentale": la decisione resta del professionista.
- Informativa al cliente sull'uso dell'IA.
- Rispetto del segreto professionale.
- Adeguamento dei codici deontologici (in corso).

Riferimenti incrociati: ordini professionali, codici deontologici; CNF, CNDCEC, FNOMCeO, CNI, ecc.

### 4. Pubblica Amministrazione (Art. 14)

Campo: uso di IA nell'attività amministrativa da parte di PP.AA. statali, regionali, locali.

Obblighi:
- Rispetto dei principi di legalità, imparzialità, buon andamento (Art. 97 Cost.).
- Motivazione del provvedimento che integri esplicitamente l'uso dell'IA.
- Tracciabilità e verificabilità.
- Controllo umano significativo.
- Accesso civico e informativa al cittadino.
- Accreditamento tramite AgID (Art. 20).

Riferimenti incrociati: L. 241/1990 procedimento amministrativo; Codice amministrazione digitale (D.Lgs. 82/2005); Piattaforme Notificazione Digitale (PDND); linee guida AgID.

### 5. Attività giudiziaria (Art. 15)

Campo: uso di IA nell'amministrazione della giustizia.

Obblighi:
- L'IA può supportare attività strumentali (organizzazione, ricerca giurisprudenziale, analisi documentale).
- **Divieto** di uso dell'IA per la decisione in senso proprio.
- La decisione resta sempre del magistrato umano.
- Tracciabilità dell'uso.
- Riferimento a Regolamento del Consiglio d'Europa e principi CEPEJ.

Riferimenti incrociati: AI Act Allegato III punto 8 (amministrazione giustizia) → alto rischio; limiti tassativi.

### 6. Minori

Campo: uso di IA rivolto a minori o che tratta dati di minori.

Obblighi:
- Consenso parentale per minori sotto i 14 anni (Art. 2-quinquies Codice Privacy confermato da Legge 132).
- Tutela specifica contro pratiche vietate Art. 5 AI Act (manipolazione, sfruttamento vulnerabilità).
- Design age-appropriate.
- Integrazione con Codice di autoregolamentazione Media e Minori.

Riferimenti incrociati: GDPR Art. 8; Convenzione ONU sui diritti del fanciullo.

## Output

Scheda settore:

1. **Settore attivato**: [sanità / lavoro / professioni / PA / giustizia / minori / altro].
2. **Fondamento**: articolo Legge 132 + articoli correlati AI Act.
3. **Obblighi aggiuntivi rispetto ad AI Act standard**: elenco puntato.
4. **Autorità competenti**: AgID/ACN + autorità settoriali (AGENAS, Garante Privacy, Ispettorato nazionale lavoro, ordini professionali).
5. **Documenti richiesti**: informative, consensi, registri, procedure.
6. **Rischi specifici**: criticità di non conformità settoriale.
7. **Interconnessioni**: rinvii puntuali a norme di dominio già applicabili.

## Regole operative

- L'applicabilità settoriale va **verificata caso per caso**: un'organizzazione può operare in più settori simultaneamente (es. ospedale = sanità + lavoro + minori).
- I decreti delegati attesi entro il 10/10/2026 (Art. 16-18) potranno specificare ulteriormente gli obblighi: mantenere il monitoraggio normativo.
- Per strutture sanitarie, integra sempre con accreditamento regionale e risk management clinico (`audit-iso-9001-sanita`).
- Per organizzazioni con SGSL (ISO 45001), integra gli obblighi sul lavoro con sicurezza sul lavoro.

## Documenti collegati

- `../references/legge-132-2025.md` (Art. 7-15)
- `../references/ai-act-2024.md` (Allegato III)
