---
description: "Fundamental Rights Impact Assessment (AI Act Art. 27)"
---

# /fria — Fundamental Rights Impact Assessment (AI Act Art. 27)

## Uso
`/fria [sistema]`

## Quando
Obbligatorio per i **deployer** di sistemi IA ad alto rischio ex Allegato III quando:
- sono organismi di diritto pubblico,
- forniscono servizi pubblici,
- valutano merito creditizio o affidabilità (eccetto rilevamento frodi finanziarie),
- valutano rischi e prezzi nell'assicurazione vita e salute.

Va eseguito prima del primo impiego del sistema. Notifica all'autorità di sorveglianza con modulo dedicato entro il rilascio. Integrabile con DPIA GDPR se già presente.

## Pre-requisiti

- Sistema classificato alto rischio (`/rischio-regolatorio`).
- Ruolo di deployer confermato (`/ruoli`).
- Contesto d'uso ed organizzazione chiaramente definiti.

## Struttura del deliverable

Documento .docx in 6 sezioni (modello coerente con template EU FRIA quando disponibile).

### 1. Descrizione dell'uso
- Processi del deployer in cui il sistema sarà usato.
- Periodo e frequenza d'uso.
- Categorie di persone fisiche o gruppi impattati.
- Rischi specifici di danno (scala, gravità, reversibilità).

### 2. Valutazione dei rischi per i diritti fondamentali
Mappa su diritti rilevanti della Carta dei diritti fondamentali UE:
- Dignità (Art. 1).
- Non discriminazione ed eguaglianza (Art. 20-21).
- Rispetto della vita privata e familiare, protezione dei dati (Art. 7-8).
- Libertà di espressione e informazione (Art. 11).
- Diritto di asilo / migranti (Art. 18).
- Tutela dei consumatori (Art. 38).
- Diritti del lavoratore (Art. 27-31).
- Diritti del minore (Art. 24).
- Tutela giudiziaria effettiva (Art. 47).

Per ciascun diritto rilevante: scenario di lesione, probabilità, gravità, categorie esposte.

### 3. Misure di sorveglianza umana
- Ruoli e qualifica delle persone incaricate della sorveglianza (Art. 14).
- Poteri di intervento (stop, override, segnalazione).
- Formazione e istruzioni d'uso.
- Evidenza tracciabile dell'esercizio della sorveglianza.

### 4. Misure in caso di materializzazione del rischio
- Procedura di gestione eventi avversi.
- Meccanismi di reclamo interno ed esterno (inclusi soggetti terzi).
- Comunicazioni a soggetti impattati.
- Obblighi Art. 73 (reporting incidenti gravi) se applicabili.

### 5. Governance e accountability
- Owner della FRIA.
- Integrazione con DPIA GDPR (se già esistente).
- Collegamento con la politica AI aziendale e con l'AIMS.
- Notifica all'autorità di sorveglianza (Art. 27 c. 3).

### 6. Revisione
- Condizioni di trigger per aggiornamento (modifiche al sistema, cambio contesto, segnalazioni, evoluzione normativa).
- Frequenza minima (almeno annuale).
- Audit trail delle versioni.

## Regole operative

- Quando esiste già una DPIA conforme al GDPR Art. 35, integra gli elementi aggiuntivi FRIA senza duplicare.
- Il FRIA è **obbligo del deployer**, non del fornitore. Se il soggetto cumula entrambi i ruoli, esegui entrambi i workflow.
- La notifica all'autorità deve avvenire tramite il modulo predisposto dalla Commissione (Art. 27 c. 5).
- Coinvolgi AI ethics lead, DPO, legal, HR (se uso impatta lavoratori), funzioni operative.
- Collegamento con Legge 132/2025: settori sanità, lavoro, PA attivano obblighi informativi aggiuntivi che vanno riflessi nel FRIA.

## Documenti collegati

- `../references/ai-act-2024.md` (Art. 27)
- `../references/legge-132-2025.md` (Art. 7-15 per settori)
- `../templates/fria-report.md`
