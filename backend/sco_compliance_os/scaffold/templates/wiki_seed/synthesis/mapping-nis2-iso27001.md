---
type: synthesis
ambito_canonico: cybersicurezza
title: "Mapping NIS 2 (D.Lgs. 138/2024) <-> ISO/IEC 27001:2022"
status: stub
last_reviewed: 2026-05-24
confidence: alto
tags: [wiki, synthesis, mapping, nis2, iso27001, sgsi, cybersicurezza]
parent: "[[wiki/synthesis/_index]]"
entities_richiamate:
  - "[[wiki/entities/d-lgs-138-2024-nis2]]"
  - "[[wiki/entities/iso-iec-27001-2022]]"
---

## 1. Razionale del mapping

Il D.Lgs. 138/2024 (recepimento Direttiva NIS 2) richiede ai soggetti essenziali e importanti l'adozione di misure di gestione dei rischi cibernetici proporzionate ai rischi effettivi, ai costi e alla dimensione del soggetto, coerenti con lo stato dell'arte (articolo 24). Il regolamento di esecuzione UE 2024/2690 ha specificato in dettaglio le misure tecniche minime da implementare. La certificazione ISO/IEC 27001:2022 e ampiamente riconosciuta come riferimento di buona prassi per la dimostrazione dell'attuazione delle misure richieste, sebbene il D.Lgs. non la imponga esplicitamente. Questa synthesis mappa i 10 macro-ambiti del Capo IV del D.Lgs. con i corrispondenti controlli dell'Annex A dello standard.

## 2. Tabella di mapping

| Macro-ambito NIS 2 (Art. 24) | Controlli Annex A ISO/IEC 27001:2022 | Note |
|---|---|---|
| (a) Politiche di sicurezza | A.5.1 Policies for information security | Politica del SGSI come copertura |
| (b) Gestione degli incidenti | A.5.24-A.5.28 (Information security incident management) | Procedure incident response + notifica autorita |
| (c) Continuita operativa e backup | A.5.29 ICT readiness for business continuity, A.5.30 Information security during disruption, A.8.13 Information backup | Integrazione con BIA e BCP |
| (d) Sicurezza della supply chain | A.5.19-A.5.22 (Supplier relationships) | Clausole contrattuali ICT rafforzate per fornitori critici |
| (e) Sicurezza nell'acquisizione, sviluppo e manutenzione | A.5.37 Documented operating procedures, A.8.25-A.8.33 (Secure development) | Secure SDLC + secure coding + supplier management |
| (f) Politiche e procedure di valutazione dell'efficacia | A.5.35-A.5.36 (Independent review of information security), capitolo 9.2 audit interno, capitolo 9.3 riesame direzione | Programma audit + KPI di efficacia |
| (g) Pratiche di igiene cibernetica e formazione | A.6.3 Information security awareness, A.5.17 Authentication information, A.8.5 Secure authentication | Programma awareness annuale + MFA |
| (h) Politiche e procedure di crittografia | A.8.24 Use of cryptography | Politica crittografica + gestione chiavi |
| (i) Sicurezza delle risorse umane, controllo degli accessi, gestione degli asset | A.6.1-A.6.8 (People controls), A.5.15-A.5.18 (Access control), A.5.9-A.5.14 (Asset management) | Coverage diretta dei 3 ambiti |
| (j) Uso di soluzioni di autenticazione a piu fattori | A.8.5 Secure authentication | MFA come misura minima |

## 3. Considerazioni operative

La certificazione ISO/IEC 27001:2022 con SoA che includa tutti i controlli pertinenti dell'Annex A copre in modo sostanziale i requisiti del Capo IV del D.Lgs. 138/2024, ma NON e sostitutiva degli obblighi normativi NIS 2 (registrazione presso il portale ACN, notifica incidenti significativi entro 24h/72h/30g, designazione della struttura referente per la cybersicurezza, riesame periodico delle misure). I soggetti destinatari che dispongono di un SGSI certificato godono di una posizione di vantaggio nella dimostrazione di compliance, in particolare in occasione di ispezioni ACN. Si raccomanda di mantenere un mapping operativo continuo nel registro dei controlli, evidenziando quali controlli ISO sono adottati come misura NIS 2 e quali sono adottati per scopi ulteriori (es. requisiti contrattuali, ISO/IEC 27017 cloud, GDPR articolo 32).

## 4. Cross-reference e fonti

- [[wiki/entities/d-lgs-138-2024-nis2]] - testo normativo NIS 2 italiano
- [[wiki/entities/iso-iec-27001-2022]] - standard SGSI
- [[wiki/concepts/analisi-dei-rischi]] - presupposto metodologico per entrambi
- [[wiki/concepts/gestione-incidenti]] - punto di contatto NIS 2 - ISO 27001 sul incident management
- Regolamento di esecuzione UE 2024/2690 (misure tecniche minime NIS 2)
- ENISA "Technical guidelines for the implementation of minimum security measures" (versione applicabile)
