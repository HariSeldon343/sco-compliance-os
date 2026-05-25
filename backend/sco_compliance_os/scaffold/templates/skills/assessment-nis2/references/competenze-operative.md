# Competenze Operative — Dettaglio

## Indice
1. [Assessment di sicurezza](#1-assessment)
2. [Consulenza aziendale](#2-consulenza)
3. [Audit di prima, seconda e terza parte](#3-audit)
4. [Workflow operativi](#4-workflow)

---

## 1. Assessment di sicurezza

### 1.1 Gap Analysis NIS2

| Elemento | Descrizione |
|---|---|
| Riferimento primario | UNI/PdR 174:2024, Art. 21 Dir. (UE) 2022/2555, D.Lgs. 138/2024 |
| 13 aree Art. 21 | Tutte le aree dalla a) alla m) — vedi `norme-e-framework.md` |
| Metodologia | Analisi documentale, interviste, verifiche tecniche, campionamento |
| Output | Report assessment con rilievi classificati, piano trattamento, roadmap |

### 1.2 Gap Analysis ISO 27001:2022

- Clausole 4-10 (requisiti sistema di gestione)
- Annex A (93 controlli, 4 temi)
- SoA (Statement of Applicability)
- Integrazione con ISO 27002:2022 per guida implementazione

### 1.3 Assessment integrato multi-framework

Mappatura combinata: `NIS2 Art. 21 ←→ ISO 27001 Annex A ←→ NIST CSF 2.0 ←→ UNI/PdR 174:2024`

Produce matrici di correlazione che evitano duplicazione e massimizzano sinergie.

### 1.4 Assessment Legge 90/2024

- Obblighi notifica incidenti per PA e soggetti PSNC
- Strutture per la cybersicurezza (Art. 8)
- Referente per la cybersicurezza (Art. 13)
- Contratti pubblici beni e servizi informatici (Art. 14)
- Raccordo con NIS2 e D.Lgs. 138/2024

### 1.5 Risk Assessment

| Metodologia | Applicazione |
|---|---|
| **ISO 27005:2022** | Risk assessment sicurezza informazioni (asset-based o scenario-based) |
| **Reg. (UE) 2024/2690** | Rischi cyber per le 13 aree, scala RIDP |
| **ISO 31000:2018** | Framework generale gestione rischio |
| **BIA (ISO 22301)** | Business Impact Analysis — MTPD, RTO, RPO |
| **NIST CSF 2.0** | Profiling e scoring per funzione |

Per ogni valutazione dei rischi:
1. Utilizzare la metodologia e scala dell'organizzazione (da knowledge base)
2. Distinguere rischio inerente e rischio residuo
3. Applicare soglia di accettazione dell'organizzazione
4. Identificare risk owner per ogni rischio
5. Proporre opzioni trattamento (modifica, condivisione, evitamento, accettazione)
6. Generare piano trattamento con azioni, responsabili, scadenze, risorse

---

## 2. Consulenza aziendale

### 2.1 Strategia e governance cyber
- Strategia cybersicurezza aziendale
- Supporto organo di gestione per obblighi NIS2 (Art. 20)
- Formazione top management su responsabilità cyber
- Definizione ruoli: CISO, DPO, Referente Cybersicurezza (L. 90/2024), Punto di Contatto NIS2

### 2.2 Adeguamento normativo
- Roadmap conformità NIS2 con milestone e deliverable
- Piano adeguamento L. 90/2024
- Integrazione requisiti NIS2 con SGI esistenti (ISO 27001, 9001, 22301)
- Registrazione e comunicazione ACN

### 2.3 Infrastrutture critiche
Per dettagli settoriali → `references/infrastrutture-critiche.md`

### 2.4 Gestione incidenti
- Processo gestione incidenti significativi
- Workflow notifica CSIRT Italia (preallarme 24h, notifica 72h, relazione intermedia, relazione finale 1 mese)
- Coordinamento con autorità (ACN, CSIRT, autorità settoriali)
- Esercitazioni e test risposta incidenti

### 2.5 Continuità operativa
- BIA e definizione MTPD/RTO/RPO
- Strategie e piani continuità operativa
- Piano disaster recovery
- Programma esercitazioni

### 2.6 Approccio consulenziale

```
ANALISI CONTESTO → GAP ANALYSIS → PIANO TRATTAMENTO →
IMPLEMENTAZIONE DOCUMENTALE → SUPPORTO OPERATIVO → MONITORAGGIO
```

Per ogni intervento: analisi contesto → gap → priorità risk-based → documentazione → supporto implementazione → KPI monitoraggio.

---

## 3. Audit di prima, seconda e terza parte

### 3.1 Tipologie

| Tipo | Scopo | Ruolo agente |
|---|---|---|
| Prima parte | Audit interno — verifica proprio SGI | Pianificazione, checklist, conduzione, report |
| Seconda parte | Audit su fornitori/partner | Valutazione supply chain, qualifica fornitori |
| Terza parte | Certificazione/sorveglianza | Preparazione, simulazione, supporto tecnico |

### 3.2 Programma audit annuale

Considerare: risk-based approach (processi ad alto rischio, NC precedenti, cambiamenti significativi), copertura completa nel ciclo (triennale controlli, annuale clausole chiave), integrazione tra schemi, indipendenza auditor.

```
ID Audit | Processi/Clausole | Schemi coperti | Auditor | Auditee |
Data | Durata | Priorità (risk-based) | Note
```

### 3.3 Piano audit singolo
1. Obiettivo e campo di applicazione
2. Criteri di audit (clausole, procedure, controlli)
3. Metodologia (interviste, osservazioni, campionamento, test tecnici)
4. Programma temporale dettagliato
5. Checklist con domande/verifiche per clausola

### 3.4 Checklist audit

```
Clausola/Controllo | Requisito | Domanda/Verifica | Evidenza attesa |
Risultato (C/NC/Oss/NA) | Note
```

Specifiche per schema quando univoco, integrate quando condiviso (HLS), operative con evidenze concrete.

### 3.5 Report audit
1. Informazioni generali (team, date, scope, criteri)
2. Sommario esecutivo con conclusione
3. Risultanze: conformità, NC maggiori/minori, osservazioni, punti forza
4. Dettaglio NC: descrizione, evidenza, clausola, analisi cause
5. Raccomandazioni
6. Piano azioni correttive

### 3.6 Regole audit
- Indipendenza: l'auditor non audita i propri processi
- Evidenze oggettive: ogni risultanza supportata da evidenze
- Tracciabilità: ogni rilievo collegato a clausola/controllo
- Piano AC: azione correttiva per ogni NC con analisi cause radice

---

## 4. Workflow operativi

### 4.1 Prima interazione
```
1. Leggi TUTTA la knowledge base
2. Identifica schemi attivi e contesto organizzativo
3. Cataloga template, modelli, procedure disponibili
4. Acquisisci: organizzazione, settore, classificazione NIS2,
   responsabili, scope, piattaforme
5. Conferma comprensione contesto
```

### 4.2 Richiesta documentale
```
RICHIESTA → CONSULTA KB → Template trovato? →
  Sì → Usa come base, preserva layout, modifica contenuto
  No → Segnala, proponi generazione coerente
→ GENERA/MODIFICA → VERIFICA (CoVe) → CONSEGNA
```

### 4.3 Assessment
```
RICHIESTA → KB COMPLETA → IDENTIFICA (soggetto, settore, framework, SGI, docs)
→ PER OGNI CONTROLLO: evidenze KB → requisiti normativi → maturità → rilievo → note
→ GENERA: report + matrice rilievi + piano trattamento + roadmap
```

### 4.4 Pianificazione audit
```
RICHIESTA → ANALIZZA (schemi, audit precedenti, registro rischi, NC, cambiamenti)
→ PROGRAMMA ANNUALE (combinato, copertura, risk-based)
→ PER OGNI AUDIT: piano + checklist + template report
```
