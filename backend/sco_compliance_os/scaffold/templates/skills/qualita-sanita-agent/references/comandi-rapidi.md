# Comandi Rapidi — QualitàSanità-Agent

Guida completa ai comandi rapidi. Ogni comando attiva un flusso specifico con metodo operativo e Chain-of-Verification integrato.

## Indice

1. [Comandi di audit](#1-comandi-di-audit)
2. [Comandi di assessment e gap analysis](#2-comandi-assessment)
3. [Comandi di redazione documentale](#3-comandi-documentali)
4. [Comandi per processi sanitari](#4-comandi-processi)
5. [Comandi di risk management](#5-comandi-risk)
6. [Comandi CoVe](#6-comandi-cove)

---

## 1. Comandi di audit

### `/rve [clausola]`
**Funzione**: Bozza di valutazione RVE con declinazione sanitaria.

**Input**: Clausola ISO 9001:2015 (es. `cl. 8.5.1`, `cl. 9.2`, `cl. 7.2`)

**Output**: Documento .docx con valutazione completa: riferimento normativo, valutazione dettagliata nel contesto sanitario (MAI solo "conforme"), evidenze a supporto, esito, tag CoVe.

**Esempi**:
```
/rve cl. 8.5.1    → Controllo erogazione servizi (es. blocco operatorio)
/rve cl. 9.2      → Audit interni (sistema + clinici)
/rve cl. 7.2      → Competenza personale sanitario + ECM
/rve cl. 10.2     → NC e azioni correttive (con RCA)
```

### `/pdv [fase] [giorni]`
**Funzione**: Bozza Piano di Valutazione per struttura sanitaria.

**Input**: Fase (`ST1`/`ST2`/`SOR`/`RIN`) + giorni/uomo

**Output**: .docx con agenda dettagliata per reparti/servizi, clausole ISO + requisiti cogenti, auditor, auditee.

**Esempi**:
```
/pdv ST2 5    → PDV Stage 2, 5 giorni, ospedale
/pdv SOR 2    → PDV Sorveglianza, 2 giorni, poliambulatorio
```

### `/nc [descrizione]`
**Funzione**: Formula un rilievo di Non Conformità strutturato per contesto sanitario.

**Input**: Descrizione del fatto riscontrato

**Output**: .docx con: riferimento normativo (clausola ISO + legge se applicabile), fatto, requisito, gap, impatto su sicurezza paziente, classificazione (Maggiore/Minore).

**Esempi**:
```
/nc Audit interni non effettuati nell'ultimo anno
/nc Checklist di sala operatoria non compilata in 3 cartelle su 10
/nc Personale infermieristico senza crediti ECM per il triennio in corso
/nc Farmaci in frigorifero senza registrazione temperatura giornaliera
```

### `/sm [descrizione]`
**Funzione**: Formula Spunto di Miglioramento.

**Input**: Descrizione area di miglioramento

**Output**: .docx con: riferimento normativo, osservazione, suggerimento, beneficio atteso.

**Esempi**:
```
/sm Introdurre audit clinici strutturati oltre agli audit di sistema
/sm Implementare handover strutturato SBAR per tutti i reparti
```

### `/checklist [processo]`
**Funzione**: Checklist di audit per processo sanitario.

**Input**: Processo o area (es. `blocco operatorio`, `farmacia`, `prevenzione ICA`, `cartella clinica`, `cl. 8`)

**Output**: .docx con: clausola ISO + requisito cogente, domanda/verifica specifica sanitaria, evidenza attesa, colonna esito.

**Esempi**:
```
/checklist blocco operatorio
/checklist gestione farmaci
/checklist prevenzione cadute
/checklist formazione ECM
/checklist cl. 8   → tutte le clausole operative
```

---

## 2. Comandi di assessment e gap analysis

### `/gap [accreditamento]`
**Funzione**: Gap analysis tra SGQ ISO 9001 e requisiti di accreditamento regionale.

**Input**: Regione o framework (es. `accreditamento Calabria`, `accreditamento Veneto`, `DM 70/2015`)

**Output**: .docx con: requisiti accreditamento, stato attuale (da evidenze o `[DA INSERIRE]`), gap, priorità, piano azione suggerito.

**Esempi**:
```
/gap accreditamento Calabria
/gap accreditamento Sicilia
/gap DM 70/2015
/gap requisiti autorizzativi DPR 14/1/1997
```

---

## 3. Comandi di redazione documentale

### `/procedura [tema]`
**Funzione**: Bozza procedura SGQ sanitario.

**Output**: .docx con: frontespizio, registro revisioni, scopo, riferimenti (ISO 9001 + cogenti), termini, matrice RACI, descrizione processo, criteri/KPI, registrazioni, allegati.

**Esempi**:
```
/procedura gestione non conformità
/procedura audit interni
/procedura gestione cartella clinica
/procedura gestione farmaci
/procedura gestione fornitori
/procedura incident reporting
/procedura dimissione protetta
```

### `/protocollo [tema]`
**Funzione**: Bozza protocollo clinico-organizzativo.

**Output**: .docx con: scopo, campo applicazione, riferimenti (linee guida evidence-based), definizioni, descrizione processo clinico, responsabilità, indicatori, allegati.

**Esempi**:
```
/protocollo prevenzione ICA
/protocollo gestione dolore
/protocollo profilassi antibiotica
/protocollo prevenzione cadute
/protocollo somministrazione farmaci
/protocollo gestione emergenza intraospedaliera
```

### `/istruzione [tema]`
**Funzione**: Bozza istruzione operativa.

**Output**: .docx con: scopo, riferimenti (procedura madre), prerequisiti, passi dettagliati, verifiche, troubleshooting, registrazioni.

**Esempi**:
```
/istruzione lavaggio chirurgico mani
/istruzione prelievo venoso
/istruzione gestione catetere venoso centrale
/istruzione compilazione scheda terapia
```

### `/politica`
**Funzione**: Bozza politica per la qualità della struttura sanitaria.

**Output**: .docx con: dichiarazione di intento, impegni (sicurezza paziente, miglioramento continuo, centralità persona, appropriatezza, formazione), coerenza con mission/vision, firma Direzione.

---

## 4. Comandi per processi sanitari

### `/mappa-processi`
**Funzione**: Mappa completa dei processi sanitari per la struttura.

**Output**: .docx con: processi primari, di supporto e gestionali, interazioni, owner, indicatori per processo. Adattata alla tipologia di struttura.

### `/indicatori [area]`
**Funzione**: Set di indicatori/KPI per area sanitaria.

**Input**: Area (es. `chirurgia`, `degenza`, `pronto soccorso`, `laboratorio`, `customer satisfaction`, `rischio clinico`)

**Output**: .docx con: indicatore, definizione operativa, fonte dati, frequenza rilevazione, target/soglia, responsabile, benchmark (PNE se disponibile).

**Esempi**:
```
/indicatori chirurgia
/indicatori prevenzione ICA
/indicatori customer satisfaction
/indicatori pronto soccorso
/indicatori laboratorio
```

### `/riesame`
**Funzione**: Struttura del riesame di direzione con input/output specifici sanitari.

**Output**: .docx con: agenda, input obbligatori (cl. 9.3.2) declinati per la sanità (PNE, eventi avversi, accreditamento, ECM), output (cl. 9.3.3), template verbale.

---

## 5. Comandi di risk management

### `/risk [processo]`
**Funzione**: Analisi dei rischi per processo sanitario.

**Input**: Processo (es. `somministrazione farmaci`, `chirurgia`, `trasfusione`, `sterilizzazione`)

**Output**: .docx con: metodologia (FMEA/matrice rischio), identificazione pericoli, cause, effetti, probabilità, gravità, indice di rischio, azioni di mitigazione, owner, scadenza.

**Esempi**:
```
/risk somministrazione farmaci
/risk blocco operatorio
/risk gestione sangue
/risk gestione dispositivi medici
/risk ICT sistemi informativi sanitari
```

### `/audit-clinico [tema]`
**Funzione**: Struttura un audit clinico completo.

**Input**: Tema clinico

**Output**: .docx con: obiettivo, standard di riferimento (linea guida/protocollo), criteri misurabili, popolazione/campionamento, raccolta dati, analisi, template risultati, piano miglioramento, re-audit.

**Esempi**:
```
/audit-clinico profilassi antibiotica
/audit-clinico compliance PDTA ictus
/audit-clinico appropriatezza trasfusionale
/audit-clinico gestione dolore post-operatorio
```

### `/linee-guida [tema/processo]`
**Funzione**: Cerca e sintetizza le linee guida nazionali pertinenti a un tema clinico-organizzativo.

**Input**: Tema clinico, processo sanitario, patologia, procedura assistenziale

**Output**: Report sintetico con: linee guida SNLG vigenti, raccomandazioni delle società scientifiche accreditate ISS, raccomandazioni ministeriali per la sicurezza, buone pratiche AGENAS pertinenti. Per ogni LG trovata: titolo, fonte, anno, stato (vigente/in aggiornamento/ritirata), principali raccomandazioni rilevanti per il contesto SGQ.

**Sequenza di ricerca**:
1. Portale SNLG (snlg.iss.it) per LG pubblicate
2. Società scientifiche accreditate di riferimento per l'ambito
3. Raccomandazioni ministeriali per la sicurezza (n. 1-19)
4. Buone pratiche AGENAS / linee di indirizzo ministeriali

**Esempi**:
```
/linee-guida gestione farmaci
/linee-guida ICA infezioni correlate assistenza
/linee-guida profilassi TEV
/linee-guida sicurezza blocco operatorio
/linee-guida PDTA ictus ischemico
/linee-guida gestione dolore
```

---

## 6. Comandi CoVe (Chain-of-Verification)

### `/cove`
**Funzione**: Espone il report CoVe completo (tutte e 4 le fasi) per l'ultima risposta generata.

**Output**: Report strutturato con: sintesi bozza iniziale → domande di verifica → risultati verifica indipendente → sintesi (claim verificati/corretti/eliminati/non verificabili + indice di confidenza).

### `/cove-check [claim]`
**Funzione**: Verifica CoVe esplicita su un singolo claim o affermazione.

**Input**: Il claim da verificare (es. `"La cl. 7.2 della ISO 9001 richiede la formazione ECM"`)

**Output**: Domanda di verifica → verifica indipendente → esito ✅/⚠️/❌/❓ con motivazione.

### `/cove-report`
**Funzione**: Report sintetico di verifica per l'ultima risposta.

**Output**: Lista di tutti i claim principali con esito ✅/⚠️/❌/❓ in formato tabellare.

---

## Note operative per tutti i comandi

1. **Contesto**: se l'utente non ha fornito il contesto (tipo struttura, regione, servizi, dimensioni), chiedi prima di procedere
2. **Knowledge base**: se disponibili documenti caricati, analizzali prima dell'output
3. **CoVe**: applicato internamente a ogni comando — l'utente riceve solo l'output verificato; può richiedere trasparenza con `/cove`
4. **Formato**: tutti gli output sono .docx con formattazione professionale
5. **Segnaposti**: `[DA INSERIRE — ...]` per dati specifici dell'organizzazione; `[DA VERIFICARE — ...]` per claim non verificabili dal CoVe
6. **Combinazione**: i comandi accettano contesto aggiuntivo (es. `/checklist blocco operatorio per casa di cura privata accreditata in Calabria`)
7. **Declinazione sanitaria**: ogni output include sempre il raccordo con normativa cogente sanitaria, non solo ISO 9001
