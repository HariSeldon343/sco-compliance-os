# Criteri di Scelta e Dimensionamento Rivelatori — UNI 9795:2013

## 1. Principi generali di scelta

### Scopo del sistema IRAI
Rilevare tempestivamente un processo di combustione al suo inizio (fase di innesco e prima propagazione) PRIMA che l'incendio si generalizzi, per:
- Attivare l'esodo e il piano di emergenza
- Attivare le misure di contrasto (sprinkler, SENFC, compartimentazione)
- Contenere i danni

### Fasi evolutive di un processo di combustione

| Fase | Caratteristiche | Prodotto rilevabile |
|---|---|---|
| **Fuoco covante** (pirolisi/braci) | Lento, può auto-estinguersi o auto-alimentarsi | Gas, fumo chiaro |
| **Fase incipiente** | Fiamma iniziale, fumo visibile | Fumo, gas, fiamma |
| **Fuoco aperto** | Rapida propagazione | Fumo scuro, calore, fiamma |
| **Incendio generalizzato** | Pieno sviluppo | Calore intenso, fiamma |

### Condizioni al contorno per la scelta
- Tipologia di materiale combustibile
- Quantitativi e metodologia di stoccaggio
- Velocità di sviluppo dell'incendio atteso
- Moti ascensionali, tossicità, opacità dei fumi

---

## 2. Classificazione dei rivelatori

### Per tipo di fenomeno rilevato

| Fenomeno | Metodo | Rivelatore | EN 54 |
|---|---|---|---|
| **Fumo** | Ottico (fotoelettronico / oscuramento) | Puntiforme | EN 54-7 |
| **Fumo** | Ottico (fascio) | Lineare | EN 54-12 |
| **Fumo** | Campionamento aria | Aspirazione (ASD) | EN 54-20 |
| **Fumo** | Ionizzazione (Americio-241) | Chimico-ionizzazione | (obsoleto, non più prodotto) |
| **Calore** | Soglia statica | Termico puntiforme | EN 54-5 |
| **Calore** | Differenziale (ΔT/Δt) | Termovelocimetrico | EN 54-6 |
| **Calore** | Fusione mescola tarata | Lineare di calore | — |
| **Fiamma** | Radiazione UV | Fiamma UV | EN 54-10 |
| **Fiamma** | Radiazione IR | Fiamma IR | EN 54-10 |
| **Scintilla** | Collisione / sfregamento | Scintilla | — |
| **Combinato** | Multi-sensore (ottico+termico+CO) | Combinato | EN 54-7 + EN 54-5 |

### Sensibilità: ottici vs. ionizzazione
- **Ottici tradizionali**: rilevano efficacemente fumi **chiari** (fuochi covanti). Diminuiscono efficienza con componente scura.
- **Ottici dual-ray / ISP**: migliorano la rilevazione di fumi scuri grazie a doppio sensore ottico o sensore chimico CO.
- **Ionizzazione**: più sensibili a fumi **scuri** (fuochi rapidi), ma in disuso per la sorgente radioattiva (Americio-241).

---

## 3. Rivelatori puntiformi di calore [UNI 9795 § 5.4.2]

### Limiti
- Conformi a **EN 54-5** (soglia statica) o **EN 54-6** (termovelocimetrico)
- **Altezza massima installazione: 8 m**
- Distanza minima dalla parete: **0,5 m** (eccezione: corridoi, cunicoli)
- Nessun macchinario o materiale a meno di **0,5 m** a fianco e al disotto

### Soffitto piano
- Raggio di copertura e superficie secondo tabelle UNI 9795 (dipendono da altezza locale)

### Soffitto inclinato (pendenza >20°)
- **Spiovente/doppio spiovente**: fila di rivelatori nel piano verticale passante per la linea di colmo (parte più alta)
- **Shed/falda trasparente**: fila di rivelatori nella parte con pendenza minore (non trasparente), a **1 m** di distanza orizzontale dal piano di colmo

### Soffitto a travi o correnti in vista
- h elemento ≤10% H locale → **soffitto piano** (dimensionamento standard)
- h elemento >30% H locale → ogni riquadro = **locale a sé stante**
- Tra 10% e 30% → travi parallele: distanza tra rivelatori in direzione parallela **S₂ = 6 m**
- Travi intersecanti: distribuzione secondo riquadri

### Corridoi e piccoli locali
- Corridoi larghezza ≤3 m con travi ≤30% H: modalità soffitto piano
- Locali ≤20 m² con travi ≤30% H: modalità soffitto piano

### Soffitto a nido d'ape
Volume max celle protette da un singolo rivelatore: **V = 4 m × (H locale − h trave)**

### Controsoffitti e pavimenti sopraelevati senza circolazione d'aria
- Per altezze >1 m: dimensionamento standard
- Ribassamenti nella metà superiore con altezza > metà dello spazio → considerati come **muri**

---

## 4. Rivelatori puntiformi di fumo [UNI 9795 § 5.4.3]

### Limiti
- Conformi a **EN 54-7**
- **Altezza massima installazione: 12 m** (16 m con condizioni favorevoli)
- Evitare installazione in zone con aerosol da lavorazione → rischio falsi allarmi
- Attenzione dove velocità aria >1 m/s normalmente o >5 m/s occasionalmente

### Cause comuni di falsi allarmi
Polvere, fumo sigaretta, vapore, umidità/condensa, scarsa manutenzione, errata installazione, errato posizionamento, disturbi EMC, insetti.

### Soffitto piano
Raggio di copertura secondo tabelle UNI 9795 (dipende da altezza locale).

### Soffitto inclinato (>20°)
Stessa logica dei rivelatori di calore (colmo/shed).

### Soffitto a travi in vista
- h ≤10% H → soffitto piano
- h >30% H → locale a sé stante
- Travi parallele: distanza tra rivelatori **S₂ = 9 m** (vs. 6 m per calore)

### Corridoi e piccoli locali
- Corridoi larghezza ≤3 m con travi ≤30% H: modalità soffitto piano
- Locali ≤**40 m²** con travi ≤30% H: modalità soffitto piano (vs. 20 m² per calore)

### Soffitto a nido d'ape
Volume max: **V = 8 m × (H locale − h trave)** (vs. 4 m per calore)

### Ambienti con circolazione d'aria elevata
- Proteggere rivelatori da corrente d'aria diretta (analisi posizione bocchette)
- Bocchette ripresa a soffitto: rivelatore a distanza ≥ **R = 1 m**
- Distribuzione uniforme ma il più lontano possibile dalle bocchette

### Controsoffitti e sottopavimenti con circolazione d'aria
Per spazi nascosti in locali con impianti di benessere: si applicano le regole per locali **senza** condizionamento.

---

## 5. Rivelatori ottici lineari di fumo [UNI 9795 § 5.4.4]

### Limiti
- Conformi a **EN 54-12**
- Area a pavimento sorvegliata ≤ **1600 m²**
- Larghezza max di copertura: **15 m** per soffitti piani

### Soffitto piano
- Distanza dal soffitto entro il **10%** dell'altezza del locale
- Se non possibile rispettare il 10%: limite inferiore del **25%** rispetto all'altezza di colmo, con installazione addizionale del **+50%** dei rivelatori

### Soffitto a shed o falde inclinate
- Parallelo o trasversale all'andamento dello shed
- Se possibile: prossimi alla linea di colmo
- Trasversale con altezza shed ≤15% H totale: area di copertura convenzionale
- Altezza shed >15%: **1 rivelatore addizionale ogni 2**, minimo **2 per campata**

### Soffitto a volta
- Altezza installazione entro il **10%** dell'altezza al colmo

### Cupola/calotta semisferica
- Collocare lungo il piano d'appoggio o base
- Se >12 m o base cupola <50% altezza totale: installazione a **matrice**, larghezza max copertura **8 m**

### Grandi altezze (>12 m)
Oltre ai rivelatori sotto il soffitto: rivelatori a **quote intermedie** e/o installazione a **matrice** (parallela + trasversale) su livelli sovrapposti. Applicazioni: aeroporti, stazioni ferroviarie, palazzetti, padiglioni fieristici, grandi edifici monumentali.

---

## 6. Rivelatori di fiamma [UNI 9795 § 5.4.5]

- Conformi a **EN 54-10**
- **Fiamme fredde** → ultravioletto (UV). Non idonei con oli/grassi/vetro/certi fumi.
- **Fiamme calde** → infrarosso (IR). Corretto in quasi tutte le condizioni.
- **Esposti a luce solare** → tipo schermato o **triplo canale**
- Non devono essere montati necessariamente a soffitto (possono essere orientati)

---

## 7. Sistemi ad aspirazione (ASD) [UNI 9795 § 5.4.6, EN 54-20]

Rivelatore di fumo ad alta sensibilità con rete di tubazioni di campionamento aria.

| Classe | Sensibilità | Applicazione tipica |
|---|---|---|
| **C** | Normale (equivalente a puntiforme) | Ambienti standard |
| **B** | Aumentata | Diluizione fumo, forti correnti d'aria, soffitti alti |
| **A** | Alta | Protezione ad oggetto (macchinari alto valore, quadri elettrici), soglia precoce per attività critiche |

- Calcolo dimensionamento con strumenti software specifici del costruttore
- Classe in funzione dell'altezza del locale e della criticità

---

## 8. Pulsanti manuali [UNI 9795 § 5.5, EN 54-11]

- Conformi a **EN 54-11**
- Almeno **2 pulsanti per zona**
- Ogni punto raggiungibile con percorso ≤ **30 m** (15 m per rischio elevato)
- Posizionati in prossimità di **tutte le uscite di sicurezza**
- Suddivisione in zone identica ai rivelatori
- Altezza installazione: **1 m — 1,6 m**
- Cartello conforme **UNI EN ISO 7010**

---

## 9. Rivelatori combinati

- Conformi ad **almeno una** norma EN 54 specifica
- Combinazioni: ottico + termico + chimico (CO)
- Copertura: si applica il criterio **più restrittivo** tra i sensori presenti

---

## 10. Connessioni via radio [EN 54-25]

- Comunicazione **bidirezionale** tra gateway e componenti
- Alimentazione **supervisionata**
