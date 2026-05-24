# Comandi Rapidi — SGQ-RSPP-Sanità

## Comandi dominio SGQ (Qualità ISO 9001)

| Comando | Input atteso | Output |
|---|---|---|
| `/procedura [tema]` | Tema della procedura (es. "gestione NC", "audit interni", "gestione documentale") | Bozza procedura gestionale (PG) o operativa (PO) completa: scopo, campo applicazione, responsabilità, modalità operative, indicatori, registrazioni, riferimenti normativi |
| `/protocollo [tema]` | Tema clinico-organizzativo (es. "somministrazione farmaci", "prevenzione cadute", "igiene mani") | Bozza protocollo clinico-organizzativo (PR): obiettivo, popolazione target, evidenze scientifiche/LG, sequenza azioni, responsabilità, indicatori, revisione |
| `/istruzione [tema]` | Attività specifica (es. "prelievo venoso", "cambio catetere", "taratura phmetro") | Bozza istruzione operativa (IO): scopo, materiali, sequenza passi dettagliati, punti di attenzione, registrazioni |
| `/politica` | (nessun input specifico, opzionale: tipo struttura) | Bozza politica per la qualità: impegno direzione, principi, obiettivi strategici, comunicazione |
| `/manuale [struttura]` | Tipo struttura (es. "ospedale pubblico 200 PL", "poliambulatorio privato accreditato") | Struttura completa manuale qualità: indice dettagliato, contenuto per clausola ISO 9001, scope, mappa processi |
| `/mappa-processi` | (opzionale: tipo struttura, servizi) | Mappa processi sanitari con classificazione (primari/supporto/gestionali), interazioni, process owner, indicatori chiave |
| `/indicatori [area]` | Area clinica o organizzativa (es. "chirurgia", "laboratorio", "degenza medica", "customer satisfaction") | Set indicatori/KPI: nome, formula, fonte dati, frequenza rilevazione, target, responsabile, benchmark |
| `/riesame` | (opzionale: tipo struttura) | Struttura riesame di direzione sanitario: input richiesti, agenda, partecipanti, template output decisionale |
| `/risk [processo]` | Processo sanitario (es. "somministrazione terapia", "identificazione paziente", "sterilizzazione") | Analisi rischi: identificazione pericoli, FMEA/matrice rischio, valutazione P×I, misure mitigazione, rischio residuo |
| `/gap [regione]` | Regione (es. "Veneto", "Calabria", "Lazio") | Gap analysis SGQ vs. requisiti accreditamento regionali: checklist requisiti, stato conformità, azioni per colmare gap |
| `/pdta [patologia/percorso]` | Patologia o percorso (es. "scompenso cardiaco", "ictus", "chirurgia protesica anca") | Struttura PDTA: inquadramento clinico, criteri inclusione, fasi percorso, attori, tempi, indicatori esito, LG di riferimento |
| `/carta-servizi [struttura]` | Tipo struttura | Struttura carta dei servizi: presentazione, servizi offerti, impegni qualità, standard, meccanismi tutela, URP |
| `/formazione [tema]` | Tema formativo (es. "approccio per processi", "risk management", "audit interni", "PDCA") | Piano formativo / materiale didattico qualità: obiettivi, contenuti, durata, destinatari, metodologia, valutazione |
| `/linee-guida [tema]` | Tema clinico (es. "sepsi", "dolore post-operatorio", "prevenzione TVP") | Ricerca e sintesi LG SNLG e società scientifiche pertinenti: titolo, fonte, data, stato, raccomandazioni chiave |

## Comandi dominio Sicurezza (D.Lgs. 81/08)

| Comando | Input atteso | Output |
|---|---|---|
| `/dvr [area/reparto]` | Area o reparto (es. "blocco operatorio", "laboratorio analisi", "degenza medicina") | Sezione DVR per area: identificazione rischi, valutazione, misure in atto, misure programmate, rischio residuo |
| `/duvri [appalto]` | Tipo appalto/servizio (es. "pulizie", "manutenzione impianti elevatori", "service apparecchiature biomediche") | DUVRI: descrizione lavori, rischi interferenziali, misure coordinamento, costi sicurezza, responsabilità |
| `/rischio [tipo]` | Tipo rischio (es. "biologico", "chimico", "MMC", "stress", "radiazioni", "incendio", "aggressioni") | Valutazione rischio specifico: identificazione pericoli, metodo valutazione, esposizione, misure, monitoraggio |
| `/emergenza [struttura]` | Tipo struttura (opzionale: dimensioni, piani) | Piano emergenza ed evacuazione: scenari, procedure, planimetrie indicazioni, squadre, punti raccolta, evacuazione assistita |
| `/formazione-sicurezza` | (opzionale: profili/mansioni specifiche) | Piano formativo sicurezza conforme Accordo SR 17/4/2025: corsi, destinatari, durata, contenuti, scadenze, registro |
| `/dpi [area/mansione]` | Area o mansione (es. "infermiere degenza", "tecnico laboratorio", "addetto pulizie") | Selezione DPI: tipo, norma EN, marcatura, criteri scelta, frequenza sostituzione, addestramento |
| `/appalti [servizio]` | Servizio appaltato (es. "ristorazione", "lavanderia", "manutenzione edile") | Gestione sicurezza appalti: verifica idoneità, DUVRI, coordinamento, vigilanza, costi sicurezza |
| `/sorveglianza [mansione]` | Mansione (es. "infermiere", "medico radiologo", "OSS", "tecnico laboratorio") | Protocollo sorveglianza sanitaria: rischi per mansione, accertamenti, periodicità, vaccinazioni, idoneità |
| `/piano-miglioramento` | (opzionale: area/priorità) | Programma misure prevenzione e protezione: azioni, priorità, tempi, risorse, responsabile, indicatore completamento |
| `/checklist-81 [area]` | Area (es. "laboratorio", "blocco operatorio", "uffici", "cucina") | Checklist conformità D.Lgs. 81/08 per area: requisiti, articoli di riferimento, conforme/non conforme, note |
| `/procedura-sicurezza [tema]` | Tema (es. "gestione taglienti", "spillamento antiblastici", "accesso aree confinate") | Procedura o istruzione operativa di sicurezza (SIC-PO/SIC-IO): scopo, rischi, misure, DPI, emergenza, registrazioni |
| `/riunione-periodica` | (nessun input specifico) | Template verbale riunione periodica art. 35: OdG, partecipanti, punti discussione, decisioni, azioni |

## Comandi CoVe (trasversali)

| Comando | Funzione |
|---|---|
| `/cove` | Report CoVe completo (4 fasi) per l'ultima risposta prodotta |
| `/cove-check [claim]` | Verifica esplicita su un singolo claim specifico |
| `/cove-report` | Report sintetico: lista claim con esito V/I/E/NV |

## Note operative sui comandi

- I comandi possono essere combinati con contesto aggiuntivo: `/dvr blocco operatorio — ospedale pubblico 300 PL, Regione Veneto`
- Per ogni comando, la skill chiede le informazioni mancanti necessarie prima di produrre l'output
- Ogni output è auto-verificato tramite CoVe prima della consegna
- Output sempre in formato .docx con codifica documentale conforme alla gerarchia
- Comandi SGQ producono documenti con prefisso PG/PO/PR/IO/MOD
- Comandi Sicurezza producono documenti con prefisso SIC-PG/SIC-PO/SIC-IO
