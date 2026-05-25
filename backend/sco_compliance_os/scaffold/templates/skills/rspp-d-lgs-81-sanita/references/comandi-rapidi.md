# Comandi Rapidi — RSPP-Sanità-81

---

## 1. Comandi documentali

### `/dvr [area/reparto]`
**Funzione**: Sezione DVR per area o reparto sanitario.
**Input**: Area/reparto (es. blocco operatorio, laboratorio, degenza medicina, PS)
**Output**: .docx con: descrizione attività e mansioni, identificazione pericoli, valutazione rischi (P×D), elenco rischi specifici con riferimenti normativi, misure di prevenzione in atto, misure programmate, DPI, sorveglianza sanitaria, formazione specifica. Indicazione interfacce con SGQ.
**Esempi**: `/dvr blocco operatorio`, `/dvr laboratorio analisi`, `/dvr sterilizzazione`, `/dvr PS`

### `/duvri [appalto]`
**Funzione**: DUVRI per appalto/servizio con interferenze.
**Input**: Tipo appalto (es. pulizie, manutenzione, ristorazione, service biomedicali)
**Output**: .docx conforme art. 26: dati committente/appaltatore, rischi specifici dell'ambiente, rischi introdotti dall'appaltatore, rischi interferenziali, misure di coordinamento, costi sicurezza (non soggetti a ribasso).
**Esempi**: `/duvri pulizia e sanificazione`, `/duvri manutenzione impianti`, `/duvri service apparecchiature biomedicali`

### `/rischio [tipo]`
**Funzione**: Valutazione rischio specifico per la struttura sanitaria.
**Input**: Tipo di rischio (biologico, chimico, MMC, stress, incendio, radiazioni, CEM, rumore, aggressioni, ecc.)
**Output**: .docx con: descrizione rischio nel contesto sanitario, riferimenti normativi (titolo D.Lgs. 81/08), aree/mansioni esposte, metodologia di valutazione, matrice P×D o algoritmo specifico, misure prevenzione (gerarchia art. 15), DPI, sorveglianza sanitaria, formazione, indicatori monitoraggio.
**Esempi**: `/rischio biologico`, `/rischio chimico farmacia`, `/rischio MMC pazienti`, `/rischio stress`, `/rischio gas anestetici`

### `/emergenza [struttura]`
**Funzione**: Piano di emergenza ed evacuazione.
**Input**: Tipo struttura, capacità (pl, personale)
**Output**: .docx con: organigramma emergenza, scenari (incendio, sisma, allagamento, bomb threat, black-out, fuga gas), procedure per scenario, gestione pazienti non deambulanti, punti raccolta, planimetrie (placeholder), ruoli e responsabilità, numeri emergenza, formazione addetti.

### `/formazione-sicurezza`
**Funzione**: Piano formativo sicurezza conforme Accordo SR 2025.
**Output**: .docx con: matrice figure/corsi/durate/scadenze (lavoratori rischio alto 16h, preposti 8h, dirigenti 12h, DL 16h, addetti antincendio L3 16h, addetti PS gr.A 16h, RLS 32h), calendario formazione, registro attestati, budget, soggetti formatori.

### `/dpi [area/mansione]`
**Funzione**: Selezione DPI per area o mansione.
**Input**: Area o mansione sanitaria
**Output**: Tabella DPI con: mansione, rischio, DPI, norma EN/UNI, marcatura CE, criteri selezione, sostituzione, formazione uso.
**Esempi**: `/dpi infermiere reparto`, `/dpi tecnico laboratorio`, `/dpi addetto sterilizzazione`, `/dpi operatore sala operatoria`

---

## 2. Comandi gestionali

### `/appalti [servizio]`
**Funzione**: Gestione sicurezza appalti e interferenze.
**Input**: Servizio in appalto
**Output**: .docx con: checklist verifica idoneità tecnico-professionale appaltatore (art. 26 c. 1), rischi specifici da comunicare, template DUVRI, costi sicurezza, coordinamento, riunioni di cooperazione. Interfaccia con procedura valutazione fornitori SGQ.

### `/sorveglianza [mansione]`
**Funzione**: Protocollo sorveglianza sanitaria per mansione.
**Input**: Mansione sanitaria
**Output**: Tabella con: rischi per mansione, accertamenti sanitari (tipo, periodicità), vaccinazioni, visite specialistiche, giudizi di idoneità (idoneo/idoneo con prescrizioni/non idoneo), monitoraggio biologico ove previsto. Nota: il protocollo è di competenza del MC, il RSPP fornisce i dati sui rischi.

### `/piano-miglioramento`
**Funzione**: Programma misure prevenzione e protezione (art. 28 c. 2 lett. c).
**Output**: .docx con: tabella interventi prioritizzati (rischio residuo, area, misura, responsabile, scadenza, costo stimato, stato), cronoprogramma, KPI di avanzamento.

### `/riunione-periodica`
**Funzione**: Template verbale riunione periodica art. 35.
**Output**: .docx con: data, partecipanti (DL, RSPP, MC, RLS), OdG obbligatorio (DVR, DPI, formazione, andamento infortuni/MP), spazio per deliberazioni, firma partecipanti. Include dati statistici infortuni da compilare.

---

## 3. Comandi di verifica

### `/checklist-81 [area]`
**Funzione**: Checklist conformità D.Lgs. 81/08 per area.
**Input**: Area o tema (es. generale, biologico, chimico, antincendio, VDT, luoghi di lavoro)
**Output**: Checklist con: requisito normativo (articolo), conforme/non conforme/NA, evidenza, note/azioni. Formato tabellare.
**Esempi**: `/checklist-81 generale`, `/checklist-81 biologico`, `/checklist-81 antincendio`, `/checklist-81 formazione`

### `/procedura-sicurezza [tema]`
**Funzione**: Procedura o istruzione operativa di sicurezza.
**Input**: Tema sicurezza
**Output**: .docx con codifica SIC-PO/IO-AREA-NNN: scopo, riferimenti normativi, responsabilità, descrizione attività/passi operativi, DPI, registrazioni. Indicazione documento SGQ complementare ove applicabile.
**Esempi**: `/procedura-sicurezza gestione esposizione accidentale agenti biologici`, `/procedura-sicurezza manipolazione chemioterapici`, `/procedura-sicurezza lockout-tagout`

---

## 4. Comandi CoVe

### `/cove`
Report CoVe completo (4 fasi) per ultima risposta.

### `/cove-check [claim]`
Verifica CoVe esplicita su singolo claim.

### `/cove-report`
Report sintetico verifica con esiti V/I/E/NV.
