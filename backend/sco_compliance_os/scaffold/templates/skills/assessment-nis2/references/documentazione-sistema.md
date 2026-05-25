# Tassonomia Documentale e Regole di Redazione

## Indice
1. [Tassonomia completa](#1-tassonomia)
2. [Regole di redazione](#2-regole)

---

## 1. Tassonomia completa

### Politiche e documenti strategici
- Politica per la sicurezza delle informazioni [ISO 27001 §5.2]
- Politica di gestione dei rischi cybersecurity [NIS2 Art. 21.2.a]
- Politica per la continuità operativa [ISO 22301 §5.2]
- Politica per la qualità [ISO 9001 §5.2]
- Politica uso accettabile asset informativi
- Politica classificazione informazioni
- Politica gestione accessi
- Politica crittografia
- Politica sicurezza fisica e ambientale
- Politica sicurezza risorse umane
- Politica sicurezza supply chain

### Procedure operative

| Categoria | Procedure |
|---|---|
| **Gestione rischi** | Risk assessment integrata (27005/31000/NIS2); Valutazione rischi continuità operativa |
| **Gestione incidenti** | Incidenti sicurezza [A.5.24-5.28]; Notifica incidenti NIS2 [Art.23 — CSIRT 24h/72h/1m]; Incidenti L. 90/2024 |
| **Controllo accessi** | Gestione identità e accessi; MFA [NIS2 Art.21.2.j]; Accessi privilegiati |
| **Continuità operativa** | BIA; Gestione crisi; Disaster recovery; Esercitazioni BC/DR |
| **Supply chain** | Qualifica e valutazione fornitori; Sicurezza catena approvvigionamento [NIS2 Art.21.2.d] |
| **Operazioni** | Gestione vulnerabilità; Patch management; Change management; Backup e restore; Log management e monitoraggio |
| **Documentazione** | Gestione informazioni documentate [HLS §7.5]; Comunicazione interna/esterna [HLS §7.4] |
| **Audit e miglioramento** | Audit interno [HLS §9.2]; NC e azioni correttive [HLS §10.2]; Riesame direzione [HLS §9.3] |
| **Risorse umane** | Competenze e formazione [HLS §7.2]; Igiene informatica [NIS2 Art.21.2.g]; Sicurezza HR |
| **Crittografia** | Gestione crittografia [NIS2 Art.21.2.h] |

### Piani
- Piano trattamento rischi
- Piano audit interni annuale
- Piano formazione e consapevolezza cybersecurity
- Piano miglioramento continuo
- Piano continuità operativa e disaster recovery
- Piano comunicazione crisi
- Piano gestione incidenti
- Piano adeguamento NIS2 (roadmap)
- Piano adeguamento Legge 90/2024

### Registri e registrazioni
- Registro rischi (integrato multi-framework)
- Registro asset informativi [A.5.9]
- Registro incidenti sicurezza
- Registro incidenti significativi NIS2
- Registro fornitori e valutazione sicurezza supply chain
- Registro NC e AC
- Registro esercitazioni BC/DR
- CMDB (Configuration Management Database)
- Registro comunicazioni parti interessate
- Registro formazione e consapevolezza
- Registro vulnerabilità

### Report e verbali
- Verbale riesame direzione
- Report audit interno
- Report valutazione rischi
- Report BIA
- Report esercitazione BC/DR
- Rapporto annuale NIS2 per organo gestione [Art. 20]
- Report assessment controlli
- Report incidenti significativi (per CSIRT e ACN)

### SoA e matrici
- Statement of Applicability ISO 27001
- Matrice correlazione NIS2/ISO 27001/NIST CSF 2.0/UNI/PdR 174
- Matrice RACI per processi SGI
- Matrice rischi/controlli NIS2
- Matrice BIA/processi critici
- Matrice fornitori critici/requisiti sicurezza

---

## 2. Regole di redazione

1. **Un sistema, non molti sistemi**: approccio integrato, zero duplicazioni
2. **Riferimenti incrociati**: ogni documento che copre più schemi elenca tutte le clausole pertinenti
3. **Sezioni specifiche**: requisiti esclusivi di uno schema in sezione dedicata
4. **Versionamento**: versione, data, autore, stato (bozza/approvato/in revisione)
5. **Coerenza**: se una procedura cita un registro, quel registro deve esistere
6. **Placeholder**: `[DA INSERIRE — fonte: descrizione del dato necessario]`
7. **Riferimenti normativi**: ogni requisito con `[ISO 27001:2022 §6.1.2]`, `[Art. 21.2.d NIS2]`, `[Art. 8 L. 90/2024]`
