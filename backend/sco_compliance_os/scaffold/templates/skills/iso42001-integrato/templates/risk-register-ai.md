# Template — Registro dei rischi IA

> Struttura compatibile con ISO/IEC 42001 cl. 6.1.2-6.1.3, ISO/IEC 23894, AI Act Art. 9.

---

# Registro dei rischi IA — [Denominazione organizzazione]

**Codice documento:** AIMS-RISK-01
**Versione:** [x.y]
**Data di aggiornamento:** [gg/mm/aaaa]
**Owner:** [AI Governance Lead / Risk Manager]

## 1. Scope e criteri

- Scope AIMS applicato: AIMS-SCP-01.
- Metodologia: ISO 31000 + ISO/IEC 23894 (linee guida risk management IA).
- Scala probabilità (1-5): Rarissima / Rara / Possibile / Probabile / Quasi certa.
- Scala gravità (1-5): Insignificante / Lieve / Moderata / Grave / Catastrofica.
- Livello di rischio = Prob × Grav.
- Soglia di accettabilità: [definire per livello e per tipologia].

## 2. Tabella rischi

| ID | Area | Sistema IA | Descrizione rischio | Fonte (AI Act / ISO 42001 / Legge 132) | Prob | Grav | Livello lordo | Controlli esistenti | Livello residuo | Trattamento | Owner | Scadenza | Stato | KRI |
|----|------|------------|---------------------|-----------------------------------------|------|------|---------------|---------------------|-----------------|-------------|-------|----------|-------|-----|
| R-001 | Data governance | [Sistema X] | Bias nei dati di training | Art. 10 AI Act; A.7.2-A.7.6 | 3 | 4 | 12 | Audit dataset trimestrale | 6 | Ribilanciamento dataset + controlli output | [Ruolo] | [data] | Aperto | Tasso falsi positivi |
| R-002 | Cybersecurity | | Data poisoning | Art. 15; A.6.2.4 | | | | | | | | | | |
| R-003 | Trasparenza | | Informativa non comprensibile agli utenti | Art. 13 | | | | | | | | | | |
| R-004 | Sorveglianza umana | | Fatigue dell'operatore che porta a omologazione automatica | Art. 14; A.9.2 | | | | | | | | | | |
| R-005 | Accuracy | | Degrado prestazioni nel tempo (model drift) | Art. 15; A.6.2.6 | | | | | | | | | | |
| R-006 | Fornitori | | Dipendenza da fornitore cloud senza SLA | Art. 25; A.10.3 | | | | | | | | | | |
| R-007 | Incidenti gravi | | Errore sistemico che produce danno a utenti | Art. 73 | | | | | | | | | | |
| R-008 | FRIA | | Discriminazione su gruppi protetti | Art. 27 | | | | | | | | | | |
| R-009 | Legge 132 | | Mancata informativa lavoratore D.Lgs. 152/1997 | L. 132 Art. 11 | | | | | | | | | | |
| R-010 | GDPR | | Trattamento senza base giuridica | GDPR Art. 6 | | | | | | | | | | |
| R-011 | NIS2 | | Incidente non notificato entro 24h | D.Lgs. 138/2024 Art. 23 | | | | | | | | | | |
| R-012 | Reputazione | | Deepfake non etichettato | Art. 50 c. 4 | | | | | | | | | | |
| R-013 | GPAI | | Uso di GPAI con rischio sistemico senza valutazione | Art. 55 | | | | | | | | | | |
| R-014 | Ciclo di vita | | Modifica sostanziale non riconosciuta | Art. 3 n. 23 | | | | | | | | | | |
| R-015 | Formazione | | Personale non formato AI literacy | Art. 4 | | | | | | | | | | |

[Estendere con rischi specifici dell'organizzazione]

## 3. Strategie di trattamento

Per ciascun rischio sopra soglia:

- **Evitare**: eliminare l'esposizione (rinuncia al sistema, modifica finalità).
- **Mitigare**: ridurre probabilità o gravità con controlli tecnici/organizzativi.
- **Trasferire**: assicurazione, contrattualizzazione con fornitore.
- **Accettare**: formalizzare accettazione del rischio residuo.

## 4. Monitoraggio (KRI)

Key Risk Indicators da monitorare:

| KRI | Soglia allerta | Soglia critica | Frequenza |
|-----|-----------------|-----------------|-----------|
| Tasso falsi positivi | [...] | [...] | mensile |
| Tasso falsi negativi | [...] | [...] | mensile |
| Incidenti in PMM | [...] | [...] | continuo |
| Reclami utenti | [...] | [...] | mensile |
| Audit trail log integrity | [...] | [...] | settimanale |
| Deriva del modello | [...] | [...] | mensile |
| Gap di sorveglianza umana | [...] | [...] | trimestrale |

## 5. Integrazione cross-framework

| Quadro | Integrazione |
|--------|--------------|
| ISO 27001 (registro rischi SGSI) | Condivisione voci sui rischi cyber del sistema IA |
| GDPR (registro trattamenti) | Mapping con trattamenti di dati personali |
| NIS2 | Rischi comuni su disponibilità servizi critici |
| Legge 231/2001 (MOG) | Rischi reato collegati a deepfake, responsabilità IA |

## 6. Revisione

- Revisione periodica: trimestrale.
- Revisione straordinaria: modifica sistemi, incidente, audit, evoluzione normativa.
- Firma revisione: [Owner + data].
