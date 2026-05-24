---
name: docx-style-cloner
description: Clona lo stile editoriale completo di un documento Word di riferimento (font, paragrafi, stili nominati, sezioni, margini, header/footer con immagini) per produrre un nuovo .docx con contenuto diverso ma identica veste grafica. Usa SEMPRE quando l'utente fornisce un file .docx come "riferimento di stile" e chiede di produrre un nuovo documento che ne mantenga layout, formattazione, intestazioni e piè di pagina. Triggera anche per "clona stile docx", "stessa formattazione di questo documento", "usa questo come modello di stile", "mantieni layout e header", "/clona-stile", "/clona-docx", "stessa veste grafica del documento allegato". La skill applica una strategia di "template + body replacement": preserva al 100% header, footer, immagini, sezioni e stili del riferimento, sostituendo solo il contenuto del corpo. Pone tre domande Q&A essenziali prima di generare l'output: (1) font, (2) aggiornamento header/footer, (3) segnaposto da sostituire. Compatibile con stile Amodeo per la redazione del contenuto.
---

# docx-style-cloner — Clonazione fedele dello stile editoriale di un documento Word

Skill per clonare in modo affidabile lo stile editoriale completo di un documento .docx di riferimento e produrre un nuovo documento che condivida con l'originale **font, dimensioni, allineamenti, rientri, interlinee, spaziature, stili nominati, gerarchia titoli, sezioni, margini, header/footer (testo + immagini), numerazione di pagina, e qualsiasi altro elemento di formattazione**. Il contenuto del nuovo documento è invece quello fornito dall'utente.

## Quando usarla

Attivare SEMPRE quando l'utente:

- fornisce un file .docx come **"esempio di stile"**, **"riferimento editoriale"**, **"modello"**, **"template"**, e chiede di produrre un altro documento che ne erediti la formattazione
- chiede esplicitamente di **clonare**, **replicare**, **mantenere identica** la veste grafica
- usa frasi come "stesso layout", "stessa formattazione", "stessa gerarchia di titoli", "stessi header e footer"
- usa i comandi: `/clona-stile`, `/clona-docx`, `/style-clone`

Non attivare quando:

- l'utente vuole solo modificare un documento esistente (usare la skill `docx`)
- l'utente vuole creare un documento ex-novo senza riferimento (usare la skill `docx`)
- il file di riferimento è in formato diverso da .docx (PDF, .doc legacy, ODT)

## Strategia: template + body replacement

La skill **non ricostruisce il documento da zero** estraendo i parametri di stile e ri-applicandoli. Quel metodo perde fedeltà su elementi complessi (immagini posizionate in header, watermark, SmartArt, tabelle annidate, numerazione personalizzata).

La skill **usa il file fisico di riferimento come template**:

1. Copia fisica del file .docx di riferimento (shutil)
2. Apre la copia con python-docx
3. **Rimuove i paragrafi e le tabelle del body** (preservando section properties, header, footer, stili, immagini in header/footer)
4. **Inserisce il nuovo contenuto** usando gli stili nominati già presenti (Heading 1, Heading 2, Normal, Quote, ecc.)
5. Applica eventuali modifiche richieste dall'utente (cambio font globale, aggiornamento testo header/footer)
6. Salva come nuovo file .docx

Il risultato è indistinguibile dal documento di riferimento per quanto riguarda layout e veste grafica.

## Workflow operativo

Segui questi passaggi in ordine.

### Step 1 — Acquisizione input

Prima di lanciare qualunque script, verifica che l'utente abbia fornito:

- **File .docx di riferimento** (path al file)
- **Contenuto del nuovo documento** (testo libero, brief, file allegato, o struttura con titoli e paragrafi)

Se manca uno dei due, chiedilo prima di procedere.

### Step 2 — Ispezione del documento di riferimento

Esegui lo script `scripts/inspect_reference.py` passando il path del file di riferimento. Lo script produce un report JSON con:

- **Font primario** del corpo del testo (con dimensione)
- **Stili nominati** presenti e usati nel documento
- **Sezioni** e relativi margini
- **Header e footer** di ciascuna sezione (testo e nomi delle immagini eventualmente presenti)
- **Tabelle, elenchi numerati, citazioni** rilevati
- **Lingua** di correzione

Mostra all'utente un sommario testuale di cosa hai rilevato. Esempio:

```
Riferimento analizzato: NOME_FILE.docx
- Font corpo: Calibri 11pt
- Stili usati: Normale, Titolo 1, Titolo 2, Citazione
- Sezioni: 1 (margini 2.5cm/2.5cm/2cm/2cm)
- Header: testo "Studio SCO Consulting" + immagine logo (logo_sco.png)
- Footer: numerazione pagina centrata + testo "Riservato"
- Lingua: it-IT
```

Questo serve a creare consapevolezza condivisa con l'utente prima delle scelte.

### Step 3 — Q&A essenziale (tre domande)

Usa il tool `AskUserQuestion` per porre **esattamente queste tre domande**, una sola tornata:

**Domanda 1 — Font**

> "Mantengo il font del documento di riferimento ([nome_font_rilevato]) o uso un font più moderno?"
>
> Opzioni:
> - "Mantieni font originale" (Raccomandato — massima fedeltà al template)
> - "Aptos" (font moderno default di Office 365, sans-serif neutro)
> - "Inter" (font moderno open source, ottima leggibilità schermo)
> - "Source Sans Pro" (sans-serif Adobe, professionale e pulito)

**Domanda 2 — Aggiornamento header/footer**

> "Devo aggiornare i contenuti di header/footer? Riferimento attuale:
> Header: [contenuto_rilevato]
> Footer: [contenuto_rilevato]"
>
> Opzioni:
> - "Mantieni invariati" (Raccomandato)
> - "Aggiorna solo il titolo del documento"
> - "Aggiorna più elementi" (poi chiedi puntualmente quali)

**Domanda 3 — Segnaposto e campi**

> "Ci sono segnaposto, campi o testi specifici nel riferimento da sostituire nel nuovo documento? (es. nome cliente, data, codice documento, autore)"
>
> Opzioni:
> - "Nessun segnaposto" (Raccomandato se il riferimento è già pulito)
> - "Sì, sostituisco automaticamente data e codice documento" (la skill rileva pattern come `[DATA]`, `[CODICE]`, gg/mm/aaaa)
> - "Sì, fornisco una lista puntuale di sostituzioni"

Non fare domande aggiuntive oltre queste tre, salvo casi in cui l'utente abbia attivato l'opzione "Aggiorna più elementi" o "lista puntuale di sostituzioni".

### Step 4 — Generazione

Esegui lo script `scripts/clone_document.py` passando:

- Path del file di riferimento
- Path/contenuto del nuovo testo
- Risposte alle tre domande Q&A
- Path di output desiderato

Lo script produce il file finale .docx applicando tutte le scelte.

### Step 5 — Verifica e consegna

Apri brevemente il file di output con `inspect_reference.py` per verificare che:

- Il font sia quello atteso (originale o moderno scelto)
- Header/footer siano coerenti con le scelte dell'utente
- Stili nominati e gerarchia titoli siano stati preservati
- Le immagini in header/footer siano ancora presenti

Riporta un riepilogo all'utente:

```
Documento generato: NOME_OUTPUT.docx
- Font corpo: [scelta]
- Stili applicati: [elenco stili usati nel nuovo contenuto]
- Header/Footer: [invariati / aggiornati con valori X, Y]
- Sostituzioni effettuate: [elenco]
```

Fornisci il file con link `computer://`.

## Stile del contenuto

Per la redazione del contenuto del nuovo documento, attiva la skill `amodeo-voice` se il documento è una nota tecnica, relazione, report di assessment, parere, o comunicazione professionale. La skill `amodeo-voice` gestisce il **tono di scrittura**, mentre `docx-style-cloner` gestisce esclusivamente la **veste grafica**.

## Limiti noti

- Non clona documenti protetti da password (richiedere all'utente la password o la rimozione)
- Non clona elementi OLE embedded (oggetti Excel, equation editor legacy)
- Le immagini in header/footer vengono **preservate** ma non sostituite automaticamente: per cambiare un logo serve sostituirlo manualmente nel file di output o farne richiesta esplicita
- I documenti con macro (.docm) vengono trattati come .docx (le macro non vengono propagate)
- I commenti e le revisioni del riferimento vengono **rimossi** nell'output (per default puliamo il documento finale)

## Dipendenze

- Python 3
- `python-docx` (≥ 1.1.0)
- `lxml` (per manipolazione XML diretta in casi avanzati)

Installazione:

```bash
pip install python-docx lxml --break-system-packages
```

## File di skill

```
docx-style-cloner/
├── SKILL.md                    # questo file
├── README.md                   # istruzioni installazione
├── scripts/
│   ├── inspect_reference.py    # analisi del documento di riferimento
│   └── clone_document.py       # generazione documento finale
└── references/
    └── workflow_example.md     # esempio operativo end-to-end
```
