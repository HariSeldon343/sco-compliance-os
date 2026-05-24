---
type: synthesis
ambito_canonico: governance-ai
title: "Mapping ISO/IEC 42001:2023 <-> AI Act (Reg. UE 2024/1689)"
status: stub
last_reviewed: 2026-05-24
confidence: alto
tags: [wiki, synthesis, mapping, iso42001, ai-act, aims, governance-ai]
parent: "[[wiki/synthesis/_index]]"
entities_richiamate:
  - "[[wiki/entities/iso-iec-42001-2023]]"
  - "[[wiki/entities/reg-ue-2024-1689-ai-act]]"
---

## 1. Razionale del mapping

Il Regolamento (UE) 2024/1689 (AI Act) stabilisce obblighi vincolanti per provider e deployer di sistemi di IA ad alto rischio (Capo III), con applicabilita progressiva 2025-2027. Lo standard internazionale ISO/IEC 42001:2023 fornisce il primo framework certificabile per un sistema di gestione dell'intelligenza artificiale (AIMS), allineato strutturalmente ai requisiti AI Act. La presunzione di conformita parziale ai sensi degli articoli 40-42 AI Act per le organizzazioni certificate ISO/IEC 42001 e attesa alla pubblicazione delle norme armonizzate europee. Questa synthesis mappa i requisiti chiave del Capo III AI Act con i corrispondenti requisiti dello standard e con i 39 controlli dell'Appendice A.

## 2. Tabella di mapping

| Requisito AI Act (Capo III, sistemi ad alto rischio) | ISO/IEC 42001:2023 |
|---|---|
| Art. 9 - Sistema di gestione dei rischi | Capitolo 6 + Appendice A.5 (Valutazione d'impatto del sistema di IA AIIA) |
| Art. 10 - Dati e governance dei dati | Appendice A.7 (Dati per i sistemi di IA) |
| Art. 11 - Documentazione tecnica | Capitolo 7.5 (Informazioni documentate) + Appendice A.6 (Ciclo di vita del sistema di IA) |
| Art. 12 - Registrazione automatica (logging) | Appendice A.6.2.6 (Tenuta dei registri durante il funzionamento del sistema di IA) |
| Art. 13 - Trasparenza e fornitura di informazioni ai deployer | Appendice A.8 (Informazioni per le parti interessate) |
| Art. 14 - Sorveglianza umana | Appendice A.9 (Uso responsabile dei sistemi di IA) |
| Art. 15 - Accuratezza, robustezza e cibersicurezza | Appendice A.6.2 (Sviluppo del sistema di IA) + integrazione con ISO/IEC 27001 |
| Art. 17 - Sistema di gestione della qualita per i provider | Tutto il sistema AIMS (capitoli 4-10) |
| Art. 18 - Conservazione documentazione | Capitolo 7.5.3 (Controllo delle informazioni documentate) |
| Art. 26 - Obblighi dei deployer | Appendice A.9 (Uso responsabile) + capitolo 8 (Operativita) |
| Art. 27 - FRIA per deployer pubblici e categorie specifiche | Appendice A.5 (AIIA estesa con dimensione diritti fondamentali) |

## 3. Considerazioni operative

La certificazione ISO/IEC 42001:2023 NON e sostitutiva della valutazione di conformita ex-ante richiesta dall'AI Act per i sistemi ad alto rischio (marcatura CE, registrazione in banca dati UE). Tuttavia, fornisce: (a) il framework metodologico per implementare in modo sistematico tutti i requisiti del Capo III; (b) la base documentale per la documentazione tecnica dell'articolo 11; (c) il riferimento per la dimostrazione di "stato dell'arte" in caso di ispezioni o contenziosi; (d) un vantaggio competitivo nel B2B come elemento di affidabilita verso clienti e partner. I provider che mirano alla compliance AI Act sono incoraggiati ad avviare il percorso AIMS in parallelo alla valutazione di conformita ex-ante, integrando il sistema di gestione con il sistema di gestione della qualita ai sensi dell'articolo 17 (per i quali la coerenza con ISO 9001 e gia consolidata). I deployer pubblici e privati soggetti a FRIA possono estendere il modulo AIIA del AIMS con le dimensioni dei diritti fondamentali richieste dall'articolo 27.

## 4. Cross-reference e fonti

- [[wiki/entities/iso-iec-42001-2023]] - standard AIMS
- [[wiki/entities/reg-ue-2024-1689-ai-act]] - testo AI Act
- [[wiki/concepts/analisi-dei-rischi]] - presupposto metodologico AIIA
- [[wiki/concepts/valutazione-conformita]] - confronto fra certificazione AIMS e valutazione di conformita ex-ante AI Act
- Legge 23 settembre 2025, n. 132 (decreto italiano di adeguamento)
- AgID Linee guida sull'IA nella PA (versioni applicabili)
