---
description: "Programma audit interno AIMS"
---

# /audit — Programma audit interno AIMS

## Uso
`/audit [ambito|ciclo]`

## Quando
Per pianificare, condurre, reportare un audit interno AIMS (ISO/IEC 42001 cl. 9.2) integrato con verifica degli obblighi AI Act e Legge 132/2025. Utile anche come audit combinato con SGSI (ISO 27001), SGQ (ISO 9001), ITSM (ISO 20000-1).

## Pre-requisiti

- Scoping completato.
- Disponibilità del Statement of Applicability (`/soa`).
- Registro rischi aggiornato.
- Precedenti rapporti di audit e non conformità aperte.

## Struttura del deliverable

Insieme di documenti .docx articolati.

### 1. Programma audit pluriennale
- Ciclo triennale che copre tutte le clausole 4-10 e tutti i controlli SoA.
- Rotazione con focus annuale su tema critico (es. anno 1 sistemi ad alto rischio, anno 2 supplier management, anno 3 ciclo di vita).
- Integrazione con audit di altri SG (combined audit quando possibile).
- Tavola dei processi e delle funzioni da auditare.

### 2. Piano di audit (per singolo audit)
- Ambito (processi, clausole, controlli, sistemi IA inclusi).
- Criteri (norma, policy, procedure, obblighi normativi).
- Obiettivi (cosa si verifica).
- Team audit (competenze richieste, indipendenza, conflitti di interesse).
- Programma dei colloqui / giornate.
- Piano di campionamento (sistemi, record, log).

### 3. Checklist operativa
- Per ciascuna clausola 4-10, domande di verifica mappate su evidenze attese.
- Per ciascun controllo Appendice A applicabile, domanda di verifica.
- Per ciascun obbligo AI Act attivato (Art. 9-17, 26-27, 50, 72-73), domanda di verifica.
- Per ciascun principio Art. 3 Legge 132 e settore attivato, domanda di verifica.
- Colonna evidenza: documento, record, osservazione, intervista, test funzionale.

### 4. Riunione di apertura
- Conferma ambito, criteri, tempi.
- Presentazione team audit.
- Piano di comunicazione.
- Accordi su NC e SM (Spunti di Miglioramento).

### 5. Conduzione
- Interviste con: top management, AI governance lead, process owner, operations, security, data protection.
- Verifica documentale: politica AI, SoA, AIIA, FRIA (se deployer), registro rischi, documentazione tecnica Allegato IV, log, istruzioni d'uso.
- Verifica operativa: osservazione di processi, test di controllo, verifica di log di sistema.

### 6. Non conformità ed osservazioni
- Classificazione NC Maggiore / NC Minore / Osservazione / SM.
- Per ciascuna: requisito violato, evidenza oggettiva, proposta di azione.
- Collegamento al flusso `/nc`.

### 7. Riunione di chiusura
- Sintesi esiti.
- Elenco NC con classificazione.
- Accordi sul piano di trattamento e tempistiche.

### 8. Rapporto di audit
- Executive summary.
- Conclusioni su efficacia AIMS.
- Grado di maturità rilevato.
- NC e osservazioni in allegato.
- Raccomandazioni per il riesame di direzione.

## Regole operative

- **Indipendenza**: l'auditor non può verificare processi di cui è process owner.
- **Competenze**: il team deve coprire AIMS, AI Act, dominio applicativo, sicurezza informazioni, data protection.
- **Evidenze oggettive**: ogni rilievo deve essere supportato da documento, record, osservazione, intervista datata.
- **Riservatezza**: trattare i log di sistema come informazioni di sicurezza; conservare secondo policy.
- **Integrazione**: quando si audit cover anche 27001/27701/9001/20000-1, produrre un singolo rapporto con sezioni dedicate per evitare duplicazioni.
- **Proporzionalità**: la profondità di verifica deve essere proporzionale al livello di rischio AI Act dei sistemi in scope.
- **Follow-up**: pianificare verifica dell'efficacia delle azioni correttive entro 90-180 giorni.

## Documenti collegati

- `../references/iso42001-2023.md` (cl. 9.2, Appendice A)
- `../references/ai-act-2024.md`
- `../references/legge-132-2025.md`
- `../templates/audit-programme.md`
