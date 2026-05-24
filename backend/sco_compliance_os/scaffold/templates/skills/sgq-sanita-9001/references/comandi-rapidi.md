# Comandi Rapidi — SGQ-Sanità-9001

Guida completa ai comandi rapidi. Ogni comando attiva un flusso specifico con Chain-of-Verification integrato.

---

## 1. Comandi di redazione documentale

### `/procedura [tema]`
**Funzione**: Bozza di procedura gestionale o operativa SGQ.

**Input**: Tema o processo (es. gestione NC, audit interni, approvvigionamento, gestione farmaci)

**Output**: .docx con: codifica (PG/PO-AREA-NNN), scopo, campo di applicazione, riferimenti normativi, definizioni, responsabilità (matrice RACI), descrizione attività (diagramma di flusso + narrativa), indicatori, documenti collegati, allegati/moduli, storico revisioni.

**Esempi**:
```
/procedura gestione non conformità e azioni correttive
/procedura audit interni
/procedura gestione informazioni documentate
/procedura approvvigionamento e valutazione fornitori
/procedura gestione farmaci
/procedura sterilizzazione
/procedura gestione reclami e customer satisfaction
```

### `/protocollo [tema]`
**Funzione**: Bozza protocollo clinico-organizzativo.

**Input**: Tema clinico o organizzativo

**Output**: .docx con: codifica (PR-AREA-NNN), obiettivo, campo applicazione, riferimenti normativi e linee guida (SNLG cercate attivamente), definizioni, responsabilità, descrizione sequenza azioni, criteri/standard, indicatori di monitoraggio, documenti collegati.

**Esempi**:
```
/protocollo profilassi antibiotica peri-operatoria
/protocollo prevenzione cadute paziente
/protocollo gestione emergenza intraospedaliera
/protocollo prevenzione ICA
/protocollo gestione sangue e emoderivati
/protocollo identificazione paziente
```

### `/istruzione [tema]`
**Funzione**: Bozza istruzione operativa.

**Input**: Attività operativa specifica

**Output**: .docx con: codifica (IO-AREA-NNN), scopo, responsabilità, materiali/attrezzature, sequenza passi operativi dettagliati, punti di attenzione/sicurezza, registrazioni.

**Esempi**:
```
/istruzione preparazione campo operatorio
/istruzione prelievo venoso
/istruzione sanificazione superfici
/istruzione gestione catena del freddo farmaci
/istruzione compilazione cartella clinica
```

### `/politica`
**Funzione**: Bozza politica per la qualità.

**Input**: Tipo struttura, mission, valori (se noti)

**Output**: .docx con: dichiarazione dell'alta direzione, impegni (sicurezza paziente, appropriatezza, EBM, ECM, miglioramento continuo, risk management, centralità persona), firma Direzione, data.

### `/manuale [struttura]`
**Funzione**: Struttura manuale qualità per tipo struttura.

**Input**: Tipo struttura sanitaria

**Output**: .docx con: indice completo del manuale articolato sulle clausole 4-10, presentazione organizzazione, scope SGQ, esclusioni giustificate, mappa processi, riferimenti a procedure, politica.

### `/carta-servizi [struttura]`
**Funzione**: Struttura carta dei servizi.

**Input**: Tipo struttura, servizi principali

**Output**: .docx con: presentazione struttura, mission e valori, servizi offerti (per UO/area), modalità di accesso, impegni verso il paziente (standard qualità), diritti e doveri, gestione reclami, informazioni pratiche.

---

## 2. Comandi di mappatura e indicatori

### `/mappa-processi`
**Funzione**: Mappa processi sanitari con interazioni.

**Input**: Tipo struttura, specialità/servizi

**Output**: Mappa strutturata con: processi primari (clinico-assistenziali), di supporto, gestionali. Per ogni processo: input, output, responsabile, interazioni con altri processi, clausole ISO 9001 di riferimento. Formato tabellare + rappresentazione grafica.

### `/indicatori [area]`
**Funzione**: Set di indicatori/KPI per area.

**Input**: Area clinica o organizzativa (es. blocco operatorio, medicina interna, emergenza, laboratorio, farmacia, SGQ complessivo)

**Output**: Tabella con: nome indicatore, formula di calcolo, fonte dati, frequenza rilevazione, target/soglia, benchmark (PNE se disponibile), responsabile monitoraggio, clausola ISO 9001 di riferimento.

**Esempi**:
```
/indicatori blocco operatorio
/indicatori customer satisfaction
/indicatori ICA
/indicatori SGQ complessivo
/indicatori laboratorio analisi
/indicatori farmacia
```

### `/riesame`
**Funzione**: Struttura riesame di direzione sanitario.

**Output**: .docx con: template completo per verbale riesame conforme a cl. 9.3 — input (stato azioni precedenti, cambiamenti contesto, indicatori qualità, soddisfazione paziente, NC/AC, audit, fornitori, rischi, risorse), output (decisioni miglioramento, modifiche SGQ, risorse), formato tabellare per dati, sezione deliberazioni.

---

## 3. Comandi di analisi

### `/risk [processo]`
**Funzione**: Analisi rischi processo sanitario.

**Input**: Processo o attività sanitaria

**Output**: Registro rischi con: descrizione rischio, causa, effetto su sicurezza paziente/continuità assistenziale, probabilità, impatto, livello rischio, azioni di trattamento, responsabile, indicatore monitoraggio. Metodologia FMEA se processo operativo, matrice probabilità-impatto se processo gestionale.

**Esempi**:
```
/risk somministrazione farmaci
/risk blocco operatorio
/risk gestione sangue e emoderivati
/risk gestione dispositivi medici
/risk percorso emergenza-urgenza
```

### `/gap [regione]`
**Funzione**: Gap analysis SGQ vs. accreditamento regionale.

**Input**: Regione (obbligatoria)

**Output**: Matrice di correlazione requisiti accreditamento regionale ↔ clausole ISO 9001 ↔ stato attuale. Per ogni gap: descrizione, priorità, azioni proposte. Nota: i requisiti regionali vengono cercati tramite web search e verificati con CoVe.

### `/pdta [patologia/percorso]`
**Funzione**: Struttura PDTA con riferimenti linee guida.

**Input**: Patologia o percorso clinico

**Output**: .docx con: scopo e popolazione target, riferimenti LG (SNLG cercate attivamente), fasi del percorso (accesso, valutazione, trattamento, follow-up), responsabilità per fase, indicatori di processo e di esito, criteri di inclusione/esclusione, diagramma di flusso.

**Esempi**:
```
/pdta ictus ischemico acuto
/pdta scompenso cardiaco
/pdta frattura femore anziano
/pdta sepsi
/pdta diabete tipo 2
/pdta BPCO riacutizzata
```

---

## 4. Comandi di formazione

### `/formazione [tema]`
**Funzione**: Piano formativo o materiale didattico su temi qualità.

**Input**: Tema formativo, destinatari (se specificati)

**Output**: A seconda della richiesta — Piano formativo annuale .docx (obiettivi, temi, destinatari, ore, crediti ECM, calendario, docenti, verifica apprendimento) OPPURE Materiale didattico (slide deck struttura, contenuti per modulo, esercitazioni, casi studio, test verifica).

**Esempi**:
```
/formazione approccio per processi e PDCA per coordinatori
/formazione risk management clinico per personale sanitario
/formazione gestione NC e incident reporting
/formazione ISO 9001 base per nuovo personale
/formazione audit interni per auditor qualificandi
/formazione gestione informazioni documentate
```

---

## 5. Comandi linee guida

### `/linee-guida [tema]`
**Funzione**: Cerca e sintetizza linee guida nazionali pertinenti.

**Input**: Tema clinico, processo, patologia, procedura assistenziale

**Output**: Report con: LG SNLG vigenti, raccomandazioni società scientifiche accreditate, raccomandazioni ministeriali sicurezza, buone pratiche AGENAS. Per ogni LG: titolo, fonte, anno, stato, principali raccomandazioni rilevanti per il SGQ.

**Sequenza di ricerca**:
1. Portale SNLG (snlg.iss.it)
2. Società scientifiche accreditate di riferimento
3. Raccomandazioni ministeriali (n. 1-19)
4. Buone pratiche AGENAS / linee indirizzo ministeriali

**Esempi**:
```
/linee-guida gestione farmaci
/linee-guida ICA infezioni correlate assistenza
/linee-guida profilassi TEV
/linee-guida sicurezza blocco operatorio
/linee-guida gestione dolore
/linee-guida antimicrobico-resistenza
```

---

## 6. Comandi CoVe

### `/cove`
**Funzione**: Report CoVe completo (4 fasi) per l'ultima risposta.

**Output**: Report strutturato: sintesi bozza → domande verifica → risultati verifica indipendente → sintesi (claim verificati/corretti/eliminati/non verificabili + indice di confidenza).

### `/cove-check [claim]`
**Funzione**: Verifica CoVe esplicita su un singolo claim.

**Input**: Affermazione da verificare

**Output**: Domanda di verifica → ricerca indipendente → esito (V/I/E/NV) con motivazione.

### `/cove-report`
**Funzione**: Report sintetico verifica.

**Output**: Lista claim dell'ultima risposta con esito V/I/E/NV, conteggio, indice di confidenza.
