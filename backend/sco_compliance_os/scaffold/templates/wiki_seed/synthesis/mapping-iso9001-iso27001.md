---
type: synthesis
ambito_canonico: multi-dominio
domini_applicabili: [qualita-sgq, cybersicurezza]
title: "Mapping ISO 9001:2015 <-> ISO/IEC 27001:2022 (sistema integrato SGQ + SGSI)"
status: stub
last_reviewed: 2026-05-24
confidence: alto
tags: [wiki, synthesis, mapping, iso9001, iso27001, sistema-integrato, hls]
parent: "[[wiki/synthesis/_index]]"
entities_richiamate:
  - "[[wiki/entities/iso-9001-2015]]"
  - "[[wiki/entities/iso-iec-27001-2022]]"
---

## 1. Razionale del mapping

ISO 9001:2015 (SGQ) e ISO/IEC 27001:2022 (SGSI) condividono la High Level Structure (HLS) Annex SL Appendice 2 di Iso Iec Directives Part 1 che armonizza i requisiti dei sistemi di gestione ISO. Cio consente di integrare i due sistemi in un unico Sistema di Gestione Integrato (SGI) ottimizzando i processi trasversali (gestione documentale, audit interno, riesame della direzione, gestione delle non conformita, miglioramento continuo) ed evitando duplicazioni operative. Questa synthesis mappa i 10 capitoli comuni HLS evidenziando le specificita di ciascun sistema e i punti di integrazione operativa.

## 2. Tabella di mapping HLS

| Capitolo HLS | ISO 9001:2015 (SGQ) | ISO/IEC 27001:2022 (SGSI) | Punto di integrazione operativa |
|---|---|---|---|
| 4 - Contesto dell'organizzazione | Identificazione del contesto + stakeholder + scope SGQ | Identificazione del contesto + stakeholder + scope SGSI | Analisi del contesto unica con specificazione degli scope distinti |
| 5 - Leadership | Politica per la qualita, ruoli SGQ | Politica per la sicurezza delle informazioni, ruoli SGSI | Politica integrata o due politiche distinte, ruoli mappati su matrice unica |
| 6 - Pianificazione | Rischi e opportunita, obiettivi qualita | Risk assessment + Risk treatment + SoA + obiettivi sicurezza | Metodologia di risk assessment unica con sottoinsiemi specifici |
| 7 - Supporto | Risorse, competenze, sensibilizzazione, comunicazione, informazioni documentate | Risorse, competenze, sensibilizzazione, comunicazione, informazioni documentate | Procedure comuni di gestione risorse umane, formazione integrata |
| 8 - Operativita | Pianificazione e controllo operativo, requisiti prodotto/servizio, progettazione, controllo fornitori | Implementazione dei controlli Annex A applicabili | Procedure di controllo fornitori integrate; gestione delle non conformita unica |
| 9 - Valutazione delle prestazioni | Monitoraggio + audit interno + riesame della direzione | Monitoraggio + audit interno + riesame della direzione | Programma di audit interno unico; riesame della direzione integrato |
| 10 - Miglioramento | Non conformita e azioni correttive | Non conformita e azioni correttive | Sistema unico di gestione NC/AC con classificazione per area |

## 3. Considerazioni operative

L'integrazione SGQ + SGSI in un Sistema di Gestione Integrato produce benefici operativi: (a) riduzione del numero di procedure documentate (procedura unica di audit interno, di riesame della direzione, di gestione NC/AC, di gestione dei documenti, di gestione dei fornitori); (b) audit congiunti che evitano disagi operativi e riducono il tempo di audit complessivo (auditor congiunto + cliente unico vs auditor separati); (c) riesame della direzione unico con prospettiva integrata; (d) razionalizzazione dei ruoli e delle responsabilita; (e) economie di scala nella formazione del personale. I rischi tipici: (a) perdita di specificita di alcuni controlli SGSI se assorbiti in procedure SGQ generiche; (b) difficolta di gestione di certificazioni separate (alcuni organismi non rilasciano certificazione SGI unificata ma due certificati distinti emessi nello stesso audit). Si raccomanda un manuale SGI unico con sezioni dedicate per gli aspetti specifici di ciascun sistema e una mappa di copertura che evidenzi quali controlli sono assorbiti da quale processo del sistema integrato. Tipica configurazione SGI: azienda manifatturiera con ICT interna; azienda di consulenza con processi qualita maturi che aggiunge cybersicurezza per esigenze contrattuali; ente pubblico con SGQ storico che integra SGSI per obblighi NIS 2 / L. 90/2024.

## 4. Cross-reference e fonti

- [[wiki/entities/iso-9001-2015]] - standard SGQ
- [[wiki/entities/iso-iec-27001-2022]] - standard SGSI
- [[wiki/concepts/audit-interno]] - programma audit integrato
- [[wiki/concepts/riesame-direzione]] - riesame integrato
- [[wiki/concepts/non-conformita-azioni-correttive]] - sistema NC/AC unico
- ISO/IEC Directives Part 1 Annex SL Appendice 2 (HLS framework)
- IAF MD 11:2019 "Application of ISO/IEC 17021-1 for audits of integrated management systems"
