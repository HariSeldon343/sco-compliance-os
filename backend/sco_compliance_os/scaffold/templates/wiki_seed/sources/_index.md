---
type: sources-index
title: "Sources - schede di sintesi delle fonti raw"
status: stub
last_reviewed: 2026-05-24
tags: [wiki, sources, indice]
parent: "[[wiki/_index]]"
---

## 1. Funzione di wiki/sources/

La cartella `wiki/sources/` ospita le schede di sintesi delle fonti depositate in `raw/`. Ogni fonte raw (PDF normativa, articolo, audit report, evidenza cliente, web-clip) ha una scheda di sintesi corrispondente in `wiki/sources/<slug>.md` che ne sintetizza il contenuto e ne preserva la provenance metadata. Lo scopo delle schede e: (a) consentire alla LLM Wiki di richiamare la fonte senza dover rileggere ogni volta il PDF intero; (b) preservare la tracciabilita (hash MD5, parser, data di import, ente emittente); (c) costituire l'anello di congiunzione fra le entity wiki e le fonti raw immutabili.

## 2. Schema standard B Ondata 4 (mandatory dal 07/05/2026)

A partire dal 07/05/2026 sera tarda, ogni nuova scheda in `wiki/sources/` deve adottare lo schema standard B con frontmatter ricco di provenance metadata. Le schede esistenti pre-Ondata 4 sono soggette a migrazione progressiva nel LINT settimanale.

### Frontmatter standard B

```yaml
---
type: source
title: "<Nome canonico della fonte>"
fonte_primaria: "[[raw/normativa/<PDF>]]"
entity_collegata: "[[wiki/entities/<slug>]]"
ente_emittente: "<UNI / ISO / IEC / D.Lgs. / Reg. UE / etc.>"
data_pubblicazione: <YYYY>
data_import_vault: <YYYY-MM-DD>
parser: "<pdftotext / pandoc / OCR / etc.>"
hash_md5: "<da popolare in fase di ingest>"
dimensione_byte: <int>
pagine: <int o n/a>
status: active | superseded | deprecated
tags: [source, <ente>, <ambito>, <eventuali tag dominio>]
---
```

### Body

Sintesi 1 paragrafo (200-300 parole) sul contenuto della fonte + cronologia revisioni source quando applicabile (ricaricamenti PDF, transizioni edizione standard come ISO/IEC 27018:2019 -> 2025).

## 3. Esempio scheda standard B

```yaml
---
type: source
title: "ISO/IEC 27001:2022 - Information security management systems - Requirements"
fonte_primaria: "[[raw/standard/2022_iso-iec_27001-2022.pdf]]"
entity_collegata: "[[wiki/entities/iso-iec-27001-2022]]"
ente_emittente: "ISO/IEC JTC 1/SC 27"
data_pubblicazione: 2022
data_import_vault: 2026-05-24
parser: "pdftotext"
hash_md5: "abc123def456..."
dimensione_byte: 524288
pagine: 19
status: active
tags: [source, iso-iec, cybersicurezza, sgsi, standard-tecnico]
---

ISO/IEC 27001:2022 specifica i requisiti per stabilire, implementare, mantenere e migliorare in modo continuo un sistema di gestione per la sicurezza delle informazioni (SGSI). La revisione 2022 introduce un Annex A completamente ristrutturato con 93 controlli organizzati in 4 temi (organizzativi, persone, fisici, tecnologici) rispetto ai 114 controlli precedenti in 14 domini. La struttura segue la High Level Structure comune ai sistemi di gestione ISO. Periodo transitorio: 36 mesi per organismi accreditati. Edizione recepita in Italia come UNI CEI EN ISO/IEC 27001:2024.

Cronologia revisioni source: prima edizione 2005 (Annex SL non ancora applicato), seconda edizione 2013 (HLS applicata), terza edizione 2022 (Annex A ristrutturato). Recepimento italiano 2024.
```

## 4. Categorie di sources

| Categoria | Cartella raw/ | Esempi |
|---|---|---|
| Normativa | `raw/normativa/` | D.Lgs. 138/2024, Reg. UE 2016/679, AI Act |
| Standard tecnici | `raw/standard/` | ISO/IEC 27001:2022, ISO 9001:2015, ISO/IEC 42001:2023 |
| Linee guida | `raw/linee-guida/` | Linee guida ENISA, AgID, AGENAS, ISS |
| Audit | `raw/audit/` | Rapporti audit di terza parte, gap analysis cliente |
| Evidenze cliente | `raw/client-evidence/` | Documentazione cliente di evidenza per audit |
| Web-clip | `raw/web-clip/` | Articoli, blog, post di settore, notizie regolatorie |
