# Architettura del Sistema IRAI — Componenti, Zone, Loop

## 1. Componenti del sistema (EN 54-1 / UNI 9795:2013)

### Componenti obbligatori

| Codice | Componente | EN 54 |
|---|---|---|
| **A** | Rivelatore(i) d'incendio | EN 54-5/6/7/10/12/20 |
| **B** | Centrale di controllo e segnalazione | EN 54-2 |
| **C** | Dispositivo(i) di allarme incendio | EN 54-3/23 |
| **D** | Punto(i) di segnalazione manuale | EN 54-11 |
| **L** | Apparecchiatura di alimentazione | EN 54-4 |

### Componenti opzionali

| Codice | Componente | EN 54 |
|---|---|---|
| **E** | Dispositivo trasmissione allarme incendio | EN 54-21 |
| **F** | Stazione ricevente allarme incendio | — |
| **G** | Comando sistema automatico antincendio | — |
| **H** | Sistema automatico antincendio | — |
| **J** | Dispositivo trasmissione segnale di guasto | EN 54-21 |
| **K** | Stazione ricevente segnale di guasto | — |
| **M** | Centrale allarme vocale | EN 54-16 |
| **N** | Interfaccia comunicazione dati | — |
| **O** | Sistema grafico o BMS | — |

**Nota**: per i collegamenti agli elementi G è necessaria la segnalazione di guasto sulla centrale per corto circuito o interruzione di linea (UNI EN 54-2).

### Funzioni del sistema
- **Funzione di rivelazione** (automatica e manuale)
- **Funzione di comando** (segnalazioni e attivazioni)
- **Funzioni associate locali** (allarme, EVAC, attuazioni)
- **Funzioni associate remote** (trasmissione allarme/guasto)

---

## 2. Sistemi convenzionali vs. indirizzati

### Sistema convenzionale
- La centrale distingue solo la **zona** di allarme (gruppo di rivelatori)
- Non identifica il singolo rivelatore
- Linee aperte con max **32 rivelatori** per linea
- Tipologie rivelatori diversi sulla stessa linea (es. ottico + termico + chimico)

### Sistema analogico indirizzato
- Ogni rivelatore ha un **ID specifico** → individuazione del singolo punto
- Consente localizzazione precisa, non solo la zona
- Configurazione tipica: **loop** ad anello
- Oltre **32** elementi su linea chiusa → obbligatorio **isolatori EN 54-17**
- Possibilità di programmazione zone logiche indipendenti dalla linea fisica

---

## 3. Suddivisione in zone [UNI 9795 § 5.2]

### Definizioni
- **Zona**: suddivisione geografica dei locali sorvegliati, in cui sono installati uno o più punti, con propria segnalazione comune
- **Area**: una o più zone protette dal sistema

### Regole di suddivisione

| Parametro | Limite |
|---|---|
| **Superficie max per zona** | 1600 m² |
| **Max locali per zona** (≤600 m², accessi su stesso disimpegno) | 10 locali |
| **Max locali per zona** (≤1000 m², con segnalatori ottici) | 20 locali |
| **Zone su piani diversi** | **NO** — ciascuna zona su un solo piano |

### Regole aggiuntive
- Le zone devono essere delimitate per localizzare **rapidamente e senza incertezze** il focolaio
- Spazi nascosti (sottopavimenti, controsoffitti, cunicoli, condotte) → **zone distinte**
- Sistemi di sola segnalazione manuale → assenti i rivelatori automatici

---

## 4. Aree da sorvegliare e aree escluse [UNI 9795 § 5.1]

### Aree da sorvegliare obbligatoriamente (§ 5.1.2)
- Vani elevatori, ascensori, montacarichi e relativi locali tecnici
- Cortili interni coperti
- Cunicoli e cavedi per cavi elettrici
- Condotti di condizionamento, aerazione, ventilazione
- Controsoffitti e sottopavimenti

### Aree NON necessariamente da coprire (§ 5.1.3)
- Servizi igienici (se non usati come depositi combustibili)
- Cavedi con sezione <1 m² se compartimentati
- Vani elevatori se parte di compartimento sorvegliato
- Vani scale compartimentati
- Banchine di carico scoperte
- Spazi nascosti (controsoffitti/sottopavimenti) che rispettano TUTTI questi requisiti:
  - Altezza <800 mm
  - Superficie <100 m²
  - Dimensione lineare <25 m
  - Rivestiti in materiale classe A1 e A1FL
  - Non contengono cavi di emergenza (salvo cavi resistenti al fuoco ≥30 min)
- Condotte di condizionamento con:
  - Canale mandata con portata <3500 m³/h
  - Canali ricircolo se: area servita completamente protetta, edificio un solo piano, e l'unità trasferisce aria solo dall'interno all'esterno

---

## 5. Isolatori di corto circuito [EN 54-17]

### Obbligo
Su linea chiusa (loop) con oltre **32 elementi**: obbligatori.

### Tipologie

| Tipo | Configurazione | Conseguenza guasto |
|---|---|---|
| **1 isolatore ogni n elementi** | Isolatori distribuiti lungo il loop | Perdita di tutti gli elementi **tra i due isolatori** intervenuti |
| **1 isolatore per ogni elemento** | Un isolatore a monte di ciascun dispositivo | Perdita del **solo elemento** a valle del corto circuito |
| **2 isolatori per ogni elemento** | Un isolatore a monte e uno a valle | **Nessun elemento** perso |

### Installazione secondo UNI 9795
Un isolatore deve essere posto in modo che un corto circuito o un'interruzione non impedisca la segnalazione di allarme per **più di una zona**.

---

## 6. Centrale di controllo e segnalazione [EN 54-2]

### Requisiti di ubicazione
- Protetta da rivelatori automatici **se non presidiata**
- Dotata di **illuminazione di emergenza**
- Se non presidiata → sistema di **trasmissione a luoghi presidiati** (connessione monitorata tramite EN 54-21), da cui gli addetti possano avviare misure di intervento **in ogni momento e con tempestività**

---

## 7. Alimentazione [EN 54-4, UNI 9795]

### Requisiti
- Almeno **2 fonti** di alimentazione:
  - **Primaria**: rete pubblica
  - **Secondaria**: batteria di accumulatori o rete di sicurezza indipendente
- L'alimentazione di riserva deve assicurare il funzionamento per un tempo pari alla somma dei tempi necessari per segnalazione + intervento + ripristino, e comunque **non meno di 24 h + 30 minuti in allarme**
- Un UPS non sostituisce la batteria EN 54-4

---

## 8. Segnalazione acustica e EVAC [UNI 9795 § 5.5.3]

### Tre livelli di segnalazione

| Sistema | Attivazione | Segnale | Norme prodotto |
|---|---|---|---|
| **Allarme con dispositivi sonori** | Automatica (dal sistema) | Segnale acustico, sirene, lampeggianti | EN 54-3 |
| **Allarme vocale UNI ISO 7240-19** | Automatica o manuale | Messaggio vocale preregistrato o al microfono | EN 54-16 + EN 54-24 + EN 54-4 |
| **Allarme vocale EN 60849** | Manuale (personale sicurezza) | Messaggio vocale | — |

### Note
- Sistemi vocali possono essere integrazione o sostituti dei dispositivi sonori
- I dispositivi sonori **non devono interferire** con l'intelligibilità del messaggio vocale
- Per sistemi EVAC: cavi con rivestimento esterno **colore viola** (CEI 20-105)

---

## 9. Ispezioni periodiche [UNI 9795]

- Almeno **2 volte l'anno**, con intervallo non minore di **5 mesi**
- Il datore di lavoro è responsabile del mantenimento dell'efficienza
- L'accertamento deve essere formalizzato nel registro con: variazioni riscontrate, deficienze riscontrate
