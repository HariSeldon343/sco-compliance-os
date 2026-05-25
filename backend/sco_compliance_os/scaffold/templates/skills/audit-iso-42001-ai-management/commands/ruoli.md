---
description: "Matrice ruoli AIMS ↔ ruoli AI Act"
---

# /ruoli — Matrice ruoli AIMS ↔ ruoli AI Act

## Uso
`/ruoli [organizzazione]`

## Quando
Quando occorre mappare il/i ruolo/i regolatorio/i del soggetto sia sulla tassonomia ISO 42001 sia sulla tassonomia AI Act. Essenziale prima di definire obblighi, documentazione richiesta, autorità competenti.

## Tassonomia ISO 42001 (DOC-005 §4.1 Nota 1)

6 categorie macro:

1. **AI providers** — organizzazioni che forniscono prodotti o servizi IA.
2. **AI producers** — chi sviluppa, integra, progetta, testa, distribuisce. Si articola in 11 sottoruoli: AI developer, AI designer, AI tester, AI operator, AI impact assessor, AI procurer, AI integrator, AI data provider, AI governance/oversight professional, AI human factors professional, AI domain expert.
3. **AI customers** — utilizzatori del sistema IA.
4. **AI partners** — collaboratori lungo la catena del valore (subfornitori, integratori).
5. **AI subjects** — persone/entità sui cui dati il sistema opera o che subiscono gli output.
6. **Autorità competenti** — regolatori e organismi di vigilanza.

## Tassonomia AI Act (Art. 3)

- **Fornitore** (Art. 3 n. 3): persona fisica/giuridica che sviluppa o fa sviluppare un sistema IA e lo immette sul mercato o lo mette in servizio con il proprio nome/marchio.
- **Deployer** (Art. 3 n. 4): utilizzatore di un sistema IA sotto la propria autorità, salvo uso personale non professionale.
- **Importatore** (Art. 3 n. 6): stabilito nell'UE, immette sul mercato un sistema IA recante il nome di un soggetto extra-UE.
- **Distributore** (Art. 3 n. 7): operatore diverso da fornitore/importatore che mette a disposizione sul mercato UE.
- **Rappresentante autorizzato** (Art. 3 n. 5): persona nell'UE con mandato scritto di un fornitore extra-UE.
- **Produttore del prodotto** (Art. 3 n. 8): chi immette sul mercato un prodotto con sistema IA integrato come componente di sicurezza.

## Matrice di mapping (modello di output)

| Ruolo regolatorio AI Act | Ruolo/i ISO 42001 tipici | Obblighi principali | Documentazione richiesta |
|--------------------------|--------------------------|---------------------|---------------------------|
| Fornitore di sistema ad alto rischio | AI provider + AI producer (developer, tester, integrator) | Art. 9-17: RMS, data governance, documentazione tecnica, log, trasparenza, sorveglianza umana, accuratezza, QMS, conservazione documenti; Art. 40 standard armonizzati; Art. 43 valutazione conformità; CE marking; registrazione EUDB | Documentazione tecnica ex Allegato IV, dichiarazione UE di conformità, policy QMS, piano post-market monitoring, procedura incidenti gravi |
| Deployer (pubblico o servizi essenziali) | AI customer | Art. 26: uso conforme alle istruzioni, sorveglianza umana, dati di input pertinenti, log retention; Art. 27 FRIA | Istruzioni d'uso, log conservati, FRIA compilato, informativa a soggetti esposti |
| Importatore | AI partner | Art. 23: verifica CE marking, conformità, documentazione, rappresentante autorizzato, conservazione dichiarazione UE 10 anni | Registro verifiche, dichiarazione UE conservata |
| Distributore | AI partner | Art. 24: verifica CE marking, istruzioni d'uso, conservazione condizioni ambientali; cooperazione con autorità | Registro verifiche |
| Rappresentante autorizzato | AI producer (oversight professional) | Art. 22: mandato scritto, conservazione documentazione 10 anni, cooperazione autorità, notifica non conformità | Mandato scritto, documentazione conservata |
| Produttore del prodotto con IA integrata | AI producer + AI integrator | Art. 25: obblighi da fornitore se il sistema è immesso con proprio marchio | Come fornitore |

## Regole operative

- Un soggetto può cumulare più ruoli (es. sviluppatore di un LLM proprio + deployer del proprio LLM nei suoi processi). In questo caso elenca tutti i fasci di obblighi sommati.
- Un deployer che apporta modifiche sostanziali al sistema IA diventa fornitore (Art. 25 c. 1).
- Se il fornitore è extra-UE e non ha stabilimento nell'UE → obbligo di nomina di rappresentante autorizzato (Art. 22).
- Per settori italiani rafforzati, i ruoli si specializzano ulteriormente (es. datore di lavoro che usa IA per gestione personale ha obblighi ex Art. 11 Legge 132 e D.Lgs. 152/1997).

## Documenti collegati

- `../references/ai-act-2024.md`
- `../references/iso42001-2023.md` (§4.1 Nota 1)
