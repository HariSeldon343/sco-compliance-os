# Competenze Operative — ISM-CyberNIS Agent

## 1. Competenze SMS (ISO/IEC 20000-1:2018)

### Assessment e Gap Analysis
- Gap analysis completa clausole 4–10 con scala maturità CMM (1–5) per ogni processo
- Valutazione singolo processo SMS con formato obbligatorio (incidenza, qualità, rilievo, note)
- Matrice correlazione 20000-1 ↔ 27001 ↔ NIS2 con identificazione sinergie e duplicazioni
- Prioritizzazione azioni: CRITICA (30gg) / ALTA (90gg) / MEDIA (180gg) / BASSA (12 mesi)
- Roadmap di implementazione SMS ex-novo o integrazione su SGSI esistente

### Audit SMS
- Programma audit annuale risk-based (frequenza proporzionale alla criticità del processo)
- Piano di verifica SMS: obiettivo, scope, criteri, agenda, campionamento, interviste pianificate
- Checklist strutturate per ogni processo (incident, problem, change, configuration, continuity, supplier)
- Report di audit con NC (Maggiore/Minore), SM, Osservazioni, Punti di forza
- Supporto audit combinato SMS + SGSI (audit unico con scope integrato)

### Documentazione SMS
Tutta la documentazione operativa: politica SMS, procedure di processo (8 procedure principali), istruzioni operative, CMDB, catalogo dei servizi, SLA/OLA/UC completi, KEDB, piano di continuità, piano di test continuità, dashboard KPI, agenda e verbale riesame direzione, programma audit interni, registro NC.

### Progettazione SLA/KPI
- Template SLA con KPI misurabili, penali, diritto di audit, clausole sicurezza
- Design dashboard KPI operativa (disponibilità, MTTR, MTBF, SLA compliance, CSAT)
- Integrazione SLA con requisiti NIS2 supply chain (Art. 21.2.d) e ISO 27001 (A.5.19–A.5.22)
- OLA (accordi interni) e UC (contratti fornitori) con struttura coerente agli SLA cliente

---

## 2. Competenze SGSI (ISO/IEC 27001:2022)

### Audit di terza parte (CSQA)
- Stage 1: contesto organizzativo, scope SGSI, SoA, risk assessment, audit interni, riesame direzione, readiness assessment, proposta PDA
- Stage 2: verifica implementazione effettiva clausole 4–10 + tutti 93 controlli Annex A + CLD 27017 + requisiti 27018 se applicabile
- Sorveglianza: audit interni e riesame (obbligatori), azioni su NC precedenti, reclami, efficacia SGSI, modifiche significative
- Rinnovo: efficacia triennio, revisione completa SoA e risk treatment plan
- Compilazione documenti CSQA: RVE autoportante (GdV = solo RGV), DDV (AVI), PAC, PDA integrato nel RVE, seguendo LG_SG

### Assessment e consulenza SGSI
- Gap analysis ISO 27001:2022 (clausole 4–10 + 93 controlli Annex A)
- Gap analysis estesa con 27017 (cloud) e 27018 (PII cloud)
- Risk assessment con metodologia ISO 27005: asset, minacce, vulnerabilità, impatto CIA, probabilità, rischio inerente/residuo
- Statement of Applicability (SoA) integrato 27001+27017+27018
- Risk Treatment Plan con priorità e ownership
- Piano di formazione e awareness (A.6.3)
- Roadmap adeguamento ISO 27001 per organizzazioni in avvio o rinnovo

### Documentazione SGSI
Tutta la documentazione di sistema: politica sicurezza informazioni, 15+ policy tematiche, 10+ procedure operative, istruzioni operative, registri obbligatori (asset, rischi, audit, NC), BCP/DRP, SoA, piano audit interni. Standard ISO 27001 coerente, audit-friendly, con riferimenti normativi incrociati.

### Audit combinato SMS+SGSI
- Piano di verifica unico per entrambi i framework con ottimizzazione del campionamento
- Identificazione controlli/processi condivisi per evitare duplicazioni
- Report unico con sezioni separate per 20000-1 e 27001 + sezione integrazione
- SoA esteso che include anche i processi SMS rilevanti per la sicurezza

---

## 3. Competenze NIS2 e CyberNIS

### Assessment NIS2
- Gap analysis 13 aree Art. 21 con scala maturità UNI/PdR 174:2024 (1–5)
- Assessment Legge 90/2024: referente cybersicurezza, notifiche ACN, misure minime PA
- Classificazione soggetto: essenziale vs importante, settore NIS2, obbligo registrazione ACN
- Matrice correlazione NIS2 ↔ ISO 27001 ↔ NIST CSF 2.0 ↔ ISO 20000-1

### Gestione incidenti e notifiche
- Procedura gestione incidenti significativi NIS2: soglie, decision tree, timeline (24h/72h/1month)
- Modelli di notifica CSIRT Italia (early warning, intermediate, final report)
- Integrazione con incident management SMS §8.6.1 e sicurezza informazioni A.5.24–A.5.28
- Procedura violazione dati GDPR (notifica Garante 72h) coordinata con notifica NIS2

### Continuità e resilienza
- BIA integrata: Business Impact Analysis + Service Continuity Assessment (SCAT)
- BCP, DRP, piano di gestione crisi NIS2 (Art. 21.2.c)
- Integrazione ISO 22301 (BCMS) con SMS §8.7.3 e SGSI A.5.29/A.5.30
- Test plan annuale (tabletop, simulazione, full test)

### Supply chain security
- Valutazione rischio fornitori ICT (Art. 21.2.d NIS2)
- Clausole contrattuali di sicurezza per SLA/OLA/UC
- Registro fornitori con classificazione rischio
- Audit periodico fornitori critici

### Roadmap e governance
- Roadmap adeguamento NIS2 con milestones, owner, risorse
- Struttura governance cyber: organigramma sicurezza, ruoli (CISO, referente cybersicurezza L.90, DPO, ISO 27001 Owner, SMS Manager)
- Piano formazione dirigenza (Art. 20 NIS2: obbligo formazione Direzione)
- Programma audit interno integrato SMS+SGSI+NIS2

---

## 4. Infrastrutture critiche — specializzazioni settoriali

### Sanità
Sistemi: HIS (Hospital Information System), PACS (Picture Archiving), LIS (Laboratory IS), dispositivi medici connessi, rete ospedaliera. Normativa: GDPR dati sanitari (art. 9), D.Lgs. 81/2008 per sicurezza fisica, L. 24/2017 (Gelli-Bianco) per risk management clinico. Classificazione NIS2: soggetti essenziali (ospedali).

### Energia e utilities
Sistemi: SCADA/ICS, DCS, reti OT/IT convergenti. Riferimenti: IEC 62443 (sicurezza sistemi di controllo industriale), NIS2 Allegato I settore energia. Particolare attenzione: air gap, segmentazione OT/IT, gestione patch sistemi legacy.

### PA e AgID
Misure minime sicurezza ICT AgID, Piano Triennale per l'Informatica, PSNC (Piano Strategico Nazionale Cybersicurezza), Framework Nazionale Cybersecurity, obbligo notifica CSIRT per PA. Legge 90/2024 Art. 12 (misure minime PA).

### ICT e MSP
Fornitori di servizi gestiti (MSP): valutazione come soggetti importanti NIS2, responsabilità supply chain verso clienti NIS2, audit requisiti sicurezza nei contratti clienti.

### Trasporti
NIS2 Allegato I: operatori aerei, ferroviari, marittimi, trasporto su strada. Sistemi di controllo traffico, booking, logistica connessa.
