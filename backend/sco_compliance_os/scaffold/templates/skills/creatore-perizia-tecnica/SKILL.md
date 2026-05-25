---
name: creatore-perizia-tecnica
description: "Crea perizie tecniche e relazioni di consulenza tecnica in piena forma peritale (frontespizio, indice con numeri di pagina, premessa e quesito, documentazione esaminata, accertamenti, conclusioni con risposta al quesito, riferimenti normativi), nello stile di il consulente normativo. Multi-dominio: cybersecurity, digital forensics, compliance e GDPR, sanita, antincendio, qualita, sicurezza sul lavoro. Supporta la modalita white-label, ossia documento a firma del cliente o committente senza alcun riferimento a SCO, consulente normativo o Fortibyte nel testo e nei metadati. Usa SEMPRE quando l'utente chiede di redigere una perizia, una relazione peritale, una relazione di consulenza tecnica (di parte o simil-CTU), una nota tecnico-difensiva strutturata, oppure di mettere un contenuto in forma di perizia. Triggera anche per: scrivi una perizia, perizia tecnica, relazione peritale, relazione di consulenza tecnica, perizia di parte, consulenza tecnica di parte, CTP, perizia forense, metti in forma di perizia, creatore perizia, /perizia."
---

# Skill: creatore-perizia-tecnica

## Scopo

Produrre perizie tecniche e relazioni di consulenza tecnica in piena forma peritale, nello stile di il consulente normativo, su qualsiasi dominio tecnico in cui opera: cybersecurity, digital forensics, compliance e protezione dati, sanita, prevenzione incendi, qualita, sicurezza sul lavoro. Supporta la modalita white-label: il documento esce a firma del cliente o committente, senza alcun riferimento al consulente reale (SCO, consulente normativo, Fortibyte) ne nel testo ne nei metadati del file.

Non e una skill di dominio: non contiene conoscenza normativa specifica. Per i contenuti tecnico-normativi si appoggia alle skill di dominio (cybernis, qualita-sanita, iso42001, risk-manager, rivelazione-incendi, ecc.) e per lo stile ad voce-consulenziale-formale.

## Quando usarla / Trigger

- "scrivi una perizia", "perizia tecnica", "relazione peritale", "relazione di consulenza tecnica"
- "perizia di parte", "consulenza tecnica di parte", "CTP", "perizia forense"
- "metti in forma di perizia", "creatore perizia", "/perizia"

## Domande iniziali (prima di redigere)

Chiedi sempre, via AskUserQuestion, e attendi conferma su:

1. Committente e soggetto interessato: chi conferisce l'incarico e su chi o cosa verte la perizia.
2. Quesito o quesiti a cui rispondere: gli oggetti puntuali dell'incarico.
3. A firma di chi esce il documento e se in modalita white-label: in tal caso nessun riferimento al consulente reale, da verificare anche nei metadati.
4. Ambito tecnico e quadro normativo applicabile.
5. Documentazione ed evidenze disponibili da esaminare, e dove si trovano.
6. Formato di consegna (docx, PDF) e se clonare una carta intestata esistente.

## Struttura del documento (forma peritale)

Front matter:

- Frontespizio: denominazione del documento (PERIZIA TECNICA o RELAZIONE DI CONSULENZA TECNICA), titolo esteso, soggetto interessato, committente, protocollo, revisione, data, dicitura di riservatezza.
- Indice con guida a puntini e numeri di pagina reali (vedi doppio passaggio).

Corpo numerato (adattare al quesito):

1. Premessa e incarico, con il QUESITO in elenco puntato.
2. Documentazione esaminata, in elenco puntato degli atti.
3. Metodologia e classificazione delle evidenze, con le classi A/B/C in elenco puntato.
4. Ricostruzione cronologica, in tabella.
5. Accertamenti tecnici, con sotto-sezioni di disamina.
6. Sezioni di merito specifiche del quesito.
N-2. Conclusioni e risposta al quesito, che rispondono in modo puntuale a ciascun quesito.
N-1. Roadmap o raccomandazioni, se pertinente.
N. Riferimenti normativi e tecnici, in elenco puntato.

Chiusura: luogo e data, firmatario. Banda identificativa del committente o autore a pie di pagina su ogni foglio, con "Pag. X di Y".

## Stile (richiama voce-consulenziale-formale)

- Registro formale, terza persona impersonale, periodi controllati, evidenza prima dell'opinione, pragmatismo, coraggio nelle conclusioni. Caricare [[Contesto/tono-di-voce]] e la skill [[Skill/voce-consulenziale-formale]].
- ELENCHI PUNTATI per le enumerazioni di elementi distinti e paralleli (quesito, documentazione esaminata, classi A/B/C, riferimenti, requisiti): mai comprimere in un'unica frase con i due punti seguita da una sequenza separata da punto e virgola. Resta prosa articolata per i ragionamenti. (Regola permanente, 23/05/2026.)

## Regole tipografiche permanenti

- Virgolette dritte "..." sempre, mai caporali.
- "al punto", "al paragrafo", "al comma" sempre, mai il segno di paragrafo.
- Font uniforme nel corpo del documento (es. Arial).
- Niente em-dash decorativi: separatori ammessi virgola, due punti, punto mediano.
- Placeholder italiano professionale: underscore continui per i campi compilabili, "(indicare ...)" per le istruzioni. Mai i marcatori con doppie parentesi angolari.
- A chiusura: sempre /umanizzatore-testi; per i testi normativi /disaiizzatore-testi-tecnici-normativi con report a parte.

## Integrita (non negoziabile)

- Non inventare nulla: ogni tesi ancorata a un'evidenza tracciabile nei documenti.
- Distinguere fatto, valutazione tecnica e opinione.
- Non attestare attivita non eseguite: se non sono state effettuate copia forense bit-stream, calcolo degli hash e catena di custodia, NON dichiararle. La perizia resta autorevole senza false attestazioni; quelle attivita, se servono, vanno prima eseguite.
- Classificare le evidenze per livello di verificabilita (classe A verificabile da chiunque; classe B che richiede interpretazione tecnica; classe C da accesso privilegiato o documentazione di parte) e dichiararlo nella metodologia.
- Tenere internamente, fuori dal documento, le contro-evidenze e i punti di esposizione, e segnalarli all'utente.

## White-label e anonimato

Se il documento esce a firma del cliente: zero riferimenti al consulente reale nel testo E nei metadati del docx (autore, ultimo autore, titolo, societa). Eseguire uno scan finale su testo e su docProps prima della consegna.

## Workflow operativo

1. Raccogli ed estrai il corpus in testo leggibile (i file solo-cloud vanno idratati).
2. Opzionale, solo su richiesta dell'utente: analisi parallela multi-agent del corpus, con subagent di sola ricerca e main agent che scrive (Conv. 33 e 34). Ogni subagent compila una sezione obbligatoria di contro-evidenze.
3. Redigi il contenuto ancorato alle evidenze, applicando struttura, stile e regole.
4. Genera il docx con lo script di riferimento reference/build_perizia_esempio.py: stili e font uniforme, frontespizio, indice a DOPPIO PASSAGGIO per i numeri di pagina, tabelle con bordi e sfondo, banda a pie di pagina, metadati anonimi, elenchi puntati. Adatta i contenuti e l'intestazione; mantieni la meccanica.
5. Verifica: integrita zip, riapertura con python-docx, conversione PDF, scan anonimato e tipografia (em-dash 0, segno di paragrafo 0, caporali 0, virgolette curve 0, font unico), ispezione visiva di frontespizio, indice e di una pagina con elenchi e tabelle.
6. Consegna docx e PDF; segnala i campi da compilare (protocollo, firmatario) e i punti di esposizione residui.

## Doppio passaggio per l'indice numerato

1. Esegui lo script senza il file /tmp/pagemap.json: l'indice viene costruito senza numeri (blocco a numero di righe costante).
2. Converti in PDF, rileva per ogni sezione la pagina dell'ultima occorrenza del titolo (lo split del testo PDF avviene sul carattere di avanzamento pagina), scrivi /tmp/pagemap.json.
3. Riesegui lo script: l'indice viene popolato con i numeri di pagina reali. La paginazione del corpo non cambia perche il blocco indice ha lo stesso numero di righe.

## Script di riferimento

reference/build_perizia_esempio.py e uno script python-docx funzionante (caso reale, perizia post-incidente per un'azienda IT). Da usare come template: si adattano intestazione, soggetto, committente, quesiti e contenuti delle sezioni; si mantiene intatta la meccanica (helpers, frontespizio, indice a doppio passaggio, tabelle, banda a pie di pagina, metadati anonimi, tipografia). Per la conversione PDF in ambiente sandbox usare LibreOffice con HOME e cache reindirizzate su disco con spazio.

## Fonti di verita

- [[Contesto/tono-di-voce]] e [[Skill/voce-consulenziale-formale]] per lo stile
- [[Skill/disaiizzatore-testi-tecnici-normativi]] e [[Skill/umanizzatore-testi]] per la pulizia anti-AI
- [[Skill/docx]] per la produzione Word, [[Skill/clonatore-stile-docx]] per la clonazione di carta intestata
- Skill di dominio per i contenuti tecnico-normativi: [[Skill/audit-iso-27001-sgsi]], [[Skill/audit-iso-9001-sanita]], [[Skill/audit-iso-42001-ai-management]], [[Skill/risk-manager-iso-31000]], [[Skill/rilevazione-incendi-impianti-iaiei]]

## Link correlati

- [[Skill/voce-consulenziale-formale]]
- [[Skill/disaiizzatore-testi-tecnici-normativi]]
- [[Skill/docx]]
- [[Skill/clonatore-stile-docx]]

---
Part of [[Skill/_index]]
