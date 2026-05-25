# Framework Normativo di Riferimento

## Indice
1. [NIS2 — Dir. (UE) 2022/2555 e D.Lgs. 138/2024](#1-nis2)
2. [Legge 90/2024](#2-legge-90)
3. [Reg. di Esecuzione (UE) 2024/2690](#3-regolamento-esecuzione)
4. [UNI/PdR 174:2024](#4-pdr-174)
5. [ISO/IEC 27001:2022](#5-iso-27001)
6. [ISO 22301:2019](#6-iso-22301)
7. [NIST CSF 2.0](#7-nist-csf)
8. [Matrice integrazione NIS2/27001/NIST/PdR174](#8-matrice)
9. [Classificazione soggetti NIS2](#9-classificazione)

---

## 1. NIS2 — Dir. (UE) 2022/2555 e D.Lgs. 138/2024

### Articoli chiave

| Articolo | Contenuto | Rilevanza |
|---|---|---|
| **Art. 20** | Governance — responsabilità organo di gestione, formazione, supervisione | Critica |
| **Art. 21** | 13 aree misure gestione rischi cibersicurezza | Critica |
| **Art. 23** | Obblighi segnalazione incidenti significativi | Critica |
| **Art. 24** | Schemi europei certificazione cibersicurezza | Alta |
| **Art. 32** | Vigilanza ed esecuzione soggetti essenziali | Alta |
| **Art. 33** | Vigilanza ed esecuzione soggetti importanti | Alta |

### Le 13 aree dell'Art. 21

| # | Area | Descrizione |
|---|------|-------------|
| a | Politiche analisi rischi | Politiche di analisi dei rischi e sicurezza dei sistemi informativi |
| b | Gestione incidenti | Gestione degli incidenti di sicurezza informatica |
| c | Continuità operativa | Continuità operativa, gestione crisi, backup, disaster recovery |
| d | Sicurezza supply chain | Sicurezza della catena di approvvigionamento |
| e | Acquisizione/sviluppo/manutenzione | Sicurezza nell'acquisizione, sviluppo e manutenzione sistemi |
| f | Valutazione efficacia | Politiche e procedure per valutare efficacia delle misure |
| g | Igiene informatica e formazione | Pratiche di igiene informatica di base e formazione cybersecurity |
| h | Crittografia | Politiche e procedure sull'uso della crittografia |
| i | Risorse umane e controllo accessi | Sicurezza HR, controllo accessi, gestione attivi |
| j | MFA | Uso di soluzioni autenticazione a più fattori |
| k | Comunicazioni protette | Comunicazioni vocali, video e testuali protette |
| l | Comunicazioni emergenza | Sistemi di comunicazione di emergenza protetti |
| m | Gestione vulnerabilità | Gestione delle vulnerabilità tecniche |

### Notifica incidenti significativi (Art. 23)

| Fase | Tempistica | Contenuto |
|------|-----------|-----------|
| Preallarme | 24h dal rilevamento | Natura dell'incidente, sospetto causa dolosa, impatto transfrontaliero |
| Notifica | 72h dal rilevamento | Aggiornamento preallarme, valutazione iniziale gravità e impatto, IoC |
| Relazione intermedia | Su richiesta CSIRT | Aggiornamenti rilevanti |
| Relazione finale | 1 mese dalla notifica | Descrizione dettagliata, causa, misure mitigazione, impatto transfrontaliero |

---

## 2. Legge 90/2024

| Articolo | Contenuto |
|---|---|
| **Art. 1** | Obblighi segnalazione e notifica CSIRT per PA e soggetti PSNC |
| **Art. 8** | Strutture per la cybersicurezza — requisiti organizzativi |
| **Art. 10** | Rafforzamento ACN |
| **Art. 13** | Referente per la cybersicurezza — obbligo nomina e competenze |
| **Art. 14** | Contratti pubblici beni e servizi informatici — requisiti cybersicurezza |
| **Art. 16-22** | Modifiche codice penale reati informatici — inasprimento sanzioni |

---

## 3. Reg. di Esecuzione (UE) 2024/2690

Requisiti tecnici e metodologici per l'applicazione dell'Art. 21 NIS2. Utilizzarlo come riferimento per definizione misure proporzionate e adeguate. Integra e dettaglia ciascuna delle 13 aree con requisiti operativi specifici.

---

## 4. UNI/PdR 174:2024

Prassi di Riferimento per valutazione conformità NIS2. Framework strutturato per:
- Assessment di conformità con scoring
- Classificazione rilievi
- Definizione priorità intervento
- Correlazione con ISO 27001 e NIST CSF 2.0

---

## 5. ISO/IEC 27001:2022

### Struttura

- **Clausole 4-10**: requisiti sistema di gestione (HLS)
- **Annex A**: 93 controlli in 4 temi
  - A.5 Organizational: 37 controlli
  - A.6 People: 8 controlli
  - A.7 Physical: 14 controlli
  - A.8 Technological: 34 controlli
- **Amendment 1:2024**: cambiamento climatico (cl. 4.1, 4.2)

### Norme correlate

| Norma | Ruolo |
|-------|-------|
| ISO/IEC 27002:2022 | Guida implementazione controlli con attributi |
| ISO/IEC 27005:2022 | Gestione rischio sicurezza informazioni |
| ISO 31000:2018 | Framework generale gestione rischio |
| ISO/IEC 27017:2015 | Controlli cloud |
| ISO/IEC 27018:2019 | PII in cloud |
| ISO/IEC 27799:2016 | Sicurezza informazioni in sanità |

---

## 6. ISO 22301:2019

Sistema di Gestione per la Continuità Operativa. Concetti chiave:
- **MTPD** (Maximum Tolerable Period of Disruption)
- **RTO** (Recovery Time Objective)
- **RPO** (Recovery Point Objective)
- **BIA** (Business Impact Analysis)
- Strategie di continuità, piani BCP/DRP, esercitazioni

---

## 7. NIST CSF 2.0

6 funzioni: **Govern** (GV), **Identify** (ID), **Protect** (PR), **Detect** (DE), **Respond** (RS), **Recover** (RC).

Ogni funzione si articola in categorie e subcategorie con profiling e scoring.

---

## 8. Matrice integrazione NIS2 / ISO 27001 / NIST CSF 2.0 / PdR 174

| Area NIS2 (Art. 21) | ISO 27001 Annex A | NIST CSF 2.0 | UNI/PdR 174 |
|---|---|---|---|
| a) Politiche analisi rischi | A.5.1, §6.1.2, §8.2-8.3 | GV.RM, ID.RA | GV.RM |
| b) Gestione incidenti | A.5.24-5.28 | RS.MA, RS.AN, RS.MI | RS.MA |
| c) Continuità operativa | A.5.29-5.30, ISO 22301 | RC.RP, PR.IR | PR.IR |
| d) Sicurezza supply chain | A.5.19-5.23 | GV.SC, ID.AM | GV.SC |
| e) Acquisizione/sviluppo/manutenzione | A.8.25-8.31 | PR.DS, PR.PS | PR.DS |
| f) Valutazione efficacia | §9.1, §9.2, §9.3 | ID.IM, GV.OV | ID.IM |
| g) Igiene informatica e formazione | A.6.3, §7.2-7.3 | PR.AT | PR.AT |
| h) Crittografia | A.8.24 | PR.DS | PR.DS |
| i) Risorse umane e controllo accessi | A.5.15-5.18, A.6.1-6.8 | PR.AA, PR.AT | PR.AA |
| j) MFA | A.8.5 | PR.AA | PR.AA |
| k) Comunicazioni protette | A.5.14, A.8.20-8.24 | PR.DS | PR.DS |
| l) Comunicazioni emergenza | A.5.30, ISO 22301 | RC.CO | RC.CO |
| m) Gestione vulnerabilità | A.8.8, A.8.9 | ID.RA, PR.PS | ID.RA |

---

## 9. Classificazione soggetti NIS2

**Soggetti essenziali**: energia, trasporti, banche, infrastrutture mercati finanziari, sanità, acqua potabile, acque reflue, infrastrutture digitali, gestione servizi TIC, PA centrale, spazio.

**Soggetti importanti**: servizi postali, gestione rifiuti, fabbricazione (chimici, dispositivi medici, elettronica, macchinari, autoveicoli), produzione/distribuzione alimenti, fornitori digitali, ricerca.

**Sanzioni**:
- Soggetti essenziali: fino a €10M o 2% fatturato mondiale
- Soggetti importanti: fino a €7M o 1,4% fatturato mondiale
