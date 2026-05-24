# ISO/IEC 20000-1:2018 — Framework di riferimento dettagliato

## Struttura normativa

ISO/IEC 20000-1:2018 è lo standard internazionale per i Sistemi di Gestione dei Servizi IT (SMS). Adotta la struttura HLS (Harmonized Structure / Annex SL) condivisa con ISO 27001, ISO 9001, ISO 22301: clausole 4–10 identiche nel framework, con requisiti specifici per i servizi IT nei gruppi 8.x.

**Termini fondamentali**:
- **SMS** (Service Management System): sistema di gestione per pianificare, progettare, erogare, monitorare e migliorare i servizi IT
- **Catalogo dei servizi**: elenco formale dei servizi erogati, con caratteristiche, dipendenze e responsabilità
- **SLA** (Service Level Agreement): accordo contrattuale sui livelli di servizio con il cliente
- **OLA** (Operational Level Agreement): accordo interno tra unità operative che contribuiscono al servizio
- **UC** (Underpinning Contract): contratto con fornitori esterni a supporto del servizio
- **CMDB** (Configuration Management Database): repository dei CI e delle loro relazioni
- **CI** (Configuration Item): componente gestito nell'SMS (HW, SW, rete, documentazione, servizio)
- **RFC** (Request for Change): richiesta formale di modifica a un CI o al servizio
- **CAB** (Change Advisory Board): organo che valuta e autorizza i change non standard
- **PIR** (Post-Implementation Review): revisione post-implementazione change
- **KEDB** (Known Error Database): registro degli errori noti con workaround documentati
- **RTO** (Recovery Time Objective) per servizio: tempo massimo di ripristino del servizio
- **RPO** (Recovery Point Objective) per servizio: massimo dato/transazione perdibile
- **SCAT** (Service Continuity Assessment Tool): strumento per la valutazione della continuità
- **Major Incident**: incidente ad alto impatto che richiede procedura escalation speciale
- **KPI operativi**: metriche di performance del servizio (disponibilità, MTTR, MTBF, SLA compliance)

---

## Clausola 4 — Contesto dell'organizzazione

**4.1** Comprendere l'organizzazione e il suo contesto (fattori interni/esterni, parti interessate, requisiti del servizio). Novità Amendment 1 ISO 27001: considerare il cambiamento climatico — applicare analoga attenzione ai rischi ambientali sui servizi IT (es. data center flood risk, heat impact).

**4.2** Comprendere le esigenze e le aspettative delle parti interessate (clienti, utenti, fornitori, regolatori, owner IT).

**4.3** Determinare lo scope dell'SMS: perimetro dei servizi, sedi, clienti inclusi. Lo scope deve essere documentato e coerente con SLA firmati.

**4.4** SMS: l'organizzazione deve stabilire, implementare, mantenere e migliorare continuamente l'SMS, inclusi i processi e le loro interazioni.

*Mapping*: identico a ISO 27001 cl. 4. Particolarità 20000-1: lo scope include obbligatoriamente il catalogo dei servizi come documento di perimetro.

---

## Clausola 5 — Leadership

**5.1** Impegno della direzione: politica SMS, obiettivi, integrazione SMS nei processi aziendali, disponibilità risorse.

**5.2** Politica SMS: documentata, comunicata, disponibile. Deve includere impegno al rispetto dei requisiti e al miglioramento continuo.

**5.3** Ruoli, responsabilità, autorità: Service Owner, Process Owner, Service Manager. Matrice RACI obbligatoria per processi critici.

*Mapping NIS2*: [Art. 20 D.Lgs. 138/2024] impone alla Direzione accountability diretta sulla governance cyber — applicare alla governance SMS per i soggetti NIS2.

---

## Clausola 6 — Pianificazione

**6.1** Rischi e opportunità dell'SMS: risk assessment formale. Identificare rischi per: continuità del servizio, qualità SLA, supply chain, sicurezza.

**6.2** Obiettivi del servizio e pianificazione: SMART, misurabili, collegati ai KPI, con piani di miglioramento formali.

*Mapping*: ISO 27001 cl. 6.1 (rischi SGSI) + ISO 27005 (risk assessment). Per NIS2 soggetti essenziali/importanti: integrare risk assessment SMS con risk assessment di sicurezza.

---

## Clausola 7 — Supporto

**7.1–7.3** Risorse, competenze, consapevolezza: piano formazione staff IT e sicurezza, skill matrix, programma awareness.

**7.4** Comunicazione interna/esterna: piani di comunicazione per incidenti, change, manutenzioni programmate.

**7.5** Informazioni documentate: struttura documentale SMS (politica, procedure, istruzioni, registri). Controllo versioni, approvazione, distribuzione. Per dettaglio documentazione → `documentazione-sistema.md`.

---

## Clausola 8 — Operazioni

### 8.2 — Asset del servizio

Identificazione, classificazione e gestione degli asset necessari all'erogazione dei servizi (HW, SW, dati, licenze, contratti). Registro asset del servizio separato o integrato nel CMDB.

*Mapping*: [ISO 27001 A.5.9 — Inventario asset], [A.5.10 — Uso accettabile asset], [A.8.8 — Gestione vulnerabilità tecniche].

### 8.3 — Gestione della configurazione

**CMDB**: registro di tutti i CI con attributi (tipo, owner, versione, stato, relazioni), baseline configuration documentata. Scope del CMDB definito e approvato.

**Processi CMDB**: identificazione CI → registrazione → controllo → audit (verifica fisica vs CMDB) → reportistica.

**Baseline configuration**: snapshot approvata della configurazione in uno stato noto-buono. Prerequisito per change management efficace.

*Mapping*: [ISO 27001 A.8.9 — Gestione della configurazione], [A.8.32 — Gestione dei change].

### 8.4 — Gestione del cambiamento

**Tipi di change**:
- **Standard**: pre-approvato, basso rischio, procedura semplificata
- **Normale**: analisi impatto, approvazione CAB, pianificazione, test, rollback plan
- **Urgente (Emergency Change)**: procedura accelerata con approvazione ECAB, PIR obbligatoria successiva

**Processo**: RFC → classificazione → analisi impatto/rischio → approvazione (CAB o ECAB) → pianificazione → implementazione → test → chiusura RFC → PIR (per change normali).

**CAB** (Change Advisory Board): frequenza minima settimanale, ruoli definiti (Change Manager, Service Owner, Security, Operations, Business).

**Freeze period**: periodi di blocco change (fine anno, eventi critici business) formalmente dichiarati.

*Mapping*: [ISO 27001 A.8.32 — Gestione dei change], [Art. 21.2.e NIS2 — sicurezza nella acquisizione, sviluppo e manutenzione].

### 8.5 — Progettazione, costruzione e transizione del servizio

Gestione del ciclo di vita dei servizi nuovi o modificati: requisiti → progettazione → build → test → release → transizione in produzione.

**Release Management**: piano di release, test in ambiente pre-produzione, criteri di accettazione, rollback plan, comunicazione agli utenti.

*Mapping*: [ISO 27001 A.8.25 — Secure development lifecycle], [A.8.29 — Security testing], [A.8.30 — Outsourced development].

### 8.6.1 — Incident Management

**Classificazione priorità**:
| Priorità | Impatto | SLA Risposta | SLA Risoluzione |
|----------|---------|--------------|-----------------|
| P1 — Critica | Servizio non disponibile / utenti critici bloccati | 15 min | 4 ore |
| P2 — Alta | Degradazione significativa / workaround non disponibile | 30 min | 8 ore |
| P3 — Media | Impatto limitato / workaround disponibile | 2 ore | 24 ore |
| P4 — Bassa | Basso impatto / richiesta informazioni | 8 ore | 72 ore |

**Processo**: segnalazione → registrazione → classificazione/priorità → diagnosi → escalation (funzionale/gerarchica) → risoluzione → chiusura → customer satisfaction.

**Major Incident Procedure**: attivazione automatica per P1 prolungato, War Room, comunicazione stakeholder, Post-Incident Review obbligatoria entro 5gg.

**Handoff Problem Management**: incidenti P1, incidenti ricorrenti (≥3 occorrenze in 30gg), incidenti con impatto significativo → apertura Problem Record.

*Mapping integrato*:
- [ISO 27001 A.5.24 — Pianificazione gestione incidenti sicurezza]
- [ISO 27001 A.5.25 — Valutazione e decisione su eventi sicurezza]
- [ISO 27001 A.5.26 — Risposta agli incidenti di sicurezza]
- [ISO 27001 A.5.27 — Apprendimento dagli incidenti di sicurezza]
- [ISO 27001 A.5.28 — Raccolta evidenze]
- [ISO 27001 A.8.15 — Logging]
- [Art. 23 D.Lgs. 138/2024 — Notifica incidenti NIS2]: early warning 24h → intermediate report 72h → final report 1 month
- [Legge 90/2024 Art. 7 — Notifica al CSIRT Italia]

### 8.6.2 — Problem Management

**Obiettivo**: identificare cause radice degli incidenti ricorrenti o ad alto impatto, prevenire ricorrenza.

**Processo**: identificazione problema (da incidenti, trend, proactive monitoring) → registrazione Problem Record → analisi causa radice (RCA: 5-Why, Ishikawa/Fishbone, Fault Tree Analysis) → identificazione Known Error → workaround documentato nel KEDB → soluzione permanente (RFC) → chiusura.

**KEDB** (Known Error Database): per ogni Known Error — descrizione, sintomi, workaround operativo, RFC di riferimento, stato (aperto/chiuso), impatto stimato.

*Mapping*: [ISO 27001 A.5.27 — Apprendimento dagli incidenti di sicurezza].

### 8.6.3 — Gestione richieste di servizio e accesso

Service Catalog: elenco richieste standard (installazioni SW, reset password, provisioning accessi). SLA specifici per richiesta. Processo di approvazione accessi integrato con [ISO 27001 A.5.18 — Diritti di accesso].

### 8.7.2 — Gestione disponibilità e capacità

**Disponibilità**: obiettivi per servizio (es. 99.9% su base mensile), misurazione, reportistica, piano miglioramento. Calcolo: MTBF / (MTBF + MTTR).

**Capacità**: pianificazione capacità a breve (operativa), medio (tattica), lungo termine (strategica). Monitoring utilizzo risorse, soglie di allerta.

*Mapping*: [ISO 27001 A.5.29 — Disponibilità delle informazioni], [Art. 21.2.b NIS2 — gestione degli incidenti], [Art. 21.2.c NIS2 — continuità operativa].

### 8.7.3 — Gestione della continuità del servizio

**SCAT** (Service Continuity Assessment): identificazione servizi critici, analisi impatto interruzione (BIA per servizio), RTO/RPO per servizio, dipendenze tecnologiche e umane.

**Piano di continuità del servizio**: strategie di ripristino, procedure di emergenza, responsabilità, contatti, testing schedule. Allineato con BCP/DRP ISO 22301.

**Test**: almeno annuale (tabletop, simulazione, full test), risultati documentati, piano di miglioramento post-test.

*Mapping integrato*: [ISO 22301 — BCMS], [ISO 27001 A.5.29, A.5.30], [Art. 21.2.c D.Lgs. 138/2024 — continuità operativa e gestione crisi NIS2].

### 8.7.5 — Gestione dei fornitori

**Registro fornitori**: nome, servizio fornito, tipo contratto (SLA/OLA/UC), referente, valutazione, rischio supply chain.

**SLA/OLA/UC**: KPI misurabili, penali, diritto di audit, clausole di sicurezza (GDPR, NIS2 supply chain, requisiti 27001).

**Valutazione fornitori**: periodica (almeno annuale), su base KPI, incident history, conformità sicurezza, capacità di risposta.

*Mapping*: [ISO 27001 A.5.19 — Sicurezza informazioni nelle relazioni con i fornitori], [A.5.20 — Requisiti sicurezza in contratti], [A.5.21 — Gestione sicurezza nella supply chain ICT], [A.5.22 — Monitoraggio, revisione e gestione modifiche fornitori], [Art. 21.2.d NIS2 — sicurezza della catena di approvvigionamento].

### 8.7.6 — Reportistica del servizio

**KPI obbligatori (esempi)**:
- Disponibilità del servizio (% mensile)
- SLA compliance (% incidenti risolti entro SLA per priorità)
- MTTR (Mean Time To Repair) per priorità
- MTBF (Mean Time Between Failures)
- Numero incidenti per priorità (trend mensile)
- Backlog problem aperti / chiusi
- Change success rate (% change senza incidenti post-implementazione)
- Customer Satisfaction Score (CSAT)

**Reportistica**: frequenza minima mensile per KPI operativi, trimestrale per riesame manageriale, annuale per riesame direzione.

*Mapping*: [ISO 27001 cl. 9.1 — Monitoraggio, misurazione, analisi e valutazione].

---

## Clausola 9 — Valutazione delle prestazioni

**9.1** Monitoraggio e misurazione: KPI di servizio, audit interni, customer satisfaction survey.

**9.2** Audit interni SMS: programma annuale risk-based, criteri, scope, frequenza. Indipendenza auditor.

**9.3** Riesame della direzione: agenda minima — performance KPI, risultati audit, NC aperte, rischi/opportunità, risorse, obiettivi, cambiamenti contesto.

*Mapping*: [ISO 27001 cl. 9 — Valutazione delle prestazioni].

---

## Clausola 10 — Miglioramento

**10.1** NC e azioni correttive: registrazione, analisi causa, azione correttiva, verifica efficacia, documentazione.

**10.2** Miglioramento continuo: piano annuale miglioramento, trend KPI, feedback clienti, benchmark.

*Mapping*: [ISO 27001 cl. 10].

---

## Integrazione SMS + SGSI: controlli condivisi

| Processo SMS | Controllo ISO 27001 | Area NIS2 |
|--------------|---------------------|-----------|
| Incident Management | A.5.24–A.5.28, A.8.15 | Art. 23 |
| Problem Management | A.5.27 | — |
| Change Management | A.8.32 | Art. 21.2.e |
| Configuration Mgmt | A.8.9 | Art. 21.2.e |
| Service Continuity | A.5.29, A.5.30, ISO 22301 | Art. 21.2.c |
| Supplier Management | A.5.19–A.5.22 | Art. 21.2.d |
| Access/Service Request | A.5.18 | Art. 21.2.i |
| Asset del Servizio | A.5.9, A.5.10 | Art. 21.2.a |
| Service Reporting | cl. 9.1 | Art. 21.1 |

---

## Matrice maturità di processo (scala CMM)

| Livello | Denominazione | Caratteristiche |
|---------|---------------|-----------------|
| 1 | Iniziale/Ad-hoc | Nessun processo formale; risultati imprevedibili; dipendenza da individui |
| 2 | Ripetibile/Gestito | Processi documentati di base; risultati ripetibili; KPI elementari |
| 3 | Definito/Standardizzato | Processi standardizzati, integrati, con procedure dettagliate; misurazione sistematica |
| 4 | Quantitativamente Gestito | Controllo statistico dei processi; obiettivi quantitativi; trend analysis |
| 5 | Ottimizzato | Miglioramento continuo basato su dati; innovazione sistematica; benchmarking |
