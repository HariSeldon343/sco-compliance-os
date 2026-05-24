---
type: synthesis
ambito_canonico: privacy-protezione-dati
title: "Mapping GDPR (Reg. UE 2016/679) <-> ISO/IEC 27701:2019 (estensione PIMS)"
status: stub
last_reviewed: 2026-05-24
confidence: medio
tags: [wiki, synthesis, mapping, gdpr, iso27701, pims, privacy]
parent: "[[wiki/synthesis/_index]]"
entities_richiamate:
  - "[[wiki/entities/reg-ue-2016-679-gdpr]]"
  - "[[wiki/entities/iso-iec-27001-2022]]"
---

## 1. Razionale del mapping

ISO/IEC 27701:2019 "Security techniques - Extension to ISO/IEC 27001 and ISO/IEC 27002 for privacy information management - Requirements and guidelines" estende lo standard ISO/IEC 27001 con i requisiti specifici per un sistema di gestione della privacy delle informazioni (PIMS - Privacy Information Management System). Lo standard e direttamente mappato sui principi e sugli obblighi del GDPR e fornisce un framework certificabile per le organizzazioni che svolgono il ruolo di titolare e/o responsabile del trattamento. Questa synthesis evidenzia i punti chiave di mapping fra i principali obblighi del GDPR e i corrispondenti requisiti dello standard.

## 2. Tabella di mapping

| Obbligo GDPR | ISO/IEC 27701:2019 |
|---|---|
| Art. 5 - Principi del trattamento | Capitoli 5-6 PIMS + clausole specifiche di Annex A e B |
| Art. 24-25 - Responsabilita del titolare; privacy by design e by default | Annex A (controlli specifici per il titolare): A.7.2.1 Identify and document purpose, A.7.4.1 Limit collection, A.7.4.7 Privacy by design |
| Art. 28 - Responsabile del trattamento | Annex B (controlli specifici per il responsabile): B.8.2 Conditions for collection and processing, B.8.5 Records related to processing PII |
| Art. 30 - Registro dei trattamenti | A.7.2.8 Records related to processing PII (titolare), B.8.2.5 Records related to processing PII (responsabile) |
| Art. 32 - Sicurezza del trattamento | Tutti i controlli di ISO/IEC 27001:2022 Annex A + estensioni A.7.4 e A.7.5 PIMS |
| Art. 33-34 - Notifica e comunicazione delle violazioni | A.7.3.5 Information security incident reporting (titolare), B.8.4 Incident management (responsabile) |
| Art. 35-36 - DPIA e consultazione preventiva | A.7.2.5 Privacy impact assessment |
| Art. 37-39 - DPO | A.6.1.1 Information security roles and responsibilities (con specifiche PIMS) |
| Art. 44-49 - Trasferimenti extra-UE | A.7.5 PII transfer (titolare), B.8.5 PII transfer (responsabile) |

## 3. Considerazioni operative

La certificazione ISO/IEC 27701:2019 (in estensione a ISO/IEC 27001:2022) NON sostituisce la conformita al GDPR ne preclude la responsabilita amministrativa o penale per violazioni del Regolamento. Tuttavia, costituisce: (a) elemento di evidenza dell'adozione di misure tecniche e organizzative adeguate ai sensi dell'articolo 32 GDPR; (b) elemento di evidenza dell'accountability del titolare ai sensi degli articoli 5.2 e 24; (c) framework metodologico per implementare in modo sistematico il PIMS; (d) elemento di affidabilita nei rapporti contrattuali B2B fra titolare e responsabile del trattamento. La certificazione richiede una preventiva certificazione ISO/IEC 27001 (lo standard 27701 e estensione, non standalone). L'aggiornamento dello standard a una nuova edizione allineata alla revisione 2022 di ISO/IEC 27001 e atteso a breve termine.

## 4. Cross-reference e fonti

- [[wiki/entities/reg-ue-2016-679-gdpr]] - testo normativo GDPR
- [[wiki/entities/iso-iec-27001-2022]] - SGSI base per estensione PIMS
- [[wiki/entities/garante-privacy]] - autorita di controllo italiana
- [[wiki/concepts/data-protection-impact-assessment-dpia]] - applicazione DPIA mappata su A.7.2.5
- [[wiki/concepts/gestione-incidenti]] - applicazione data breach mappata su A.7.3.5
- ISO/IEC 27018:2019 (privacy nei cloud public services come responsabile) come standard correlato
