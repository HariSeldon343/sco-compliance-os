---
description: "AI System Impact Assessment (ISO 42001)"
---

# /aiia — AI System Impact Assessment (ISO 42001)

## Uso
`/aiia [sistema]`

## Quando
Quando occorre produrre la valutazione d'impatto del sistema IA richiesta da ISO/IEC 42001 cl. 6.1.4 e dai controlli A.5.2-A.5.5 dell'Appendice A. È il prerequisito per la corretta identificazione dei rischi e delle misure di trattamento all'interno dell'AIMS. Differisce dal FRIA AI Act (che è richiesto al deployer ex Art. 27 e si concentra sui diritti fondamentali) e dal DPIA GDPR (che si concentra sul trattamento dei dati personali).

## Pre-requisiti

- Scoping completato (`/scope`).
- Classificazione rischio AI Act (`/rischio-regolatorio`).
- Ruolo regolatorio mappato (`/ruoli`).

## Struttura del deliverable

Documento .docx in 5 sezioni.

### 1. Identificazione del sistema
- Denominazione, versione, finalità d'uso dichiarata (intended use).
- Contesto operativo (ambiente di deployment, utenti finali, soggetti impattati).
- Dati di addestramento, validazione, test (fonti, qualità, bias noti).
- Architettura tecnica (modello base, pipeline, integrazioni).
- Ruolo regolatorio del soggetto che conduce l'AIIA.
- Classificazione di rischio AI Act.

### 2. Analisi d'impatto
- **Impatti su individui**: autonomia decisionale, privacy, non discriminazione, sicurezza fisica, accesso a servizi.
- **Impatti su gruppi e società**: equità, concentrazione di potere informativo, pluralismo, ambiente.
- **Impatti su organizzazione**: reputazione, compliance, continuità operativa, responsabilità legale.
- Per ogni impatto: scenario, probabilità, gravità, reversibilità, scala (individuale/collettiva).

### 3. Valutazione
- Matrice probabilità × gravità (scala 1-5).
- Livello di rischio: basso / medio / alto / inaccettabile.
- Confronto con soglie di accettabilità definite dalla politica AI.
- Identificazione rischi residui dopo controlli esistenti.

### 4. Trattamento
- Misure di mitigazione proposte (tecniche, organizzative, contrattuali).
- Mapping con controlli Appendice A ISO 42001.
- Mapping con obblighi AI Act (se alto rischio).
- Mapping con settori Legge 132 attivati.
- Rischio residuo atteso post-trattamento.
- Accettazione formale del rischio residuo (owner, data).

### 5. Documentazione e revisione
- Persone coinvolte nella valutazione (competenze, conflitti di interesse).
- Fonti consultate.
- Data di prima emissione e piano di revisione (almeno annuale o su change significativo).
- Integrazione nel sistema documentale AIMS.

## Regole operative

- L'AIIA è **diversa** dal FRIA AI Act Art. 27: quando il soggetto è deployer di un sistema ad alto rischio, entrambi sono dovuti. Usa `/fria` per il secondo.
- L'AIIA è **diversa** dalla DPIA GDPR: quando il sistema tratta dati personali con rischio elevato, entrambe sono dovute.
- Se il sistema rientra nelle pratiche vietate AI Act Art. 5, l'AIIA si riduce a documentazione del divieto e raccomandazione di non dispiegare.
- Aggiornamento obbligatorio al verificarsi di: modifica sostanziale del sistema, incidente grave, cambio di contesto operativo, nuova evidenza di bias o danno.
- Coinvolgi almeno: AI impact assessor, domain expert, data protection officer, rappresentanti dei soggetti impattati (quando proporzionato).

## Documenti collegati

- `../references/iso42001-2023.md` (cl. 6.1.4, A.5.2-A.5.5)
- `../references/ai-act-2024.md` (Art. 27 per differenza con FRIA)
- `../templates/aiia-report.md`
