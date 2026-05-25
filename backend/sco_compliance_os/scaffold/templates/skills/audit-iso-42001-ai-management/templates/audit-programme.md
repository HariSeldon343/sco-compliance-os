# Template — Programma di audit interno AIMS

> Struttura per ISO/IEC 42001 cl. 9.2. Utilizzabile anche per audit combinati con 27001 / 9001 / 20000-1.

---

# Programma di audit interno AIMS — [Denominazione organizzazione]

**Codice documento:** AIMS-AUD-PROG-[anno]
**Versione:** [x.y]
**Data di emissione:** [gg/mm/aaaa]
**Owner:** [Audit Lead]
**Approvato da:** [Direzione]

## 1. Scopo

Pianificare gli audit interni AIMS per l'anno [aaaa] coprendo, in un ciclo triennale, tutte le clausole 4-10 e tutti i controlli Appendice A applicabili come risultanti dalla SoA AIMS-SOA-01.

## 2. Obiettivi

- Verificare la conformità a ISO/IEC 42001.
- Verificare l'implementazione degli obblighi AI Act applicabili.
- Verificare la coerenza con i principi Legge 132/2025 e con gli obblighi settoriali attivati.
- Verificare l'efficacia delle misure di mitigazione del registro rischi.
- Identificare non conformità, osservazioni, spunti di miglioramento.
- Fornire input al riesame di direzione (cl. 9.3).

## 3. Ambito

- Tutti i processi AIMS definiti dallo scope AIMS-SCP-01.
- Tutti i sistemi IA classificati "alto rischio" AI Act.
- A campione, sistemi IA a rischio limitato / minimo.
- Processi condivisi con SGSI / SGQ / SMS quando integrati.

## 4. Ciclo triennale

| Anno | Focus primario | Clausole / controlli | Sistemi IA campionati |
|------|---------------|----------------------|------------------------|
| Anno 1 | Governance, scope, risk, AIIA | Cl. 4-6, A.2, A.3, A.5 | Sistemi alto rischio, 100% |
| Anno 2 | Ciclo di vita e dati | A.6, A.7 | Alto rischio (100%) + campione altri |
| Anno 3 | Uso responsabile e terze parti | A.8, A.9, A.10 | Alto rischio + fornitori critici |

Ogni anno copre anche: cl. 7 (supporto), cl. 8 (attività operative), cl. 9 (valutazione prestazioni), cl. 10 (miglioramento).

## 5. Piano operativo dell'anno [aaaa]

| Audit | Data prevista | Ambito | Team | Giornate | Output atteso |
|-------|---------------|--------|------|----------|---------------|
| A-01 | | Governance + politica | [Auditor X, Y] | 2 | Rapporto A-01 |
| A-02 | | Risk + AIIA | | 3 | Rapporto A-02 |
| A-03 | | Ciclo di vita sistemi alto rischio | | 4 | Rapporto A-03 |
| A-04 | | Dati e data governance | | 3 | Rapporto A-04 |
| A-05 | | Fornitori | | 2 | Rapporto A-05 |
| A-06 | | Incidenti, PMM, NC | | 2 | Rapporto A-06 |

## 6. Checklist operativa

Per ogni audit, checklist dedicata con:

- Domande di verifica per clausola ISO 42001.
- Domande di verifica per controllo Appendice A applicabile.
- Domande di verifica per articolo AI Act attivato.
- Domande di verifica per settore Legge 132 rilevante.
- Colonna evidenza (documento, record, log, intervista, test).

## 7. Team di audit

| Nome | Ruolo | Competenze | Indipendenza | Conflitti dichiarati |
|------|-------|------------|--------------|----------------------|
| | Lead Auditor | ISO 42001 + AI Act + dominio | Sì/No | |
| | Auditor | Security / Data protection | | |
| | Auditor | Dominio tecnico | | |

**Principio**: nessun auditor verifica processi di cui è process owner.

## 8. Criteri di audit

- Norma ISO/IEC 42001:2023.
- Reg. (UE) 2024/1689 (AI Act).
- Legge 132/2025.
- Policy, procedure, istruzioni operative interne.
- Contratti con fornitori e clienti.
- Standard volontari applicabili (ISO 23894, 23053, ecc.).

## 9. Evidenze attese per tema

| Tema | Evidenze |
|------|----------|
| Politica AI | Documento approvato, distribuzione, formazione |
| Risk | Registro rischi, metodologia, soglie |
| AIIA / FRIA | Report compilati, revisioni |
| Ciclo di vita | SDLC, gate approvativi, documentazione tecnica |
| Dati | Data governance policy, registro dataset, lineage |
| Log | Sistema di logging, integrità, retention |
| Trasparenza | Istruzioni d'uso, informative, user interface |
| Sorveglianza umana | Ruoli, formazione, audit operativi |
| Cybersecurity IA | Penetration test, threat model |
| Fornitori | Contratti, DPA, audit fornitore |
| Incidenti | Registro incidenti, notifiche autorità |
| PMM | Report PMM periodici |
| Riesame direzione | Verbali riesame |

## 10. Reportistica

- Rapporto per singolo audit (entro 15 gg lavorativi dalla chiusura audit).
- Executive summary all'AI Governance Lead.
- Sintesi annuale per riesame di direzione.

## 11. Follow-up

- Verifica efficacia azioni correttive: 90-180 giorni dopo attuazione.
- Registro centralizzato NC / OSS / SM.

## 12. Budget e risorse

Stima: [giornate/uomo complessive; costi se audit con terze parti].
