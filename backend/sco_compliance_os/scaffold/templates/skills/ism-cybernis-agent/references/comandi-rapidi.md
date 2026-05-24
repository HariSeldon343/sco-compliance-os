# Comandi Rapidi — Descrizioni Complete

## Comandi SMS (ISO 20000-1)

### `/gap-sms`
Gap analysis ISO/IEC 20000-1:2018, clausole 4–10. Produce: tabella per clausola con stato (Conforme / Parziale / Non Conforme / N.A.), livello di maturità, gap identificato, azione correttiva, priorità, owner, scadenza. Usa formato assessment obbligatorio. Chiedi se disponibili documenti SMS da analizzare.

### `/gap-integrato`
Gap analysis combinata ISO 20000-1 + ISO 27001 + NIS2/Legge 90. Per ogni area, mostra il gap nei tre framework e le interdipendenze. Produce matrice consolidata con priorità integrate. Particolarmente utile per soggetti NIS2 che devono ottimizzare l'adeguamento su più standard contemporaneamente.

### `/assessment [processo/controllo]`
Valutazione approfondita di un singolo processo SMS o controllo ISO 27001. Usa il formato obbligatorio: riferimento, incidenza, qualità, tipo rilievo (3–4 righe strutturate), note estese (min 8–10 righe con evidenze, mapping triplice, azioni). Esempio: `/assessment incident-management` | `/assessment A.8.9` | `/assessment 8.4-change`.

### `/checklist-sms [area]`
Genera checklist di audit per processo SMS. Struttura: clausola/requisito | domanda di verifica | evidenza attesa | esito (C/NC/N.A.) | note. Aree disponibili: incident | problem | change | configuration | continuity | supplier | full (tutte le aree).

### `/procedura [processo]`
Bozza procedura operativa SMS o SGSI. Usa il template struttura procedura da `documentazione-sistema.md`. Processi SMS: incident-management | problem-management | change-management | configuration-management | service-continuity | supplier-management | service-request | service-reporting. Processi SGSI: gestione-incidenti-sicurezza | vulnerability-management | backup | change-security | risk-assessment.

### `/sla [servizio]`
Template SLA completo per il servizio specificato. Include: descrizione servizio, orari, SLO con KPI misurabili e penali, classificazione incidenti P1–P4, matrice escalation, reportistica, revisione. Chiedi: nome servizio, cliente, orari copertura, piattaforme critiche, SLO target richiesti.

### `/catalogo-servizi`
Template catalogo dei servizi SMS. Struttura per servizio: ID, nome, descrizione, utenti destinatari, componenti tecnici (CI associati), SLA di riferimento, owner del servizio, dipendenze (OLA/UC), stato (Attivo/In sviluppo/Dismissione), costo indicativo. Genera in formato tabellare o strutturato per documento.

### `/cmdb`
Template CMDB con attributi minimi per CI (vedi `documentazione-sistema.md`). Include: struttura registro CI, tipi di CI supportati, processo di aggiornamento, frequenza riconciliazione, integrazione con Change e Incident Management. Chiedi: piattaforma CMDB in uso (ServiceNow, Jira, Excel, altro) per adattare il formato.

### `/incidente-integrato`
Procedura unificata che integra: Incident Management ISO 20000-1 §8.6.1 (classificazione P1–P4, SLA, escalation, Major Incident) + Gestione incidenti di sicurezza ISO 27001 A.5.24–A.5.28 (identificazione, valutazione, risposta, apprendimento, raccolta evidenze) + Notifica NIS2 Art. 23 (early warning 24h → intermediate 72h → final report 1 month) + Notifica Legge 90/2024. Include: matrice di decisione "è un incidente di sicurezza significativo NIS2?", workflow integrato, modello di notifica CSIRT.

### `/continuita-servizio`
Piano di continuità del servizio ISO 20000-1 §8.7.3. Include: SCAT (identificazione servizi critici, BIA per servizio), RTO/RPO per servizio, strategie di ripristino, procedure operative, test plan (tabletop/simulazione/full test), integrazione con BCP ISO 22301. Chiedi: servizi in scope, RTO/RPO attuali o desiderati, infrastruttura DR disponibile.

### `/matrice-sms`
Matrice di correlazione completa: ISO 20000-1:2018 ↔ ISO/IEC 27001:2022 ↔ NIS2 D.Lgs. 138/2024. Per ogni processo/area: clausola 20000-1, controllo 27001, articolo NIS2, livello di integrazione (Alto/Medio/Basso), note operative. Utile per pianificare audit combinati e ottimizzare la documentazione condivisa.

### `/kpi [servizio]`
Dashboard KPI per il servizio specificato. Include: disponibilità mensile, MTTR, MTBF, SLA compliance per priorità, change success rate, CSAT, backlog problem/NC aperte. Con formule di calcolo, soglie alert (verde/giallo/rosso), frequenza di misurazione, fonte dati.

### `/riesame-sms`
Struttura agenda e verbale riesame direzione SMS (cl. 9.3). Include tutti i punti obbligatori (vedi `documentazione-sistema.md`), formato verbale con sezioni Input/Discussione/Decisioni/Azioni per ogni punto, integrazione con riesame direzione SGSI per audit combinati.

---

## Comandi SGSI (ISO 27001)

### `/rve [clausola/controllo]`
Bozza di valutazione RVE (Rapporto di Verifica) CSQA per la clausola o controllo specificato. Formato: riferimento normativo → VALUTAZIONE (descrizione completa: cosa verificato, come, conclusione — mai solo "conforme") → EVIDENZE A SUPPORTO (documenti, interviste, campionamento) → ESITO (Conforme / NC Maggiore / NC Minore / SM). Segue LG_SG CSQA.

### `/pdv [fase] [durata-giorni]`
Bozza Piano di Verifica CSQA per la fase specificata (Stage1 | Stage2 | Sorveglianza | Rinnovo). Include: obiettivo, scope, criteri, metodo, campionamento, agenda con slot temporali, interviste pianificate, documenti da esaminare, risorse GdV. Adatta durata in base ai giorni indicati.

### `/soa`
Statement of Applicability integrato: ISO 27001:2022 (93 controlli A.5–A.8) + ISO/IEC 27017 (controlli CLD aggiuntivi) + ISO/IEC 27018 (requisiti A.1–A.12). Per ogni controllo: applicabilità (S/N), giustificazione esclusione se N.A., stato implementazione, evidenza. Chiedi: scope SGSI, presenza cloud (CSP/CSC), trattamento PII nel cloud.

### `/gap [framework]`
Gap analysis per: NIS2 | 27001 | L.90 | NIST | integrato. Framework NIS2: 13 aree Art. 21 con livello maturità 1–5. Framework 27001: clausole 4–10 + 93 controlli Annex A. Framework integrato: tutti e tre simultaneamente con mapping consolidato.

### `/risk [area]`
Risk assessment ISO 27005/31000/NIS2. Per area specificata: asset/processo, minacce, vulnerabilità, impatto (C/I/A), probabilità, rischio inerente, controlli esistenti, rischio residuo, trattamento (accettare/mitigare/trasferire/evitare), owner, scadenza.

### `/bcp [scope]`
Business Impact Analysis, Business Continuity Plan, Disaster Recovery Plan. BIA: identificazione processi critici, MTPD, RTO, RPO, dipendenze IT. BCP: strategie, procedure attivazione, ruoli e responsabilità, comunicazione. DRP: procedure ripristino tecnico, test plan.

### `/incidente [tipo]`
Procedura/workflow per: incidente-sicurezza | violazione-dati-gdpr | ransomware | data-breach | DDoS. Include: criteri di identificazione, passi di risposta, notifiche obbligatorie (CSIRT, Garante Privacy, ACN), raccolta evidenze forensi, comunicazione, post-incident review.

---

## Comandi NIS2

### `/assessment [area-nis2]`
Assessment di un'area NIS2 (Art. 21.2.a–j). Formato standard con incidenza, qualità, tipo rilievo, note. Include riferimento UNI/PdR 174:2024 per la scala di maturità.

### `/piano [tipo]`
Piano per: adeguamento-NIS2 | adeguamento-L90 | audit-annuale | formazione | trattamento-rischi. Include: obiettivi, azioni, owner, scadenze, risorse, dipendenze, KPI di avanzamento.

### `/matrice [tipo]`
Matrici disponibili: NIS2-27001-NIST (correlazione completa) | RACI-SMS (per tutti i processi) | BIA (per servizi critici) | rischi (probabilità-impatto).

---

## Comandi generici

### `/nc [descrizione]`
Formula rilievo di Non Conformità. Include: tipo (Maggiore/Minore), riferimento normativo preciso, descrizione stato attuale, requisito violato, evidenza a supporto, azione correttiva suggerita. Ogni NC = un solo punto della norma.

### `/sm [descrizione]`
Formula Spunto di Miglioramento o Osservazione. Include: area di miglioramento, requisito di riferimento, opportunità identificata, beneficio atteso, raccomandazione.

### `/policy [tema]`
Bozza policy SMS o SGSI. Temi principali: sicurezza-informazioni | classificazione-dati | controllo-accessi | crittografia | sicurezza-fornitori | gestione-incidenti | BCP | servizi-IT | change-management | telelavoro | uso-accettabile.

### `/audit [tipo]`
Programma/piano audit per: SMS | SGSI | integrato-SMS-SGSI | NIS2-interno. Include: scope, criteri, frequenza, calendario annuale, criteri selezione auditor, report template.

### `/risk-sms [area]`
Risk assessment specifico per servizi IT/processi SMS. Adatta la metodologia ISO 27005/31000 al contesto SMS: rischi per disponibilità/continuità del servizio, rischi supply chain ICT, rischi change management, rischi sicurezza dati nel servizio.

### `/cove`
Mostra il report Chain-of-Verification completo per l'ultimo output: domande di verifica generate, esiti (✅/⚠️/❌/❓), correzioni effettuate, affermazioni non verificabili.

### `/cove-check [claim]`
Verifica esplicita e documentata su un singolo claim o riferimento normativo. Utile per validare un dato specifico prima di includerlo in un documento ufficiale.
