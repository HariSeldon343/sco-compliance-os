# Documentazione di Sistema — SMS (ISO 20000-1) e SGSI (ISO 27001)

## Gerarchia documentale

```
Livello 1: Politiche (cosa e perché — impegno della Direzione)
Livello 2: Procedure (chi fa cosa, quando, come — processi operativi)
Livello 3: Istruzioni operative (come esattamente — step tecnici)
Livello 4: Registrazioni (evidenza che si è fatto — record, log, ticket, verbali)
```

---

## Documentazione obbligatoria SMS (ISO 20000-1:2018)

| Documento | Clausola | Tipo |
|-----------|----------|------|
| Politica SMS | 5.2 | Politica |
| Scope dell'SMS | 4.3 | Documento di sistema |
| Catalogo dei servizi | 8.2 | Documento operativo |
| Obiettivi del servizio | 6.2 | Piano |
| Registro rischi SMS | 6.1 | Registro |
| Procedura Incident Management | 8.6.1 | Procedura |
| Procedura Problem Management | 8.6.2 | Procedura |
| Procedura Change Management | 8.4 | Procedura |
| Procedura Configuration Management | 8.3 | Procedura |
| CMDB (Configuration Management Database) | 8.3 | Registro |
| Procedura Service Continuity | 8.7.3 | Procedura |
| Piano di continuità del servizio | 8.7.3 | Piano |
| Procedura Supplier Management | 8.7.5 | Procedura |
| Registro fornitori / SLA/OLA/UC | 8.7.5 | Registro |
| KEDB (Known Error Database) | 8.6.2 | Registro |
| Dashboard KPI e report di servizio | 8.7.6, 9.1 | Report |
| Programma audit interni SMS | 9.2 | Piano |
| Verbali riesame direzione SMS | 9.3 | Registro |
| Registro NC e azioni correttive | 10.1 | Registro |
| Piano di miglioramento | 10.2 | Piano |

---

## Documentazione obbligatoria SGSI (ISO 27001:2022)

| Documento | Clausola/Controllo | Tipo |
|-----------|-------------------|------|
| Politica della sicurezza delle informazioni | 5.2, A.5.1 | Politica |
| Scope del SGSI | 4.3 | Documento di sistema |
| Metodologia risk assessment | 6.1.2 | Procedura |
| Risk Assessment Report | 6.1.2 | Registro/Report |
| Risk Treatment Plan | 6.1.3 | Piano |
| Statement of Applicability (SoA) | 6.1.3 | Documento chiave |
| Obiettivi sicurezza | 6.2 | Piano |
| Registro asset | A.5.9 | Registro |
| Politica classificazione informazioni | A.5.12 | Politica |
| Politica controllo accessi | A.5.15 | Politica |
| Politica crittografia | A.8.24 | Politica |
| Politica sicurezza fornitori | A.5.19 | Politica |
| Procedura gestione incidenti sicurezza | A.5.24 | Procedura |
| Procedura gestione vulnerabilità | A.8.8 | Procedura |
| Procedura backup | A.8.13 | Procedura/Istruzione |
| Procedura change management (sicurezza) | A.8.32 | Procedura |
| Piano BCP/DRP | A.5.30, ISO 22301 | Piano |
| Programma audit interni | 9.2 | Piano |
| Piano di formazione e awareness | A.6.3 | Piano |
| Verbali riesame direzione | 9.3 | Registro |
| Registro NC e azioni correttive | 10.1 | Registro |

---

## Template struttura — Procedura SMS/SGSI

```markdown
# [TITOLO PROCEDURA]
**Codice**: [es. SMS-PRO-001 | SGI-PRO-007]
**Versione**: X.X
**Data emissione**: GG/MM/AAAA
**Approvata da**: [Ruolo]
**Classificazione**: [Uso Interno / Riservato]

## 1. Scopo e campo di applicazione
[Cosa descrive la procedura e a chi/cosa si applica]

## 2. Riferimenti normativi
[ISO 20000-1:2018 §X.X | ISO 27001:2022 cl./A.X.X | Art. X D.Lgs. 138/2024 | ...]

## 3. Definizioni e acronimi
[Termini tecnici usati nella procedura]

## 4. Responsabilità (RACI)
| Attività | R | A | C | I |
|----------|---|---|---|---|

## 5. Descrizione del processo
### 5.1 [Fase 1]
### 5.2 [Fase 2]
[...]

## 6. KPI e metriche
[Indicatori di performance del processo]

## 7. Documenti correlati
[Procedure collegate, modelli, registri generati]

## 8. Storico revisioni
| Ver. | Data | Autore | Modifiche |
|------|------|--------|-----------|
```

---

## Template struttura — SLA (Service Level Agreement)

```markdown
# Service Level Agreement — [Nome Servizio]
**Versione**: X.X | **Data**: GG/MM/AAAA
**Cliente**: [Organizzazione / BU]
**Service Provider**: [Team IT / Fornitore]
**Periodo di validità**: [da — a]

## 1. Descrizione del servizio
[Cosa include e cosa esclude il servizio]

## 2. Orari di servizio e supporto
- Orario operativo: [es. 8:00–18:00 Lun-Ven]
- Supporto reperibilità: [es. 7x24 per P1]
- Finestre di manutenzione: [es. Sab 22:00–02:00]

## 3. Obiettivi di livello di servizio (SLO)

| KPI | Target | Misurazione | Penale |
|-----|--------|-------------|--------|
| Disponibilità mensile | ≥ 99.5% | Monitoring automatico | [X€/0.1% sotto target] |
| Tempo risposta P1 | ≤ 15 min | Ticketing system | [penale definita] |
| Tempo risoluzione P1 | ≤ 4h | Ticketing system | [penale definita] |
| Tempo risposta P2 | ≤ 30 min | Ticketing system | — |
| Tempo risoluzione P2 | ≤ 8h | Ticketing system | — |
| Change success rate | ≥ 95% | Post-PIR | — |

## 4. Gestione degli incidenti
[Riferimento a procedura Incident Management e classificazione P1–P4]

## 5. Escalation
[Matrice escalation con contatti e tempi]

## 6. Reportistica
[Frequenza, formato, distribuzione SLA report]

## 7. Revisione dello SLA
[Frequenza revisione, trigger per revisione straordinaria]

## 8. Eccezioni e cause di forza maggiore
[Eventi che sospendono il calcolo SLA]

## 9. Firme
[Cliente | Service Provider | Data]
```

---

## Template CMDB — Attributi minimi CI

| Attributo | Descrizione | Esempio |
|-----------|-------------|---------|
| CI_ID | Identificatore univoco | SRV-PROD-001 |
| Nome | Nome dell'asset | Server Applicativo ERP |
| Tipo | Categoria (Server / VM / SW / Rete / Contratto / Servizio) | Server Fisico |
| Owner | Responsabile tecnico | [Nome Ruolo] |
| Business Owner | Referente business | [Nome Ruolo] |
| Stato | (Operativo / In manutenzione / Dismesso / In staging) | Operativo |
| Ambiente | (Produzione / Pre-prod / Test / DR) | Produzione |
| Versione/Release | Versione SO o applicativo | Windows Server 2022 22H2 |
| Localizzazione | Data center / rack / sede | DC-Principale Rack-A03 |
| IP / FQDN | Indirizzo rete | 10.0.1.50 / srv-erp01.azienda.it |
| Data installazione | Prima messa in servizio | 01/03/2024 |
| Data ultima modifica | Ultima change applicata | 15/11/2024 (CHG-2024-089) |
| Classificazione sicurezza | Criticità asset | Alto |
| SLA associato | SLA di riferimento | SLA-ERP-001 |
| CI correlati | Dipendenze (CI padre/figlio) | DB-PROD-001, FW-PROD-01 |
| Contratto manutenzione | Riferimento contratto | CONT-HW-2024-003 |

---

## Agenda riesame direzione SMS (ISO 20000-1 cl. 9.3)

1. Approvazione verbale riesame precedente
2. Performance KPI vs obiettivi di servizio
3. Risultati audit interni SMS (NC aperte/chiuse)
4. Risultati audit di certificazione/sorveglianza (se applicabile)
5. Reclami clienti e CSAT survey
6. Stato SLA (breach, trend, cause)
7. Stato fornitori critici (SLA breach, incidenti supply chain)
8. Incidenti significativi (P1, Major Incident, post-incident review)
9. NC e azioni correttive: stato avanzamento
10. Rischi e opportunità SMS: aggiornamento registro
11. Modifiche al contesto (organizzative, normative, tecnologiche)
12. Adeguatezza risorse (personale, strumenti, formazione)
13. Obiettivi per il prossimo periodo
14. Piano di miglioramento: approvazione

---

## Nomenclatura documenti

**Formato consigliato**: `[SIGLA-AREA]-[TIPO]-[NUMERO]_[Titolo breve]_v[X.X]`

Esempi:
- `SMS-PRO-001_Incident_Management_v1.2`
- `SGI-POL-003_Politica_Sicurezza_Informazioni_v2.0`
- `NIS2-PIA-001_Piano_Adeguamento_NIS2_v1.0`
- `SMS-REG-005_KEDB_v3.1`
- `SGI-SoA-001_Statement_of_Applicability_v4.0`

**Sigle area**: SMS (Service Management), SGI (SGSI/27001), NIS (NIS2/Cyber), IMS (Integrato)
**Tipi**: POL (politica), PRO (procedura), IO (istruzione operativa), REG (registro), PIA (piano), RPT (report), CHK (checklist), MOD (modello/template)
