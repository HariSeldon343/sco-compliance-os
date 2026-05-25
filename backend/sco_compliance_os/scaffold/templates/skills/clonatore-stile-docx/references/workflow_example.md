# Esempio operativo end-to-end

Questo file mostra il flusso completo di utilizzo della skill `clonatore-stile-docx` su un caso reale.

## Scenario

L'utente ha un documento `relazione_audit_27001_clienteX.docx` che gli piace come stile editoriale: Calibri 11pt, header con logo aziendale Azienda S.r.l., footer con numerazione di pagina e codice documento, gerarchia titoli su tre livelli, citazioni in corsivo. Vuole produrre una nuova relazione di audit per un cliente diverso, con lo stesso identico aspetto ma contenuto diverso.

## Step 1 — Acquisizione input

L'utente fornisce:

- **Riferimento:** `C:\path\relazione_audit_27001_clienteX.docx`
- **Contenuto nuovo:** brief con i contenuti dell'audit per il Cliente Y, strutturato in capitoli e paragrafi

## Step 2 — Ispezione

Eseguito `inspect_reference.py`:

```json
{
  "file": "relazione_audit_27001_clienteX.docx",
  "primary_font": {"name": "Calibri", "size_pt": 11.0},
  "named_styles_used": [
    "Citazione", "Heading 1", "Heading 2", "Heading 3", "Normale", "Titolo"
  ],
  "sections_count": 1,
  "sections": [{
    "page_size_cm": {"width": 21.0, "height": 29.7},
    "margins_cm": {"top": 2.5, "bottom": 2.5, "left": 2.5, "right": 2.5,
                   "header_distance": 1.27, "footer_distance": 1.27},
    "orientation": "PORTRAIT",
    "header": {
      "text": "Azienda S.r.l. | Relazione di audit ISO/IEC 27001:2022",
      "paragraphs": ["Azienda S.r.l. | Relazione di audit ISO/IEC 27001:2022"],
      "images": [{"rId": "rId7"}]
    },
    "footer": {
      "text": "Codice: DOC-AUD-2026-001 | Pag.",
      "paragraphs": ["Codice: DOC-AUD-2026-001 | Pag."],
      "images": []
    }
  }],
  "language": "it-IT",
  "tables_count": 3,
  "lists_count": 12,
  "warnings": []
}
```

Sommario testuale presentato all'utente:

```
Riferimento analizzato: relazione_audit_27001_clienteX.docx
- Font corpo: Calibri 11pt
- Stili usati: Normale, Titolo, Heading 1, Heading 2, Heading 3, Citazione
- Sezioni: 1 (A4, margini 2.5cm)
- Header: "Azienda S.r.l. | Relazione di audit ISO/IEC 27001:2022" + immagine logo
- Footer: "Codice: DOC-AUD-2026-001 | Pag."
- Tabelle: 3 | Elenchi: 12
- Lingua: it-IT
```

## Step 3 — Q&A

**Domanda 1 — Font:** L'utente sceglie "Mantieni font originale" → Calibri 11pt.

**Domanda 2 — Header/Footer:** L'utente sceglie "Aggiorna più elementi":

- Header: invariato (logo e titolo categoria sono validi)
- Footer: il codice documento `DOC-AUD-2026-001` deve diventare `DOC-AUD-2026-018`

**Domanda 3 — Segnaposto:** L'utente fornisce queste sostituzioni puntuali:

- `Cliente X S.r.l.` → `Cliente Y S.p.A.`
- `15/01/2026` → `26/04/2026` (data audit)
- `Auditor lead: [nome]` → `Auditor lead: Mario Rossi`

## Step 4 — Generazione

Predisposto `content.json` con la struttura del nuovo audit:

```json
{
  "blocks": [
    {"type": "title", "text": "Relazione di audit ISO/IEC 27001:2022"},
    {"type": "paragraph", "text": "Cliente: Cliente Y S.p.A. — Audit di sorveglianza"},
    {"type": "heading1", "text": "1. Obiettivo e scopo dell'audit"},
    {"type": "paragraph", "text": "L'audit è stato condotto in data 26/04/2026 presso la sede di Cliente Y S.p.A. con l'obiettivo di verificare il mantenimento della conformità del Sistema di Gestione per la Sicurezza delle Informazioni rispetto ai requisiti della norma ISO/IEC 27001:2022."},
    {"type": "heading1", "text": "2. Team di audit"},
    {"type": "paragraph", "text": "Auditor lead: Mario Rossi"},
    {"type": "heading1", "text": "3. Risultanze"},
    {"type": "heading2", "text": "3.1 Punti di forza"},
    {"type": "paragraph", "text": "..."},
    {"type": "heading2", "text": "3.2 Non conformità"},
    {"type": "paragraph", "text": "..."}
  ]
}
```

Comando eseguito:

```bash
python scripts/clone_document.py \
  --reference "relazione_audit_27001_clienteX.docx" \
  --content "content.json" \
  --output "relazione_audit_27001_clienteY.docx" \
  --footer-replacements '{"DOC-AUD-2026-001":"DOC-AUD-2026-018"}' \
  --placeholders '{"Cliente X S.r.l.":"Cliente Y S.p.A.", "15/01/2026":"26/04/2026", "Auditor lead: [nome]":"Auditor lead: Mario Rossi"}'
```

## Step 5 — Verifica

Riesecuzione di `inspect_reference.py` sul file di output per confermare:

- Font: Calibri 11pt ✓
- Stili nominati: invariati ✓
- Header: logo Azienda S.r.l. + testo originale ✓
- Footer: codice documento aggiornato a `DOC-AUD-2026-018` ✓
- Margini, sezioni, pagina: invariati ✓

## Output finale

File `relazione_audit_27001_clienteY.docx` con:

- Identica veste grafica del riferimento
- Contenuto nuovo strutturato secondo i blocchi forniti
- Footer aggiornato con il nuovo codice documento
- Tutti i segnaposto sostituiti

Tempo totale di esecuzione: pochi secondi, indipendentemente dalla lunghezza del documento.
