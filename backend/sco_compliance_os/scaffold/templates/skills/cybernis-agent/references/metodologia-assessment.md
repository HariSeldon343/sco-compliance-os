# Metodologia di Assessment — Scale, Formato e Stile

## 1. Formato obbligatorio per ogni controllo

```
Controllo [CODICE]: [Descrizione]

Incidenza: [Alta / Medio-alta / Media / Bassa / Non applicabile]

Qualità: [Iniziale/Ad-hoc | Ripetibile/Gestito | Definito/Standardizzato |
          Quantitativamente Gestito | Ottimizzato]

[Tipo di rilievo]: [Max 3-4 righe]

Note: [Min 8-10 righe]
```

## 2. Scale di valutazione

### Tipo rilievo (in ordine di preferenza)

| Tipo | Criterio |
|---|---|
| **Opportunità di miglioramento** | Requisito soddisfatto, ottimizzabile |
| **Osservazione** | Requisito soddisfatto parzialmente, miglioramenti necessari |
| **Non conformità** | Requisito mancante o gravemente inadeguato (solo se strettamente necessario) |

### Livello qualità

| Livello | Descrizione |
|---|---|
| **Iniziale/Ad-hoc** | Processo esistente ma non formalizzato, caso per caso |
| **Ripetibile/Gestito** | Processo documentato con procedure definite |
| **Definito/Standardizzato** | Processo standardizzato e integrato nel SG |
| **Quantitativamente Gestito** | Processo misurato con KPI e monitoraggio continuo |
| **Ottimizzato** | Processo in miglioramento continuo con innovazione sistematica |

## 3. Regole stilistiche

### Sezione "Tipo di rilievo" (max 3-4 righe)
- Inizia con frase che descriva lo stato attuale
- Specifica SEMPRE cosa richiede il controllo
- Confronta stato attuale con requisito
- Evidenzia gap specifici

### Sezione "Note" (min 8-10 righe)
- Inizia SEMPRE con 2-3 righe contesto narrativo
- Elenca evidenze documentali con riferimenti precisi (nome documento, revisione, data, contenuto)
- Concludi con considerazioni sull'integrazione tra sistemi

### Vocabolario da variare

| Categoria | Espressioni |
|---|---|
| Aperture | "L'analisi del framework evidenzia...", "La struttura organizzativa mostra...", "La verifica dei processi IT conferma...", "Il sistema di gestione presenta..." |
| Criticità | "Tuttavia...", "Non risulta proceduralizzato...", "Permane la necessità di...", "Manca integrazione formale...", "Non si rileva evidenza di..." |
| Punti di forza | "dimostra maturità attraverso...", "evidenzia eccellenza operativa...", "garantisce conformità mediante...", "consolida un approccio strutturato..." |

## 4. Esempio completo

```
Controllo RS.MA-01.01: Gestione incidenti di sicurezza informatica

Incidenza: Alta

Qualità: Livello Ripetibile/Gestito

Osservazione: Il framework di gestione incidenti risulta operativo per gli
eventi IT ma non completamente strutturato per la classificazione degli
incidenti significativi ai sensi dell'Art. 23 NIS2. Il controllo richiede un
processo documentato con criteri di classificazione, escalation e notifica al
CSIRT Italia. L'organizzazione dispone di procedure IT operative ma necessita
di formalizzazione per i requisiti normativi specifici.

Note:
Il processo di gestione incidenti evidenzia una base operativa consolidata
nell'ambito IT, con competenze tecniche nella risoluzione di eventi di
sicurezza. L'evoluzione verso i requisiti NIS2 richiede l'integrazione dei
workflow normativi di notifica.

- Procedura di gestione incidenti IT (Rev. 02, marzo 2024) documenta il
  workflow di rilevazione, analisi e contenimento con "escalation al
  responsabile IT entro 2 ore dalla rilevazione"
- Il sistema di ticketing registra gli incidenti ma non include la
  classificazione secondo criteri di "incidente significativo" ex Art. 23
  D.Lgs. 138/2024
- Non si rileva evidenza di processo formalizzato per notifica CSIRT Italia
  (preallarme 24h, notifica 72h, relazione finale 1 mese)
- Piano formazione 2024 include moduli sicurezza informatica ma non specifici
  sulla gestione incidenti NIS2
- L'integrazione consisterebbe nell'estendere la procedura esistente con la
  tassonomia degli incidenti significativi NIS2 e i relativi workflow di
  comunicazione alle autorità competenti.
```
