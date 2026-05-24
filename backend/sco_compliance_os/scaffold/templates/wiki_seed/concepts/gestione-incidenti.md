---
type: concept
ambito_canonico: multi-dominio
domini_applicabili: [cybersicurezza, service-management-ict, privacy-protezione-dati, accreditamento-sanitario]
title: "Gestione degli incidenti"
status: stub
last_reviewed: 2026-05-24
tags: [wiki, concept, incident-management, incidenti, notifica]
parent: "[[wiki/concepts/_index]]"
---

## 1. Definizione

La gestione degli incidenti e l'insieme di processi, procedure e responsabilita finalizzati alla rilevazione tempestiva, all'analisi, alla contenimento, all'eradicazione e al recupero da eventi che compromettono o minacciano di compromettere la confidenzialita, l'integrita, la disponibilita di un servizio, di un sistema, di un'informazione, ovvero la sicurezza di pazienti o lavoratori. Comprende inoltre la notifica obbligatoria alle autorita competenti laddove l'evento integri la fattispecie di incidente significativo, di data breach o di evento sentinella.

## 2. Riferimenti normativi e standard

- **D.Lgs. 138/2024 articolo 25** - obblighi di notifica incidenti significativi NIS 2 (finestra 24h/72h/30g)
- **GDPR articoli 33-34** - notifica delle violazioni di dati personali al Garante (72h) e comunicazione agli interessati
- **ISO/IEC 27035:2023** "Information security incident management" come standard di riferimento metodologico
- **ISO/IEC 27001:2022 Annex A.5.24-A.5.28** - controlli specifici di gestione degli incidenti di sicurezza delle informazioni
- **ISO/IEC 20000-1:2018 capitolo 8.6.1** - processo di Incident Management nel SMS
- **Legge 24/2017 (Gelli-Bianco)** - gestione del rischio clinico ed eventi sentinella nelle strutture sanitarie
- **Direttiva NIS 2 Reg. UE 2024/2690** - regolamento di esecuzione su misure tecniche minime e procedure di notifica

## 3. Pattern applicativo

Un processo di gestione degli incidenti maturo prevede: (a) rilevazione attraverso fonti automatiche (SIEM, alert, monitoraggio) e manuali (segnalazioni utente, audit, controlli); (b) registrazione formale nel sistema di Incident Management con classificazione di priorita e gravita; (c) analisi preliminare per qualificare l'evento (incidente vs anomalia vs falso positivo); (d) classificazione di significativita ai sensi della normativa applicabile (criteri NIS 2, criteri GDPR, criteri evento sentinella); (e) contenimento immediato per arginare la propagazione; (f) eradicazione delle cause; (g) recupero dei servizi e dei dati con verifica di integrita; (h) notifica alle autorita competenti entro i termini di legge (CSIRT-Italia entro 24h pre-notifica + 72h notifica + 30g relazione finale per NIS 2; Garante entro 72h per data breach GDPR); (i) lesson learned formalizzata in azione correttiva; (j) aggiornamento del registro dei rischi e dei controlli. Il processo e supportato da un piano di Incident Response Plan (IRP) testato periodicamente.

## 4. Cross-reference

- [[wiki/concepts/business-impact-analysis-bia]] - input per la prioritizzazione del recovery
- [[wiki/concepts/analisi-dei-rischi]] - i lesson learned alimentano l'aggiornamento del registro
- [[wiki/concepts/non-conformita-azioni-correttive]] - incidente come trigger di NC critiche e AC
- [[wiki/entities/d-lgs-138-2024-nis2]] - obblighi NIS 2 di notifica
- [[wiki/entities/reg-ue-2016-679-gdpr]] - obblighi GDPR di notifica violazioni
- [[wiki/entities/acn]] - destinataria delle notifiche NIS 2
- [[wiki/entities/garante-privacy]] - destinatario delle notifiche data breach
