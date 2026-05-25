# Catalogo dei tell AI italiani

Pattern stilistici riconoscibili come tipici della generazione AI in italiano, con sostituzioni e ristrutturazioni adatte al registro tecnico-normativo. Il catalogo è ordinato per frequenza di occorrenza nel corpus dei modelli generativi più diffusi (GPT-4/4o/5, Claude 3.5/4/4.5/4.6, Gemini 2.x).

> **Avvertenza operativa**: ogni voce del catalogo va applicata solo dopo verifica di Fase 2 (Verification Planning). Alcuni pattern *sembrano* AI ma sono formule legittime del registro tecnico-normativo italiano. In caso di dubbio, lasciare invariato.

---

## 1. Enfasi gonfiata sulla significatività

**Pattern**: l'AI tende a "imbottire" di importanza qualunque oggetto descritto, anche quando non serve.

**Spie lessicali**: rappresenta una pietra miliare, costituisce un tassello fondamentale, gioca un ruolo cruciale, riveste un'importanza strategica, si configura come elemento centrale, segna un momento decisivo, rappresenta una svolta, è un punto di riferimento imprescindibile, costituisce la pietra angolare, è il fulcro di, si pone come baricentro.

**Esempio (audit ISO 27001)**:
- ❌ *La gestione degli accessi rappresenta una pietra miliare nel sistema di sicurezza dell'informazione, costituendo un tassello fondamentale per la protezione degli asset.*
- ✅ *La gestione degli accessi è un controllo prioritario del SGSI ai sensi di ISO/IEC 27001:2022 A.5.15.*

---

## 2. Trittici sinonimici (regola del tre)

**Pattern**: tre aggettivi o sostantivi in fila, spesso semanticamente sovrapposti.

**Spie**: efficace, efficiente ed efficace · solido, robusto e affidabile · chiaro, trasparente e comprensibile · strutturato, organico e coerente · completo, esaustivo e dettagliato · proattivo, dinamico e reattivo.

**Regola**: ridurre a uno o due termini distinti. Se i tre termini sono effettivamente diversi, mantenerli; se sono sinonimi, scegliere quello più preciso.

**Esempio**:
- ❌ *Il piano di trattamento del rischio risulta solido, robusto e affidabile.*
- ✅ *Il piano di trattamento del rischio è strutturato e tracciabile.*

---

## 3. Frasi participiali pseudo-analitiche (-ando/-endo finali)

**Pattern**: tipico di GPT/Claude in italiano. Una frase principale chiusa, poi un gerundio che aggiunge "profondità apparente".

**Spie**: ...garantendo al contempo... · ...assicurando in tal modo... · ...favorendo così... · ...promuovendo nel contempo... · ...consolidando di fatto... · ...rafforzando ulteriormente...

**Regola**: separare in due frasi indipendenti, oppure eliminare il gerundio se non aggiunge informazione.

**Esempio (procedura ISO 9001)**:
- ❌ *L'Ente effettua il riesame della Direzione con cadenza annuale, garantendo al contempo il monitoraggio continuo dell'efficacia del SGQ e favorendo così il miglioramento.*
- ✅ *L'Ente effettua il riesame della Direzione con cadenza annuale. Gli esiti alimentano il piano di miglioramento del SGQ.*

---

## 4. Parallelismi negativi ("non solo… ma anche")

**Pattern**: costruzione antitetica per dare ritmo artificiale.

**Spie**: non solo X, ma anche Y · non si limita a X, ma estende a Y · va oltre la mera X per abbracciare Y · non è semplicemente X, è Y.

**Regola**: rimuovere la struttura antitetica. Affermare direttamente.

**Esempio (DDV)**:
- ❌ *La policy di sicurezza non si limita a definire i comportamenti attesi, ma stabilisce anche i meccanismi sanzionatori.*
- ✅ *La policy di sicurezza definisce i comportamenti attesi e i relativi meccanismi sanzionatori.*

---

## 5. Connettori AI ad alta densità

**Pattern**: l'AI usa connettivi di transizione molto più di un autore italiano. La densità è il vero marker, non il singolo connettivo.

**Spie**: inoltre · pertanto · in tal senso · al contempo · parallelamente · di conseguenza · in aggiunta · va sottolineato che · è opportuno evidenziare che · risulta peraltro che · in ultima analisi · in definitiva.

**Regola**: dimezzare la frequenza. Tenere solo i connettivi che svolgono una funzione logica reale (causa, opposizione, conclusione). Eliminare quelli puramente decorativi.

---

## 6. Verbi-fantasma (copula avoidance)

**Pattern**: l'AI evita "è/sono/ha" preferendo perifrasi.

**Spie**: si configura come · si pone come · risulta essere · viene a costituire · assume i contorni di · si presenta come · si caratterizza per essere · viene a delinearsi come.

**Regola**: sostituire con il verbo essere/avere/diventare appropriato.

**Esempio**:
- ❌ *Il controllo A.8.16 si configura come un elemento critico del SGSI.*
- ✅ *Il controllo A.8.16 è critico per il SGSI.*

---

## 7. Nominalizzazioni a catena

**Pattern**: trasformare verbi in nomi astratti, concatenati con preposizioni.

**Spie**: l'implementazione della valutazione del trattamento dei rischi · l'attivazione del processo di gestione delle non conformità · la definizione delle modalità di esecuzione delle verifiche.

**Regola**: tornare ai verbi quando possibile. Le nominalizzazioni sono ammesse nel registro normativo, ma non in catena.

**Esempio**:
- ❌ *Si è proceduto all'implementazione dell'attivazione del processo di gestione delle segnalazioni.*
- ✅ *Il processo di gestione delle segnalazioni è stato attivato.*

---

## 8. Hedging eccessivo

**Pattern**: accumulo di marcatori di incertezza dove l'autore tecnico sarebbe netto.

**Spie**: potrebbe potenzialmente · sembrerebbe possibile che · in linea di massima si potrebbe ipotizzare · pare verosimile che · potenzialmente in alcuni casi.

**Regola**: una sola modulazione per claim. Nei DDV e nelle perizie CTU, l'hedging si esprime con formule tipizzate ("non risulta", "non è stato possibile verificare", "a parere dello scrivente"), non con accumulo di avverbi.

---

## 9. Conclusioni generiche positive

**Pattern**: chiusura con frase motivazionale generica che non aggiunge valore.

**Spie**: in conclusione, il percorso intrapreso si presenta promettente · le prospettive appaiono incoraggianti · la strada è tracciata · si auspica un ulteriore consolidamento · ci si attende che i benefici si materializzino · il futuro appare luminoso.

**Regola**: chiudere sull'evidenza più forte o sulla raccomandazione operativa più rilevante. Mai chiudere con un augurio.

**Esempio (gap analysis)**:
- ❌ *In conclusione, l'Ente ha intrapreso un percorso promettente verso la conformità NIS2 e le prospettive appaiono incoraggianti.*
- ✅ *La chiusura dei 4 gap di Priorità 1 entro Q3 2026 è prerequisito per il rispetto dei termini di adeguamento NIS2 (Art. 41 D.Lgs. 138/2024).*

---

## 10. Em dash al posto della punteggiatura italiana

**Pattern**: l'em dash è il marker più riconoscibile. L'italiano scritto formale non lo usa quasi mai. Anche il trattino lungo intercalato è raro nei testi tecnici.

**Regola**: sostituire **sempre** con virgole, parentesi tonde, punto e virgola, due punti, o spezzando in due frasi.

**Esempio**:
- ❌ *La gestione del rischio — disciplinata da ISO 31000 — costituisce un riferimento metodologico.*
- ✅ *La gestione del rischio, disciplinata da ISO 31000, costituisce un riferimento metodologico.*

---

## 11. Bold semantico ed enfasi tipografica diffusa

**Pattern**: l'AI evidenzia in **grassetto** parole chiave dentro paragrafi prosastici. Non è uso italiano formale.

**Regola**: rimuovere ogni grassetto inline nei paragrafi discorsivi. Mantenere il grassetto solo per: titoli di sezione, intestazioni di tabelle, etichette di campi (es. "**Scopo:**", "**Ambito:**" all'inizio di una procedura).

---

## 12. Riassuntini ricorsivi ("come abbiamo visto")

**Pattern**: l'AI riassume sé stessa a metà testo o all'inizio di ogni sezione.

**Spie**: come accennato in precedenza · come anticipato sopra · ricapitolando quanto detto · riprendendo il filo · alla luce di quanto esposto finora · come emerso dai paragrafi precedenti.

**Regola**: rimuovere. Il lettore tecnico ha appena letto: non serve riassumerglielo. Eccezione: in documenti molto lunghi (>20 pagine) un richiamo esplicito è ammesso.

---

## 13. Liste a tre voci con parallelismo perfetto

**Pattern**: bullet list dove ogni voce inizia con un verbo all'infinito o con una nominalizzazione, sempre della stessa lunghezza, sempre tre.

**Esempio**:
- ❌
  - Garantire la conformità
  - Assicurare la tracciabilità
  - Promuovere il miglioramento

**Regola**: nei documenti tecnici la lista deve essere giustificata dal contenuto, non dall'estetica. Se i tre punti sono genuinamente distinti, vanno bene; se sono parafrasi dello stesso concetto, accorparli in un periodo.

---

## 14. Formule meta-discorsive

**Pattern**: l'AI commenta il proprio testo.

**Spie**: è importante notare che · vale la pena sottolineare che · merita evidenziare come · si ritiene opportuno precisare che · è doveroso menzionare che · non si può non rilevare che.

**Regola**: rimuovere e affermare direttamente. Se la cosa è importante, l'importanza emerge dal merito, non dall'etichetta.

**Esempio**:
- ❌ *È importante notare che l'assenza di MFA su accessi privilegiati configura una non conformità maggiore.*
- ✅ *L'assenza di MFA su accessi privilegiati configura NC_I rispetto a ISO/IEC 27001:2022 A.5.17.*

---

## 15. Aggettivi "di catalogo" promozionali

**Pattern**: aggettivi che descrivono qualunque cosa come desiderabile.

**Spie**: olistico · sinergico · proattivo · resiliente · innovativo · all'avanguardia · best-in-class · cutting-edge · di nuova generazione · di ultima generazione · di eccellenza · ottimale.

**Regola**: nel registro tecnico-normativo questi aggettivi sono quasi sempre rumore. Eliminarli o sostituirli con un dato concreto.

**Esempio**:
- ❌ *L'Ente ha implementato un approccio olistico e proattivo alla gestione del rischio.*
- ✅ *L'Ente ha adottato un processo di gestione del rischio conforme a ISO 31000:2018 con riesame trimestrale del registro rischi.*

---

## 16. "Il presente documento si propone di..."

**Pattern**: apertura tipica AI nelle premesse di documento.

**Spie**: il presente documento si propone di · l'obiettivo del presente lavoro è quello di · scopo del presente paragrafo è · attraverso il presente elaborato si intende.

**Regola**: nello stile consulenziale formale si apre con il fatto, non con la dichiarazione di intenti. "La presente nota tecnica documenta…" oppure "Questa procedura definisce…".

---

## 17. Doppia negazione enfatica

**Pattern**: "non si può non...", "non è raro che...", "non manca chi sostenga...".

**Regola**: scioglierla in affermazione positiva.

---

## 18. Citazioni vaghe di "esperti" e "studi"

**Pattern**: "secondo gli esperti del settore", "diversi studi hanno dimostrato", "è opinione condivisa che", "molti professionisti ritengono".

**Regola**: nel registro tecnico-normativo si cita la fonte (norma, linea guida, autore), oppure si dichiara l'opinione come propria ("a parere dello scrivente"). Mai attribuzioni vaghe.

---

## 19. Uso di "mero/a" e "in essere"

**Pattern**: due marker semi-burocratici amati dall'AI.

- *Una mera formalità* → *una formalità*
- *Le procedure in essere* → *le procedure vigenti / le procedure attuali*

(Non sono errori, ma sono in alta sovra-rappresentazione nei testi AI.)

---

## 20. Uso ridondante di "stesso/medesimo"

**Pattern**: "il documento e i suoi allegati al medesimo"; "la procedura e l'attuazione della stessa".

**Regola**: pronome o ripetizione semplice. *La procedura e la sua attuazione*.

---

## Pattern strutturali (non lessicali)

### 21. Paragrafi tutti della stessa lunghezza
L'AI tende a produrre paragrafi calibrati (4–6 righe ciascuno). I testi umani hanno varianza maggiore. **Regola**: variare ritmicamente. Un paragrafo di una riga è ammesso e talvolta efficace.

### 22. Strutture sempre tripartite
Ogni sezione ha 3 sottosezioni, ogni elenco 3 voci, ogni argomento 3 angolazioni. **Regola**: il numero di sottosezioni segue il merito, non l'estetica.

### 23. Apertura + corpo + chiusura ridondanti per ogni sezione
Ogni sezione ha una mini-premessa e una mini-conclusione. **Regola**: nel registro tecnico, si entra direttamente nel merito. La premessa metodologica è una sola, all'inizio del documento.

### 24. Tabelle a 3 colonne uniformi
Spesso AI-generated. **Regola**: la struttura della tabella deve riflettere il dato, non un template estetico.

---

## Calibrazioni specifiche per tipologia di documento

### Procedure ISO
- Mantenere le sezioni canoniche (Scopo, Campo di applicazione, Riferimenti, Definizioni, Responsabilità, Modalità operative, Registrazioni, Riesame)
- Tono impersonale obbligatorio
- Verbi al presente indicativo
- Numerazione gerarchica
- Tell AI tipici da rimuovere: gerundi finali (#3), "garantendo" (#3), "approccio olistico" (#15), riassuntini (#12)

### Relazioni di audit (DDV/RVE)
- Mantenere classificazione esatta dei rilievi (NC_I, NC_II, SM, Osservazione)
- Preservare la formula "non risulta evidenza di" (è whitelist)
- Eliminare hedging eccessivo (#8) e meta-discorso (#14)
- Mai attenuare un rilievo in fase di riscrittura

### Gap analysis
- Mantenere le tabelle gap → remediation invariate nei dati
- Eliminare le righe descrittive con conclusioni generiche positive (#9)
- Le priorità (Alta/Media/Bassa) o (P1/P2/P3) sono whitelist

### Perizie CTU
- Formule tipizzate processuali = whitelist assoluta
- Sezioni standard ("operazioni peritali", "risposta al quesito") = whitelist strutturale
- Eliminare aggettivi promozionali (#15) e enfasi gonfiata (#1)
- Mantenere il "sottoscritto perito" e simili

---

## Note finali

Questo catalogo non è esaustivo. I modelli generativi evolvono e i tell cambiano nel tempo. Quando incontri un pattern non catalogato che ti sembra AI, applica il **test del consulente esperto**: un Lead Auditor italiano con 15 anni di esperienza scriverebbe così? Se la risposta è no, considera la riscrittura. Se la risposta è "potrebbe", lascia stare.
