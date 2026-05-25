---
name: flusso-gsd-get-shit-done
description: "Flusso di lavoro GSD (Get Shit Done) adattato al vault di il consulente normativo: esecuzione disciplinata a fasi di OGNI cantiere non banale - inquadramento e roadmap, plan di fase, esecuzione, verifica con gate, chiusura milestone e retrospettiva. Usa SEMPRE come cornice operativa per task multi-step: perizie, gap analysis, pacchetti documentali, audit, progetti, sviluppo app, qualsiasi lavoro con piu passi. Triggera per: /gsd, gsd, get shit done, flusso di lavoro, imposta il cantiere, roadmap, fasi, plan-execute-verify, retrospettiva, milestone. Si integra con tutte le regole permanenti del vault (GOAL, VERIFY-OR-REDO, ASK-USER, multi-agent on-demand, QI190, tracciatura Conv. 41, smoke Conv. 46)."
---

# Skill: flusso-gsd-get-shit-done

## Scopo

Applicare la metodologia GSD ("Get Shit Done") come cornice operativa standard a ogni cantiere non banale del vault. GSD e una metodologia a fasi nata per agenti di sviluppo (repo originale gsd-build/get-shit-done, ora open-gsd/get-shit-done-redux) e qui adattata al lavoro consulenziale, documentale e di sviluppo di il consulente. Non sostituisce le regole permanenti del vault: le orchestra in un ciclo ripetibile.

## Quando usarla

Per qualsiasi lavoro con piu di 2-3 passi: perizie e relazioni, gap analysis, pacchetti documentali (procedure, policy, manuali), preparazione audit, progetti IRAI/antincendio, sviluppo app/SaaS, riorganizzazioni. Non per risposte conversazionali o singole micro-azioni.

## Il ciclo GSD adattato al vault (5 fasi)

1. INQUADRAMENTO E ROADMAP (gsd new-project / discuss-phase)
   - Chiarire obiettivo, requisiti, vincoli con AskUserQuestion (regola ASK-USER).
   - Definire la roadmap: milestone + fasi, e la CONDIZIONE DI COMPLETAMENTO esplicita e verificabile (blocco GOAL).
   - Materializzare la roadmap come lista attivita (TaskCreate), una task per fase/step.

2. PLAN DI FASE (gsd plan-phase)
   - Per la fase corrente: ricerca delle fonti (vault + WebSearch istituzionali, Conv. 35; multi-agent on-demand SOLO se richiesto/proposto), poi piano di task atomici.
   - Check del piano contro l'obiettivo PRIMA di eseguire (plan-checker): il piano raggiunge davvero il goal della fase?

3. ESECUZIONE (gsd execute-phase)
   - Eseguire i task della fase. Tracciare ogni operazione sostanziale (Conv. 41: skill attivate, file letti/verificati, assunzioni vs verifiche, comandi, decisioni, anomalie) nel daily.

4. VERIFICA - GATE (gsd verify-work)
   - VERIFY-OR-REDO: fare la verifica che farebbe l'utente, non un proofreading. Per software e deliverable: smoke E2E prima del tag/consegna (Conv. 46); per docx: triple check zip + reopen + PDF (Conv. 42).
   - NON dichiarare "fatto/perfetto" finche il gate non passa al 100% (GOAL). Se bloccato da input esterno, esporre il blocco in chiaro.

5. CHIUSURA E RETROSPETTIVA (gsd complete-milestone / extract-learnings)
   - Aggiornare stato, consegnare deliverable nel vault (con backup PRE-REDAZIONE), aggiornare daily + attivi.
   - Catturare i learnings: nuove convenzioni in CLAUDE.md, memorie persistenti, SOP candidate.

## Stato e tracciamento (mapping GSD -> vault SCO)

- ROADMAP.md / fasi  -> TaskCreate / TaskUpdate (la lista attivita e il widget di avanzamento).
- STATE.md           -> Giornaliero/attivi.md + daily Giornaliero/YYYY-MM/YYYY-MM-DD.md.
- RETROSPECTIVE      -> memorie persistenti + convenzioni cristallizzate in CLAUDE.md.
- CONTEXT predicati  -> wiki/ + Contesto/ (gia presenti).

## Modalita

- autonomous: delega piena, l'agente percorre tutte le fasi senza chiedere ai gate (coerente con Conv. 40 chiusura delegata). Usare solo su richiesta esplicita di delega.
- manager: l'agente si ferma e chiede conferma a ogni gate (default per cantieri ad alto impatto: deliverable cliente, modifiche a file di sistema).
- quick: task piccolo e a basso rischio, si salta il plan formale (fasi 2-3 compresse), ma il gate di verifica (fase 4) resta.

## Marker cerimoniale di apertura cantiere

A inizio di ogni cantiere significativo, oltre ai marker gia previsti (postura QI 190, blocco GOAL, "ottimizzazione: OK" del prompt-master, dichiarazione skill attive), stampare il blocco:

[GSD - cantiere <nome>] modalita: <autonomous|manager|quick> | roadmap: <N fasi> | fase corrente: <k/N> | condizione di completamento: <criterio verificabile>

## Integrazione con le regole permanenti

GSD e la cornice; queste regole restano vincolanti dentro ogni fase: GOAL-PERSISTENCE (condizione di completamento), VERIFY-OR-REDO, ASK-USER-QUESTION, SKILL-CONFIRM, multi-agent on-demand, QI 190, LINGUAGGIO SEMPLICE, regole tipografiche e anti-AI a chiusura deliverable, Conv. 41 (tracciatura), Conv. 46 (smoke prima del tag).

## Riferimenti

- reference/gsd-flusso.md - sintesi del flusso e dei comandi GSD canonici.
- Repo: open-gsd/get-shit-done-redux (ex gsd-build/get-shit-done, archiviato).

## Link correlati

- [[CLAUDE]] sezione "FLUSSO DI LAVORO GSD"
- [[Contesto/strategia]] sezione "Workflow Claude"

---
Part of [[Skill/_index]]
