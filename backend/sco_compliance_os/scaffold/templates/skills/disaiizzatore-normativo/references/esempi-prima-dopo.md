# Esempi prima/dopo — calibrati su ISO, audit, gap analysis, perizie CTU

Casi reali del corpus tipico di Antonio Silvestro Amodeo. Ogni esempio mostra:
1. **Versione AI** (con i tell evidenziati)
2. **Versione deaiizzata** (stile-target Amodeo)
3. **Note di revisione** (cosa è cambiato e perché)

---

## Esempio 1 — Procedura ISO 27001 (Scopo)

### Versione AI
> Il presente documento si propone di definire in maniera chiara, strutturata e organica le modalità operative attraverso le quali l'organizzazione gestisce gli accessi logici ai propri sistemi informativi, garantendo al contempo il rispetto dei requisiti normativi applicabili e promuovendo una cultura della sicurezza che permea ogni livello dell'azienda. **L'obiettivo** è quello di assicurare un approccio olistico, proattivo e resiliente alla gestione delle identità digitali, configurando un sistema solido, robusto e affidabile.

### Versione deaiizzata
> La presente procedura definisce le modalità di gestione degli accessi logici ai sistemi informativi aziendali, in attuazione del controllo A.5.15 di ISO/IEC 27001:2022. Si applica a tutti gli utenti, interni ed esterni, che accedono ai sistemi nel perimetro del SGSI.

### Note di revisione
- Eliminato "il presente documento si propone di" (#16)
- Eliminato trittico "chiara, strutturata e organica" (#2)
- Eliminato gerundio finale "garantendo al contempo… promuovendo" (#3)
- Eliminato secondo trittico "olistico, proattivo e resiliente" (#15)
- Eliminato terzo trittico "solido, robusto e affidabile" (#2)
- Aggiunto riferimento puntuale al controllo (precisione normativa)
- Aggiunto perimetro di applicazione (struttura procedura ISO standard)

---

## Esempio 2 — Rilievo di audit (DDV)

### Versione AI
> In sede di audit è emerso che l'organizzazione, pur avendo implementato un approccio strutturato e all'avanguardia alla gestione degli accessi privilegiati, presenta alcune aree di miglioramento che meritano di essere evidenziate. **È importante notare** che, sebbene il sistema sia in linea di massima conforme ai requisiti, l'assenza di un meccanismo di autenticazione a più fattori per gli account amministrativi potrebbe potenzialmente esporre l'organizzazione a rischi significativi, configurando una situazione che andrebbe sanata — anche tenendo conto del contesto operativo — al fine di rafforzare ulteriormente la postura di sicurezza complessiva.

### Versione deaiizzata
> Non risulta evidenza dell'attivazione di meccanismi di autenticazione a più fattori (MFA) sugli account amministrativi dei sistemi `<sistema>`. La condizione è in contrasto con il controllo A.5.17 di ISO/IEC 27001:2022 e con l'Art. 21, comma 2, lett. d) del D.Lgs. 138/2024, che richiede misure rafforzate di autenticazione per gli accessi privilegiati ai soggetti essenziali e importanti. **Classificazione: NC_I.**

### Note di revisione
- Eliminato preambolo meta-discorsivo "in sede di audit è emerso che" (#14, è ammesso ma qui ridondante con la classificazione)
- Eliminato "approccio strutturato e all'avanguardia" (#15)
- Eliminato "aree di miglioramento che meritano di essere evidenziate" (#14)
- Eliminato hedging "in linea di massima… potrebbe potenzialmente" (#8)
- Eliminato em dash (#10)
- Eliminato gerundio "configurando" (#3)
- Eliminato finale generico "rafforzare ulteriormente la postura" (#9)
- **Cruciale**: il rilievo è stato espresso in forma più nitida e netta, **mantenendo la stessa gravità** (NC_I). Non si è attenuato.

---

## Esempio 3 — Gap analysis (sezione descrittiva)

### Versione AI
> L'analisi della maturità cyber dell'Ente ha permesso di evidenziare un quadro complessivo che, pur presentando aree di forza significative, mostra parallelamente alcune lacune che meritano un'attenta riflessione. In tal senso, è possibile osservare come l'Ente abbia investito proattivamente in soluzioni innovative di endpoint protection — dimostrando una visione lungimirante — ma al contempo non risulti aver consolidato adeguatamente i processi di gestione degli incidenti, configurando una situazione di asimmetria che andrebbe sanata. Inoltre, **vale la pena sottolineare** come la mancanza di un piano di continuità operativa formalizzato rappresenti una pietra miliare mancante nel percorso verso la conformità NIS2, costituendo un tassello fondamentale che dovrà essere affrontato con priorità, garantendo così un approccio organico alla resilienza.

### Versione deaiizzata
> L'analisi restituisce un quadro asimmetrico. L'Ente dispone di soluzioni di endpoint protection di mercato (EDR), ma non ha formalizzato i processi di gestione degli incidenti né un piano di continuità operativa.
>
> L'assenza di BCP è un gap di Priorità 1 ai fini NIS2: l'Art. 21, comma 2, lett. c) del D.Lgs. 138/2024 richiede misure di continuità operativa per i soggetti essenziali. La rimediazione di questo gap è prerequisito per la chiusura dei rilievi di compliance entro il termine di adeguamento.

### Note di revisione
- Eliminato "ha permesso di evidenziare un quadro complessivo che, pur presentando…" (#1, #14)
- Eliminato "in tal senso" (#5)
- Eliminato "proattivamente in soluzioni innovative" (#15)
- Eliminato em dash "dimostrando una visione lungimirante" (#10, #15)
- Eliminato "configurando una situazione di asimmetria" (#3, #6)
- Eliminato "vale la pena sottolineare" (#14)
- Eliminato "rappresenti una pietra miliare mancante… tassello fondamentale" (#1)
- Eliminato gerundio finale "garantendo così un approccio organico" (#3, #15)
- **Aggiunto**: riferimento normativo puntuale (Art. 21, comma 2, lett. c)
- **Aggiunto**: dichiarazione di priorità con conseguenza operativa (stile Amodeo: ogni analisi sfocia in un'azione)

---

## Esempio 4 — Conclusioni di una relazione

### Versione AI
> In conclusione, alla luce di quanto esposto nel corso della presente relazione, è possibile affermare con ragionevole certezza che l'Ente ha intrapreso un percorso virtuoso e promettente verso la piena conformità alle disposizioni normative applicabili. Le prospettive appaiono incoraggianti e, sebbene permangano alcune aree di miglioramento, la strada è tracciata e i benefici dell'investimento in sicurezza dovrebbero materializzarsi nei prossimi mesi, contribuendo così al rafforzamento della postura complessiva e al consolidamento della resilienza organizzativa.

### Versione deaiizzata
> Lo stato attuale dell'Ente presenta progressi misurabili nelle funzioni Identify e Protect del NIST CSF 2.0. Le aree critiche restano la capacità di Detect (assenza di SOC/SIEM operativo) e di Recover (BCP non formalizzato, RPO non testato). La chiusura dei 6 gap di Priorità 1 entro il 30/09/2026 è condizione necessaria per il rispetto del termine di adeguamento NIS2 di cui all'Art. 41 del D.Lgs. 138/2024.

### Note di revisione
- Eliminato "in conclusione, alla luce di quanto esposto" (#9, #12)
- Eliminato "percorso virtuoso e promettente" (#9, #15)
- Eliminato "le prospettive appaiono incoraggianti" (#9)
- Eliminato "la strada è tracciata" (#9)
- Eliminato "benefici dovrebbero materializzarsi" (#9)
- Eliminato gerundio finale "contribuendo così al rafforzamento" (#3)
- **Aggiunto**: misurazione concreta (funzioni NIST CSF, numero gap, scadenza)
- **Aggiunto**: ancoraggio normativo (Art. 41 D.Lgs. 138/2024)
- **Stile Amodeo**: la chiusura ora "morde" ed è operativa

---

## Esempio 5 — Perizia CTU (frammento metodologico)

### Versione AI
> Il sottoscritto perito incaricato, al fine di rispondere in maniera esaustiva e completa al quesito posto dall'Ill.mo Magistrato, ha proceduto all'implementazione di una metodologia di analisi forense che si configura come solida, robusta e all'avanguardia, garantendo al contempo il pieno rispetto degli standard internazionali in materia di digital forensics e assicurando la perfetta riproducibilità dei risultati ottenuti, nel pieno rispetto della catena di custodia delle evidenze digitali acquisite.

### Versione deaiizzata
> Il sottoscritto perito incaricato, in risposta al quesito posto dall'Ill.mo Magistrato, ha condotto le operazioni peritali secondo la metodologia prevista dalle linee guida ISO/IEC 27037:2012 (identification, collection, acquisition and preservation of digital evidence) e ISO/IEC 27042:2015 (analysis and interpretation of digital evidence). La catena di custodia è documentata nell'Allegato A. Le operazioni di acquisizione e analisi sono riproducibili a partire dalle copie forensi conservate presso lo scrivente, i cui hash SHA-256 sono riportati nell'Allegato B.

### Note di revisione
- Mantenuto "Il sottoscritto perito incaricato" (whitelist CTU)
- Mantenuto "Ill.mo Magistrato" (whitelist CTU)
- Eliminato "in maniera esaustiva e completa" (#2)
- Eliminato "ha proceduto all'implementazione di una metodologia" (#7)
- Eliminato "si configura come" (#6)
- Eliminato trittico "solida, robusta e all'avanguardia" (#2, #15)
- Eliminato gerundio "garantendo al contempo… assicurando" (#3)
- **Aggiunto**: riferimenti normativi puntuali (ISO/IEC 27037, ISO/IEC 27042)
- **Aggiunto**: rinvio agli allegati (struttura peritale standard)
- **Aggiunto**: hash SHA-256 → tracciabilità tecnica (sostituisce le frasi vuote sulla catena di custodia con un dato concreto)

---

## Esempio 6 — Email a cliente (registro formale leggero)

### Versione AI
> Gentilissimo Dott. Rossi,
>
> spero che questa mia email La trovi bene. Le scrivo per aggiornarLa in merito allo stato di avanzamento del progetto di adeguamento NIS2, che sta procedendo in maniera estremamente positiva. **Sono lieto di comunicarLe** che, a seguito delle attività svolte nelle ultime settimane, abbiamo raggiunto importanti traguardi che meritano di essere condivisi.
>
> In particolare, vorrei sottolineare come il team abbia lavorato instancabilmente per garantire il pieno rispetto delle scadenze concordate, dimostrando un impegno encomiabile e un approccio sinergico che ha permesso di superare le sfide incontrate lungo il percorso.
>
> Resto a Sua completa disposizione per qualsiasi chiarimento dovesse necessitare e La ringrazio anticipatamente per l'attenzione che vorrà dedicare alla presente comunicazione.
>
> Cordiali saluti

### Versione deaiizzata
> Buongiorno Dott. Rossi.
>
> Aggiornamento sullo stato del progetto NIS2 al 08/04/2026:
>
> 1. **Gap analysis** completata. Identificati 12 gap (4 Priorità 1, 6 Priorità 2, 2 Priorità 3).
> 2. **Piano di rimediazione** in bozza. Trasmissione per revisione entro venerdì 11/04.
> 3. **Riunione di allineamento** proposta per martedì 15/04 ore 10:00 (modalità da concordare).
>
> Resto disponibile per chiarimenti.

### Note di revisione
- Eliminato "Gentilissimo" → "Buongiorno" (regola Amodeo registro formale leggero)
- Eliminato "spero che questa mia email La trovi bene" (#14, filler)
- Eliminato "estremamente positiva", "importanti traguardi che meritano di essere condivisi" (#1, #9)
- Eliminato "vorrei sottolineare come il team… instancabilmente… approccio sinergico" (#15)
- Eliminato "ringrazio anticipatamente per l'attenzione che vorrà dedicare" (filler)
- **Restituita** struttura Amodeo: contesto sintetico → 3 punti numerati → chiusura asciutta
- **Aggiunti** dati concreti (numero gap, date, orari)

---

## Esempio 7 — Sezione che NON va modificata (whitelist)

### Versione originale
> Ai sensi e per gli effetti dell'Art. 21, comma 2, lett. b) del D.Lgs. 138/2024, i soggetti essenziali e importanti adottano misure tecniche, operative e organizzative adeguate e proporzionate per gestire i rischi posti alla sicurezza dei sistemi informatici e di rete che tali soggetti utilizzano nelle loro attività.

### Decisione del disaiizzatore
**NON MODIFICARE.**

### Motivazione
- Citazione di articolo di legge → whitelist normativa #1
- "Ai sensi e per gli effetti" → formula tipizzata
- "Misure tecniche, operative e organizzative" → trittico **legittimo** perché riproduce il testo normativo (le tre categorie sono distinte e previste dalla norma)
- "Adeguate e proporzionate" → coppia tipizzata della normativa NIS2
- Anche se il paragrafo "sembra" pesante, è una citazione formale che va lasciata identica.

---

## Principi che emergono dagli esempi

1. **La deaiizzazione spesso accorcia, ma a volte allunga**: rimpiazzare frasi vuote con dati concreti può aumentare la lunghezza. L'obiettivo è la densità informativa, non la brevità.
2. **I rilievi di audit non si attenuano mai**: spesso la deaiizzazione li rende *più* nitidi e diretti, non più morbidi.
3. **Aggiungere riferimenti normativi precisi è spesso parte della deaiizzazione**: l'AI tende a parlare in generale, lo stile tecnico-normativo italiano è puntuale.
4. **Rimuovere un gerundio finale è quasi sempre un miglioramento**: è il singolo tell più frequente.
5. **Le formule di registro non sono tell**: "non risulta evidenza di", "ai sensi e per gli effetti", "il sottoscritto perito" sono whitelist.
