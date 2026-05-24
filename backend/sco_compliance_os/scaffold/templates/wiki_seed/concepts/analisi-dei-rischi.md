---
type: concept
ambito_canonico: multi-dominio
domini_applicabili: [cybersicurezza, qualita-sgq, sicurezza-lavoro, governance-ai, privacy-protezione-dati]
title: "Analisi dei rischi"
status: stub
last_reviewed: 2026-05-24
tags: [wiki, concept, risk-management, analisi-rischi]
parent: "[[wiki/concepts/_index]]"
---

## 1. Definizione

L'analisi dei rischi e il processo sistematico di identificazione, analisi e valutazione dei rischi che possono compromettere il raggiungimento degli obiettivi di un'organizzazione. Costituisce il presupposto metodologico per la definizione del piano di trattamento dei rischi e per la programmazione delle misure di prevenzione e protezione. Nei sistemi di gestione conformi alla High Level Structure ISO, l'analisi dei rischi e elemento trasversale obbligatorio (capitolo 6 dei principali standard ISO).

## 2. Riferimenti normativi e standard

- **ISO 31000:2018** "Risk management - Guidelines" come framework generale di risk management
- **ISO/IEC 27005:2022** "Information security, cybersecurity and privacy protection - Guidance on managing information security risks" per il dominio cyber
- **ISO 9001:2015** capitolo 6 ("rischi e opportunita") per il dominio qualita
- **ISO/IEC 27001:2022** capitolo 6 ("pianificazione") per il dominio SGSI
- **ISO/IEC 42001:2023** capitolo 6 (con riferimento alla Valutazione d'Impatto del Sistema di IA AIIA) per il dominio AI governance
- **GDPR articolo 35** (Valutazione d'Impatto sulla Protezione dei Dati DPIA) per il dominio privacy
- **D.Lgs. 81/2008 articolo 28** (Valutazione dei Rischi DVR) per il dominio sicurezza lavoro
- **D.Lgs. 138/2024 articolo 24** (misure di gestione dei rischi cibernetici basate sul rischio) per il dominio NIS 2

## 3. Pattern applicativo

Un'analisi dei rischi metodologicamente robusta segue le fasi: (a) definizione del contesto e dello scope; (b) identificazione degli asset/processi/attivita in scope; (c) identificazione delle minacce e delle vulnerabilita; (d) analisi della probabilita di accadimento e dell'impatto delle conseguenze; (e) valutazione del rischio inerente sulla base di una scala definita; (f) confronto con i criteri di accettazione del rischio; (g) identificazione delle opzioni di trattamento (evitare, ridurre, trasferire, accettare); (h) definizione del rischio residuo post-trattamento; (i) documentazione formalizzata e riesame periodico almeno annuale. Il pattern e ricorsivo: ogni cambiamento rilevante (nuovi processi, nuove tecnologie, incidenti) innesca un riesame mirato.

## 4. Cross-reference

- [[wiki/concepts/business-impact-analysis-bia]] - input per il Business Continuity Management
- [[wiki/concepts/data-protection-impact-assessment-dpia]] - applicazione specifica per il dominio privacy
- [[wiki/concepts/valutazione-conformita]] - integrazione fra analisi dei rischi e conformita normativa
- [[wiki/entities/iso-iec-27001-2022]] - SGSI risk-based
- [[wiki/entities/iso-9001-2015]] - SGQ risk-based thinking
- [[wiki/entities/d-lgs-81-2008-tu-sicurezza]] - DVR per i rischi lavorativi
