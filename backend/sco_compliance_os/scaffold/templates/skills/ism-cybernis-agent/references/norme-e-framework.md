# Norme e Framework — NIS2, ISO 27001, Legge 90/2024

## NIS2 — D.Lgs. 138/2024

### Struttura Art. 21 — Misure di gestione dei rischi

| Area | Requisito | Priorità |
|------|-----------|----------|
| 21.2.a | Politiche di sicurezza e analisi dei rischi | Alta |
| 21.2.b | Gestione degli incidenti | Alta |
| 21.2.c | Continuità operativa (BCP, DRP, gestione crisi) | Alta |
| 21.2.d | Sicurezza della catena di approvvigionamento | Alta |
| 21.2.e | Sicurezza nell'acquisizione, sviluppo e manutenzione | Alta |
| 21.2.f | Valutazione efficacia misure di gestione rischi | Media |
| 21.2.g | Pratiche di igiene informatica e formazione | Media |
| 21.2.h | Politiche sull'uso della crittografia | Alta |
| 21.2.i | Sicurezza delle risorse umane, controllo accessi, IAM | Alta |
| 21.2.j | Uso di autenticazione a più fattori (MFA) | Alta |

### Art. 23 — Notifica incidenti (timeline obbligatoria)

| Step | Termine | Contenuto |
|------|---------|-----------|
| Early Warning | 24h dall'awareness | Conferma incidente significativo; possibile causa intenzionale; impatto cross-border |
| Intermediate Report | 72h dall'awareness | Valutazione iniziale: gravità, impatto, indicatori di compromissione |
| Final Report | 1 mese | Descrizione completa: causa radice, misure adottate, impatto reale |

**Soglia "incidente significativo"** [Art. 23.3]: causa o può causare grave perturbazione operativa o perdite finanziarie; ha colpito o può colpire altri soggetti causando danni materiali/immateriali considerevoli.

### Art. 20 — Governance e responsabilità Direzione

Gli organi di gestione approvano le misure di gestione dei rischi, ne supervisionano l'attuazione, rispondono delle violazioni. Obbligo di formazione periodica per i membri della Direzione.

### Legge 90/2024 — Rafforzamento cybersicurezza nazionale

- **Art. 6**: obbligo notifica CSIRT entro 24h per PA e soggetti NIS2
- **Art. 7**: notifica ACN per incidenti che impattano infrastrutture critiche
- **Art. 8**: referente per la cybersicurezza (nomina obbligatoria per soggetti essenziali)
- **Art. 12**: misure minime sicurezza ICT PA (cfr. AgID)

### UNI/PdR 174:2024

Linee guida per la valutazione della conformità NIS2. Struttura in 13 aree tematiche, scala di maturità 1–5. Utilizzata da enti di certificazione italiani per assessment NIS2.

---

## ISO/IEC 27001:2022 + Amendment 1:2024

### Struttura HLS (clausole 4–10)

| Clausola | Contenuto |
|----------|-----------|
| 4 | Contesto: fattori interni/esterni, parti interessate, scope SGSI. Amendment 1: valutare cambiamento climatico in 4.1/4.2 |
| 5 | Leadership: impegno direzione, politica sicurezza, ruoli |
| 6 | Pianificazione: risk assessment (ISO 27005), risk treatment, SoA, obiettivi |
| 7 | Supporto: risorse, competenze, consapevolezza, comunicazione, documentazione |
| 8 | Operazioni: attuazione dei processi di risk treatment |
| 9 | Valutazione: monitoring KPI, audit interni, riesame direzione |
| 10 | Miglioramento: NC, azioni correttive, miglioramento continuo |

### Annex A — 93 controlli, 4 temi

**A.5 — Controlli Organizzativi (37 controlli)**
A.5.1 Politiche sicurezza | A.5.2 Ruoli e responsabilità | A.5.3 Segregazione compiti | A.5.4 Responsabilità manageriali | A.5.5 Contatti con autorità | A.5.6 Contatti con gruppi di interesse | A.5.7 Threat intelligence | A.5.8 Sicurezza nella gestione progetti | A.5.9 Inventario asset | A.5.10 Uso accettabile | A.5.11 Restituzione asset | A.5.12 Classificazione informazioni | A.5.13 Etichettatura | A.5.14 Trasferimento informazioni | A.5.15 Controllo accessi | A.5.16 Identity management | A.5.17 Informazioni di autenticazione | A.5.18 Diritti di accesso | A.5.19 Sicurezza fornitori | A.5.20 Sicurezza nei contratti | A.5.21 Supply chain ICT | A.5.22 Monitoraggio fornitori | A.5.23 Sicurezza servizi cloud | A.5.24 Pianificazione gestione incidenti | A.5.25 Valutazione eventi | A.5.26 Risposta incidenti | A.5.27 Apprendimento dagli incidenti | A.5.28 Raccolta evidenze | A.5.29 Disponibilità informazioni | A.5.30 Preparazione ICT continuità | A.5.31 Requisiti legali | A.5.32 Diritti di proprietà intellettuale | A.5.33 Protezione registrazioni | A.5.34 Privacy | A.5.35 Revisione indipendente | A.5.36 Conformità a politiche | A.5.37 Procedure operative documentate

**A.6 — Controlli People (8 controlli)**
A.6.1 Screening | A.6.2 Termini e condizioni | A.6.3 Consapevolezza e formazione | A.6.4 Processo disciplinare | A.6.5 Responsabilità post-impiego | A.6.6 Riservatezza | A.6.7 Telelavoro | A.6.8 Segnalazione eventi

**A.7 — Controlli Fisici (14 controlli)**
A.7.1–A.7.14: perimetri fisici, accesso fisico, sicurezza uffici/stanze/strutture, monitoraggio fisico, protezione da minacce fisiche/ambientali, lavoro in aree sicure, scrivania pulita, posizionamento e protezione attrezzature, sicurezza asset fuori sede, supporti rimovibili, politica schermo pulito, smaltimento attrezzature, manutenzione attrezzature, sicurezza cavi

**A.8 — Controlli Tecnologici (34 controlli)**
A.8.1 Endpoint | A.8.2 Accessi privilegiati | A.8.3 Restrizione accesso informazioni | A.8.4 Codice sorgente | A.8.5 Autenticazione sicura | A.8.6 Gestione capacità | A.8.7 Protezione malware | A.8.8 Gestione vulnerabilità | A.8.9 Gestione configurazione | A.8.10 Cancellazione informazioni | A.8.11 Data masking | A.8.12 DLP | A.8.13 Backup | A.8.14 Ridondanza | A.8.15 Logging | A.8.16 Monitoraggio | A.8.17 Sincronizzazione orologi | A.8.18 Utility privilegiate | A.8.19 Installazione SW | A.8.20 Sicurezza reti | A.8.21 Sicurezza servizi rete | A.8.22 Segregazione reti | A.8.23 Filtro web | A.8.24 Crittografia | A.8.25 Secure development | A.8.26 Requisiti sicurezza applicazioni | A.8.27 Architettura sicura | A.8.28 Secure coding | A.8.29 Security testing | A.8.30 Outsourced development | A.8.31 Separazione ambienti | A.8.32 Change management | A.8.33 Test di accettazione | A.8.34 Protezione sistemi in test

### Estensioni cloud

**ISO/IEC 27017:2015** — Controlli aggiuntivi per cloud:
CLD.6.3 (Ruoli e responsabilità CSP/CSC) | CLD.8.1 (Asset nel cloud) | CLD.9.5 (Separazione ambienti virtuali) | CLD.12.1 (Pianificazione capacità cloud) | CLD.12.4 (Logging e monitoraggio cloud) | CLD.13.1 (Sicurezza reti cloud)

**ISO/IEC 27018:2019** — Protezione PII nel cloud pubblico: A.1–A.12 (consenso, limitazione scopo, trasparenza, contabilità, accountability del CSP).

---

## Procedure CSQA

### IOP008 Rev. 22 — Conduzione audit di certificazione ISO 27001

Fasi del ciclo di certificazione:
- **Stage 1** (Desk Review): contesto, scope, SoA, risk assessment, audit interni, riesame → readiness assessment → proposta PDA
- **Stage 2** (On-site): implementazione effettiva clausole 4–10 + tutti i 93 controlli Annex A + CLD per cloud + requisiti 27018 se applicabile → RVE + NC/SM
- **Sorveglianza S1/S2**: audit interni e riesame direzione (obbligatori), azioni su NC precedenti, modifiche significative
- **Rinnovo**: efficacia complessiva triennio, revisione completa SoA e risk treatment plan

### Documenti di audit CSQA

| Documento | Descrizione |
|-----------|-------------|
| **RVE** | Rapporto di Verifica: documento principale con valutazione completa per clausola/controllo. Se GdV = solo RGV: autoportante (non richiede DDV separato) |
| **PDV** | Piano di Verifica: agenda, scope, criteri, metodo, campionamento, interviste |
| **PAC** | Piano di Audit Combinato (per multi-schema) |
| **PDA** | Proposta di Decisione di Accreditamento: integrata nel RVE |
| **DDV** | Diario di Verifica: usato da AVI, evidenze raccolte per aree assegnate |
| **RCD** | Rapporto di Conformità Documentale |
| **PVV** | Processo Verbale di Verifica |

**Regola LG_SG**: nel RVE non basta "conforme/non conforme" — serve valutazione completa con evidenze a supporto, interviste effettuate, campionamento e risultato. Il PDA viene integrato nel RVE. Parti non pertinenti: chiuse nel capitolo, non eliminate.

---

## Legge 132/2025 — AI e sicurezza informatica

Introduce obblighi per soggetti che utilizzano sistemi di IA in contesti critici. Integra con Reg. UE 2024/1689 (AI Act). Valutare nel SGSI: risk assessment per sistemi AI, controllo A.5.8 (sicurezza nella gestione progetti), A.8.25 (secure development lifecycle IA).

---

## Matrice correlazione NIS2 ↔ ISO 27001 ↔ NIST CSF 2.0 ↔ ISO 20000-1

| Requisito NIS2 | ISO 27001 | NIST CSF 2.0 | ISO 20000-1 |
|----------------|-----------|--------------|-------------|
| Art. 21.2.a — Risk management | cl. 6.1, A.5.1 | GV.RM, ID.RA | cl. 6.1 |
| Art. 21.2.b — Incident handling | A.5.24–A.5.28 | RS.MA, RS.CO | 8.6.1 |
| Art. 21.2.c — Business continuity | A.5.29, A.5.30, ISO 22301 | RC.RP | 8.7.3 |
| Art. 21.2.d — Supply chain | A.5.19–A.5.22 | ID.SC | 8.7.5 |
| Art. 21.2.e — Change/dev security | A.8.25, A.8.32 | PR.DS | 8.4, 8.5 |
| Art. 21.2.g — Cyber hygiene | A.6.3, A.8.7, A.8.8 | PR.AT | cl. 7 |
| Art. 21.2.h — Cryptography | A.8.24 | PR.DS | — |
| Art. 21.2.i — Access control | A.5.15–A.5.18 | PR.AA | 8.6.3 |
| Art. 21.2.j — MFA | A.8.5 | PR.AA | — |
| Art. 23 — Incident notification | A.5.24, A.5.26 | RS.CO | 8.6.1 |
