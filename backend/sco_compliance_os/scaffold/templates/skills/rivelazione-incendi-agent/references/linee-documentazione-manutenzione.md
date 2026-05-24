# Linee di Interconnessione, Documentazione di Progetto e Manutenzione

## 1. Linee di interconnessione [UNI 9795:2013 § 6]

### Requisiti generali cavi
- Sezione minima: **0,5 mm²**
- Conduttori **flessibili** (non ammessi conduttori rigidi)
- Resistenti al fuoco per almeno **30 minuti** secondo CEI EN 50200
- Bassa emissione di fumo e zero alogeni (**LSOH**)
- I cavi devono garantire il funzionamento del circuito **in condizioni di incendio**

### Cavi per apparati ≤100 V c.a. (sensori, pulsanti, interfacce, sirene)
- Resistenti al fuoco conformi a **CEI EN 50200** (requisito minimo PH 30)
- In caso di zone/compartimenti distinti: mantenimento funzioni per periodo ≥ quello prescritto dalle regole tecniche di prevenzione incendi
- Costruiti secondo norma **CEI 20-105**

### Cavi per apparati >100 V c.a. (illuminazione emergenza, SENFC, elettroserrature, comandi emergenza)
- Conformi a **CEI 20-45** (LSOH, U₀/U = 0,6/1 kV)
- Conduttori flessibili, sezione minima **1,5 mm²**
- Colore isolamento esterno: **Blu**

### Cavi per sistemi EVAC (linee 70V/100V c.a.)
- Cavi a bassa capacità con rivestimento esterno colore **Viola**
- Costruiti secondo **CEI 20-105**
- **ATTENZIONE**: la CEI 20-105 garantisce integrità circuito in emergenza ma **non** specifica le caratteristiche trasmissive → necessario verificare parametri trasmissivi (induttanza, capacità, impedenza) con i requisiti del costruttore di apparati

### Parametri trasmissivi per sistemi indirizzati
Negli impianti indirizzati, l'interoperabilità avviene tramite **protocollo bus** → attenzione ai parametri trasmissivi per evitare riflessioni, interferenze o guasti casuali. Verificare:
- Compatibilità cavo con protocollo della centrale
- Lunghezza massima del loop
- Capacità, induttanza, impedenza del cavo
- Richiedere ai costruttori i parametri minimi delle linee

### Gerarchia norme cavi

| Norma | Cosa garantisce |
|---|---|
| **CEI EN 50200** | Metodo di prova — integrità circuito durante incendio (PH 30) |
| **CEI 20-105** | Norma di prodotto — caratteristiche costruttive (materiali, isolamenti, spessori, sezioni, schermature) |
| **CEI 20-45** | Cavi LSOH 0,6/1 kV per circuiti >100 V c.a. |
| **CEI 20-35** | Non propagazione fiamma (singolo cavo, >65 cm) |
| **CEI 20-22/III (CEI EN 60332-3-25)** | Non propagazione incendio in fascio |
| **CEI 20-36** | Resistenza al fuoco |

### Isolanti e costanti dielettriche

| Materiale isolante | Costante dielettrica | Tipo cavo CEI 20-105 |
|---|---|---|
| Vetro-mica (T) | — | FTE4OHM1 |
| Silicone (G4) | 8-16 | FG4OHM1 |

Il tipo di isolamento deve essere scelto in base al tipo di installazione (es. lunghezza loop) per garantire il corretto funzionamento.

### Verifiche obbligatorie
1. Caratteristiche trasmissive congrue con quelle richieste dal costruttore
2. Test report emessi da laboratori accreditati a livello nazionale
3. Dichiarazione di idoneità del cavo per le condizioni di posa
4. Dichiarazioni di conformità del costruttore
5. Documentazione valida e in linea con requisiti normativi attuali
6. In caso di subappalto: verificare che i componenti installati siano quelli previsti da capitolato

### Domande critiche
- In caso di sostituzione della centrale o dei rivelatori → è necessario sostituire tutti i cavi?
- In caso di ampliamento di un impianto → è necessario revisionare l'intero impianto?

---

## 2. Documentazione di progetto [UNI 9795 Appendice A]

### Fase preliminare — Progetto preliminare e/o di massima (A.2)
- Relazione tecnico-descrittiva dell'impianto comprensiva di **schema a blocchi**
- Insieme di tavole grafiche che illustri:
  - Tipo di installazione
  - Aree non protette
  - Destinazione d'uso dei locali
  - Sezione trasversale dell'intero edificio con posizione dei rivelatori
- Dichiarazione che il progetto si basa sulla **UNI 9795**

### Fase successiva — Progetto definitivo e/o esecutivo (A.3)
- A.3.1: Dettaglio tecnico completo
- A.3.3: Calcoli dimensionali, planimetrie esecutive
- A.3.4: Elenco componenti con riferimenti EN 54
- A.3.5: Schemi elettrici e di collegamento

---

## 3. Manutenzione — UNI 11224

### Controllo iniziale
- Controllo del **100%** dei componenti del sistema
- Accertamento del rispetto delle prescrizioni di legge
- Congruenza delle logiche di segnalazione/attuazione
- Efficienza della centrale inclusi i **tempi di autonomia delle batterie**
- Attivazione degli allarmi su **ogni dispositivo** — **NON È CONSENTITO L'USO DEL MAGNETE** per le attivazioni
- Verifica delle corrette attivazioni a seguito di allarmi
- Verifica dell'intensità dei dispositivi ottici e acustici
- Verifica delle logiche di programmazione
- Simulare la **mancanza rete** per valutare l'efficacia dei sistemi ausiliari

### Manutenzione periodica [UNI 9795 § 7]
- Almeno **2 volte l'anno**, con intervallo non minore di **5 mesi**
- Il datore di lavoro è responsabile del mantenimento delle condizioni di efficienza
- L'accertamento deve essere formalizzato nel **registro** con:
  - Eventuali variazioni riscontrate
  - Eventuali deficienze riscontrate

---

## 4. Documentazione DM 20/12/2012

Ai fini della valutazione del progetto, gli impianti di protezione attiva previsti nella documentazione tecnica (DM 7/8/2012 Allegato I) devono essere documentati con:
- **Specifica d'impianto** (contenuto conforme a § G.2.10 o alla norma applicata)
- **Dichiarazione di conformità** (DM 37/2008)
- **Dichiarazione di corretta installazione e funzionamento**
