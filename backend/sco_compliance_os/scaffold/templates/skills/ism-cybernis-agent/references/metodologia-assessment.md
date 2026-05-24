# Metodologia di Assessment e Classificazione Rilievi

## Formato obbligatorio — Assessment processo/controllo

```
Processo/Controllo [RIFERIMENTO PRECISO]: [Descrizione breve]
Incidenza: [Alta / Medio-alta / Media / Bassa / Non applicabile]
Qualità: [Iniziale/Ad-hoc | Ripetibile/Gestito | Definito/Standardizzato |
          Quantitativamente Gestito | Ottimizzato]

[TIPO RILIEVO — scegliere uno]:
[Max 3–4 righe strutturate:
  → Stato attuale (cosa esiste/non esiste)
  → Requisito (cosa richiede la norma)
  → Confronto (delta tra stato e requisito)
  → Gap evidenziato (impatto della carenza)]

Note:
[Min 8–10 righe:
  - Contesto narrativo (perché questo processo è critico per l'organizzazione)
  - Evidenze documentali (documento, rev., data, paragrafo/sezione specifica)
  - Evidenze da intervista o osservazione diretta
  - Considerazioni su integrazione 20000-1/27001/NIS2
  - Interdipendenze con altri processi o controlli
  - Eventuale impatto cloud, supply chain, compliance normativa
  - Azioni suggerite (solo se richieste)]
```

---

## Classificazione rilievi

### Per audit di terza parte (CSQA)

| Classificazione | Criteri | Note operative |
|----------------|---------|----------------|
| **NC Maggiore/Essenziale** | Mancata implementazione requisito; fallimento sistematico; assenza controllo critico che compromette efficacia SGSI/SMS | Blocca certificazione. Richiede azione correttiva e verifica follow-up |
| **NC Minore/Marginale** | Deviazione parziale; carenza documentazione o implementazione isolata; non compromette efficacia complessiva | Richiede azione correttiva entro periodo sorveglianza |
| **SM (Spunto di Miglioramento)** | Opportunità di miglioramento senza violazione; requisito soddisfatto ma ottimizzabile | Non blocca. Raccomandata azione proattiva |
| **Punto di forza** | Eccellenza operativa; best practice consolidata da valorizzare | Da citare nel report come elemento positivo |

**Regola CSQA**: ogni NC deve fare riferimento a UN SOLO punto della norma. Valutare sempre: estensione, sistematicità, criticità, influenza sull'efficacia del sistema.

### Per assessment (consulenza / gap analysis)

| Classificazione | Definizione |
|----------------|-------------|
| **Non conformità** | Requisito non soddisfatto; gap materiale rispetto allo standard |
| **Osservazione** | Requisito parzialmente soddisfatto; area di rischio potenziale |
| **OdM (Opportunità di Miglioramento)** | Requisito soddisfatto ma con margini di ottimizzazione |

---

## Prioritizzazione azioni

| Priorità | Criteri | Scadenza indicativa |
|----------|---------|---------------------|
| **CRITICA** | NC maggiori; rischi sopra soglia accettabile; non conformità normative cogenti (NIS2, GDPR, L.90) | 30 giorni |
| **ALTA** | NC minori; gap rilevanti in assessment; obblighi imminenti; impatto SLA significativo | 90 giorni |
| **MEDIA** | Osservazioni; miglioramenti con impatto significativo su KPI o maturità | 180 giorni |
| **BASSA** | Enhancement, ottimizzazioni, best practice da implementare | 12 mesi |

---

## Struttura action plan (per ogni rilievo)

```
ID: [es. GAP-SMS-001 | NC-27001-014 | OBS-NIS2-007]
Riferimento normativo: [ISO 20000-1:2018 §X.X | ISO 27001 cl./A.X.X | Art. X NIS2]
Tipo: [NC Maggiore / NC Minore / Osservazione / OdM]
Descrizione gap: [breve descrizione del requisito non soddisfatto]
Azione correttiva: [cosa fare]
Owner: [ruolo/funzione responsabile]
Priorità: [Critica / Alta / Media / Bassa]
Scadenza: [data]
Dipendenze: [altri gap o azioni correlate]
Stato: [Aperta / In corso / Chiusa / Verificata]
```

---

## Metodo RCA (Root Cause Analysis) — Problem Management

### 5-Why
Iterazione di 5 domande "Perché?" a partire dal sintomo osservato. Efficace per problemi con catena causale lineare.

### Ishikawa (Fishbone / Cause-Effect Diagram)
Categorie: Persone, Processi, Tecnologia, Ambiente, Dati, Management. Efficace per problemi multi-causali.

### Fault Tree Analysis (FTA)
Approccio top-down: evento indesiderato → condizioni necessarie/sufficienti → cause radice. Efficace per sistemi complessi con dipendenze.

---

## Matrice RACI — Processi SMS/SGSI

| Processo | Responsabile (R) | Accountable (A) | Consultato (C) | Informato (I) |
|----------|-----------------|-----------------|----------------|---------------|
| Incident Management | Service Desk / IT Ops | Service Manager | Security Officer, Business Owner | Direzione (P1), Utenti |
| Problem Management | Problem Manager | Service Manager | IT Ops, Sviluppo | Service Desk, Direzione |
| Change Management | Change Manager | CAB Chair | IT Ops, Security, Business | Utenti, Direzione |
| Configuration Mgmt | Config Manager | IT Manager | IT Ops, Change Manager | Audit, Security |
| Service Continuity | BCP Manager | CIO | IT Ops, Business Owner | Direzione, Regolatori |
| Supplier Management | Procurement / IT | CIO | Legal, Security | Direzione, Auditor |
| Risk Assessment | Risk Owner | CISO / ISO27001 Owner | Process Owner | Direzione |

---

## Domande chiave per audit SMS (campionamento)

### Incident Management
- Mostrami il ticket di un P1 recente: come è stato classificato, chi è stato notificato, entro quanto è stato risolto?
- Dove è documentata la procedura Major Incident? È stata testata negli ultimi 12 mesi?
- Come avviene l'handoff verso Problem Management?
- Per i soggetti NIS2: è stata effettuata la notifica CSIRT entro 24h per incidenti significativi?

### Change Management
- Mostrami gli ultimi 5 RFC aperti/chiusi: classificazione, approvazione CAB, PIR.
- Esiste un freeze calendar? Chi lo approva?
- Come gestite un Emergency Change fuori orario?

### Configuration Management
- Il CMDB è aggiornato? Chi effettua la riconciliazione fisica vs CMDB e con quale frequenza?
- Mostrami la baseline configuration di [sistema critico].
- Come viene gestita la discovery automatica dei CI?

### Service Continuity
- Qual è il RTO/RPO contrattuale per il servizio X? È stato testato?
- Quando è stato effettuato l'ultimo test di continuità? Esiste il report?
- I fornitori critici hanno obblighi di continuità nel contratto (UC)?

### Supplier Management
- Mostrami gli SLA con i 3 fornitori principali. Come vengono misurati e reportati?
- Qual è la procedura in caso di SLA breach?
- Per NIS2: i fornitori ICT sono stati valutati per rischio supply chain?
