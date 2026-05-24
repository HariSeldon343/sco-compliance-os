---
type: concept
ambito_canonico: multi-dominio
domini_applicabili: [cybersicurezza, service-management-ict, qualita-sgq]
title: "Business Impact Analysis (BIA)"
status: stub
last_reviewed: 2026-05-24
tags: [wiki, concept, bia, business-continuity, business-impact-analysis]
parent: "[[wiki/concepts/_index]]"
---

## 1. Definizione

La Business Impact Analysis (BIA) e l'analisi formale dell'impatto che l'interruzione delle attivita di un'organizzazione (in seguito a un evento disruptive) produrrebbe sui processi di business, sui servizi erogati, sugli stakeholder, sul rispetto degli obblighi cogenti e contrattuali, sulla reputazione e sui risultati economici. La BIA fornisce gli input fondamentali per la definizione delle strategie di continuita operativa e degli obiettivi di recovery (RTO - Recovery Time Objective, RPO - Recovery Point Objective, MAO - Maximum Acceptable Outage).

## 2. Riferimenti normativi e standard

- **ISO 22301:2019** "Security and resilience - Business continuity management systems - Requirements" capitolo 8.2.2 (Business Impact Analysis)
- **ISO 22317:2021** "Security and resilience - Business continuity management systems - Guidelines for business impact analysis" come standard di riferimento metodologico dedicato
- **ISO/IEC 27001:2022 Annex A.5.29-A.5.30** - controlli specifici di continuita operativa e ICT readiness for business continuity
- **D.Lgs. 138/2024 articolo 24** - misure di gestione dei rischi cibernetici che includono la continuita operativa
- **DORA Reg. UE 2022/2554 articolo 11** - obblighi di BIA per il settore finanziario

## 3. Pattern applicativo

Una BIA metodologicamente robusta segue le fasi: (a) identificazione dei processi e dei servizi critici dell'organizzazione attraverso interviste con i process owner e analisi documentale; (b) caratterizzazione di ciascun processo (input, output, risorse necessarie, interdipendenze, asset di supporto, fornitori critici); (c) analisi dell'impatto dell'interruzione lungo un orizzonte temporale crescente (1 ora, 4 ore, 1 giorno, 1 settimana) con valutazione di impatti economici, operativi, di compliance, reputazionali, di sicurezza; (d) calcolo del MAO (Maximum Acceptable Outage) come tempo massimo oltre il quale l'interruzione produce conseguenze inaccettabili; (e) definizione dell'RTO (Recovery Time Objective) come obiettivo di tempo di ripristino, sempre piu basso del MAO; (f) definizione dell'RPO (Recovery Point Objective) come obiettivo di perdita dati massima accettabile; (g) prioritizzazione dei processi critici sulla base di MAO/RTO/RPO; (h) input al BCP (Business Continuity Plan) per la definizione delle strategie di continuita e dei piani operativi. La BIA va riesaminata periodicamente (almeno annualmente) e a fronte di cambiamenti rilevanti.

## 4. Cross-reference

- [[wiki/concepts/analisi-dei-rischi]] - input complementare alla BIA per il dimensionamento delle strategie di continuita
- [[wiki/concepts/gestione-incidenti]] - le strategie di continuita si attivano in caso di incidente disruptive
- [[wiki/entities/iso-iec-27001-2022]] - Annex A.5.29-A.5.30 controlli continuita
- [[wiki/entities/d-lgs-138-2024-nis2]] - articolo 24 misure NIS 2 inclusi continuita
